"""Single-file static HTML report (no server, no external assets)."""
from __future__ import annotations

import html

from .schema import ISSUE_TYPES

CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--muted:#6b6b66;--line:#e3e2dd;--accent:#2f5d8a;--ok:#2e7d4f;--bad:#b3392f;--warn:#a86a12;--chip:#eef2f6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151514;--card:#1f1f1d;--ink:#ecebe6;--muted:#a3a29b;--line:#34332f;--accent:#8fb6dd;--ok:#6cc08f;--bad:#ef8a80;--warn:#e0b060;--chip:#2a2f35}}
:root[data-theme="dark"]{--bg:#151514;--card:#1f1f1d;--ink:#ecebe6;--muted:#a3a29b;--line:#34332f;--accent:#8fb6dd;--ok:#6cc08f;--bad:#ef8a80;--warn:#e0b060;--chip:#2a2f35}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1200px;margin:0 auto;padding:24px 16px 64px}h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:32px 0 10px}
.sub{color:var(--muted);margin:0 0 20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}.kpi b{display:block;font-size:22px;font-variant-numeric:tabular-nums}
.kpi span{color:var(--muted);font-size:12px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:4px 0;overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:860px;font-variant-numeric:tabular-nums}td:nth-child(-n+5){white-space:nowrap}th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;color:var(--muted);font-weight:600}tr:last-child td{border-bottom:0}.ok{color:var(--ok);font-weight:600}.bad{color:var(--bad);font-weight:600}
.chip{display:inline-block;background:var(--chip);border-radius:6px;padding:1px 6px;margin:1px 2px;font-size:12px}.sel{outline:1.5px solid var(--accent)}
.muted{color:var(--muted)}details{margin:0}summary{cursor:pointer}.num{text-align:right}
"""


def _e(x) -> str:
    return html.escape(str(x))


def build(ev: dict, val: dict, scale: str, seed: int) -> str:
    p, d = ev["planning"], ev["detector"]
    k = [("Shortages", f"{p['shortages']:,}"), ("Shortage units", f"{p['shortage_units']:,}"),
         ("Recoverable", f"{p['recoverable_pct']}%"), ("Fill rate after mitigation", f"{p['fill_rate_pct']}%"),
         ("Mitigation cost", f"{p['mitigation_cost']:,.0f}"), ("Hidden by anomalies", f"{ev['anomaly_impact']['shortages_hidden_in_raw_plan']:,}"),
         ("Detector F1 (micro)", f"{d['_micro']['f1']:.3f}"), ("Validation", val["overall_status"])]
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>ORYVA Planning Report</title><style>{CSS}</style></head><body><main>",
             f"<h1>ORYVA supply planning report</h1><p class='sub'>Scale <b>{_e(scale)}</b> &middot; seed {seed} &middot; "
             f"plan as of 2026W01 &middot; horizon 2026W01-2026W52</p><div class='grid'>"]
    for a, b in k:
        cls = " ok" if b == "PASS" else (" bad" if b == "FAIL" else "")
        parts.append(f"<div class='kpi'><b class='{cls.strip()}'>{_e(b)}</b><span>{_e(a)}</span></div>")
    parts.append("</div>")

    parts.append("<h2>Top shortages by priority</h2><div class='card'><table><tr><th>#</th><th>Shortage</th><th>SKU</th><th>Location</th>"
                 "<th>Weeks</th><th class='num'>Qty</th><th>Causes (contribution)</th><th>Mitigation options (selected outlined)</th><th class='num'>Fill</th></tr>")
    for r in ev["top_shortages"]:
        causes = "".join(f"<span class='chip' title='{_e(c['evidence'] or '')}'>{_e(c['type'])} {c['qty']:,}</span>" for c in r["causes"])
        opts = "".join(
            f"<span class='chip{' sel' if o['selected'] else ''}' title='{_e(o['reason'] or '')}'>{_e(o['type'])}"
            f"{' ' + _e(o['source']) if o['source'] else ''}: {('cost ' + format(o['cost'], ',.0f') + ', fill ' + format(o['fill_pct'], '.0f') + '%') if o['feasible'] else 'infeasible'}"
            f"{' (dominated)' if o['dominated'] else ''}</span>" for o in r["options"])
        parts.append(f"<tr><td>{r['rank']}</td><td>{_e(r['shortage_id'])}<br><span class='muted'>{'recoverable' if r['recoverable'] else 'inside lead time'}</span></td>"
                     f"<td>{_e(r['sku_id'])} ({_e(r['abc'])})</td><td>{_e(r['location_id'])}</td><td>{_e(r['start_week'])}&ndash;{_e(r['end_week'])}</td>"
                     f"<td class='num'>{r['shortage_qty']:,}</td><td>{causes}</td><td>{opts}</td><td class='num'>{r['fill_pct']:.0f}%</td></tr>")
    parts.append("</table></div>")

    parts.append("<h2>Anomaly detection vs ground truth</h2><div class='card'><table><tr><th>Issue type</th><th class='num'>Labelled</th>"
                 "<th class='num'>Flagged</th><th class='num'>Precision</th><th class='num'>Recall</th><th class='num'>F1</th></tr>")
    for it in ISSUE_TYPES:
        m = d[it]
        parts.append(f"<tr><td>{_e(it)}</td><td class='num'>{m['labelled']}</td><td class='num'>{m['flagged']}</td>"
                     f"<td class='num'>{m['precision']:.3f}</td><td class='num'>{m['recall']:.3f}</td><td class='num'>{m['f1']:.3f}</td></tr>")
    b = d["_boundary"]
    parts.append(f"</table></div><p class='muted'>Valid boundary records: {b['boundary_records']}, wrongly flagged: {b['false_positives']}.</p>")

    parts.append("<h2>Where the shortage units come from</h2><div class='card'><table><tr><th>Cause</th><th class='num'>Units</th><th class='num'>Share</th></tr>")
    tot = max(sum(p["cause_units"].values()), 1)
    for c, q in sorted(p["cause_units"].items(), key=lambda z: -z[1]):
        parts.append(f"<tr><td>{_e(c)}</td><td class='num'>{q:,}</td><td class='num'>{100 * q / tot:.1f}%</td></tr>")
    parts.append("</table></div>")

    parts.append("<h2>Validation checks</h2><div class='card'><table><tr><th>Check</th><th>Category</th><th class='num'>Violations</th><th>Status</th></tr>")
    for r in sorted(val["checks"], key=lambda r: (r["status"] == "PASS", r["category"], r["check"])):
        cls = "ok" if r["status"] == "PASS" else "bad"
        extra = f" <span class='muted'>({r.get('explained_by_ground_truth', 0)} labelled)</span>" if r["category"] == "business_rule" else ""
        parts.append(f"<tr><td>{_e(r['check'])}</td><td>{_e(r['category'])}</td><td class='num'>{r['violations']}{extra}</td><td class='{cls}'>{r['status']}</td></tr>")
    parts.append("</table></div></main></body></html>")
    return "".join(parts)
