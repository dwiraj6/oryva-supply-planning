"""Evaluation: detector vs ground truth, planning KPIs, data realism profile."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import calendar as cal
from .schema import ISSUE_TYPES


def detector_metrics(exc: pd.DataFrame, gt: pd.DataFrame) -> dict:
    out = {}
    tp_all = fp_all = fn_all = 0
    for it in ISSUE_TYPES:
        truth = set(gt.record_id[(gt.issue_type == it) & gt.expected_flag.astype(bool)])
        pred = set(exc.record_id[exc.issue_type == it])
        tp, fp, fn = len(truth & pred), len(pred - truth), len(truth - pred)
        tp_all, fp_all, fn_all = tp_all + tp, fp_all + fp, fn_all + fn
        p = tp / (tp + fp) if tp + fp else 1.0
        r = tp / (tp + fn) if tp + fn else 1.0
        out[it] = {"labelled": len(truth), "flagged": len(pred), "tp": tp, "fp": fp, "fn": fn,
                   "precision": round(p, 4), "recall": round(r, 4),
                   "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
                   "false_positive_ids": sorted(pred - truth)[:10], "missed_ids": sorted(truth - pred)[:10]}
    p = tp_all / (tp_all + fp_all) if tp_all + fp_all else 1.0
    r = tp_all / (tp_all + fn_all) if tp_all + fn_all else 1.0
    out["_micro"] = {"tp": tp_all, "fp": fp_all, "fn": fn_all, "precision": round(p, 4), "recall": round(r, 4),
                     "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0}
    # boundary records must NOT be flagged
    flagged = set(exc.record_id) | {x for rel in exc.related_record_ids.dropna() for x in rel.split("|")}
    b = gt[~gt.expected_flag.astype(bool)]
    fpb = b[b.record_id.isin(flagged)]
    out["_boundary"] = {"boundary_records": len(b), "false_positives": len(fpb),
                        "false_positive_ids": fpb.record_id.tolist()}
    # confusion: predicted type vs true type, by record id
    truth_type = dict(zip(gt.record_id[gt.expected_flag.astype(bool)], gt.issue_type[gt.expected_flag.astype(bool)]))
    conf = {}
    for rid, it in zip(exc.record_id, exc.issue_type):
        tt = truth_type.get(rid, "NOT_AN_ANOMALY")
        conf.setdefault(tt, {}).setdefault(it, 0)
        conf[tt][it] += 1
    for rid, tt in truth_type.items():
        if rid not in set(exc.record_id):
            conf.setdefault(tt, {}).setdefault("NOT_FLAGGED", 0)
            conf[tt]["NOT_FLAGGED"] += 1
    out["_confusion"] = conf
    return out


def _line_delta(lines: pd.DataFrame, mask: pd.Series, H: int) -> dict:
    out = {}
    sub = lines[mask]
    for r, w, q in zip(sub.row, sub.w_actual, sub.q_actual):
        if 1 <= w <= H and q:
            out.setdefault(int(r), np.zeros(H, dtype=np.int64))[int(w) - 1] += int(q)
    return out


def anomaly_impact(o: dict, gt: pd.DataFrame, t: dict) -> dict:
    """Isolated impact of each labelled anomaly: the cleaned plan with ONLY that
    record's raw (uncorrected) receipt lines swapped back in."""
    raw = o["_raw"]
    idx, C, raw_lines, lines = raw["idx"], raw["C"], raw["raw_lines"], raw["lines"]
    H = C.shape[1]
    sh = o["shortage"]
    hidden = sh[~sh.visible_in_raw_plan.astype(bool)]
    rows = []
    for g in gt[gt.expected_flag.astype(bool)].itertuples(index=False):
        col = "shipment_id" if g.entity == "inbound_shipment" else "po_id"
        d_raw = _line_delta(raw_lines, raw_lines[col] == g.record_id, H)
        d_cln = _line_delta(lines, lines[col] == g.record_id, H)
        for r in sorted(set(d_raw) | set(d_cln)):
            delta = np.cumsum(d_raw.get(r, 0) - d_cln.get(r, np.zeros(H, dtype=np.int64)))
            if not np.any(delta):
                continue
            alt = C[r] + delta
            rows.append({"issue_type": g.issue_type, "record_id": g.record_id,
                         "sku_id": idx.rows.sku_id[r], "location_id": idx.rows.location_id[r],
                         "raw_shortage_weeks": int((alt < 0).sum()), "clean_shortage_weeks": int((C[r] < 0).sum()),
                         "max_abs_balance_error": int(np.abs(delta).max()),
                         "direction": "overstated" if delta.max() > 0 else "understated"})
    df = pd.DataFrame(rows)
    if len(df):
        df["hidden_shortage_weeks"] = np.maximum(df.clean_shortage_weeks - df.raw_shortage_weeks, 0)
        df["false_shortage_weeks"] = np.maximum(df.raw_shortage_weeks - df.clean_shortage_weeks, 0)
        by = df.groupby("issue_type").agg(records=("record_id", "nunique"),
                                          direction=("direction", lambda s: "/".join(sorted(set(s)))),
                                          hidden_shortage_weeks=("hidden_shortage_weeks", "sum"),
                                          false_shortage_weeks=("false_shortage_weeks", "sum"),
                                          max_abs_balance_error=("max_abs_balance_error", "max")).reset_index()
    else:
        by = df
    return {"shortages_hidden_in_raw_plan": int(len(hidden)), "by_issue_type": by.to_dict("records"),
            "records": df.to_dict("records")}


def planning_kpis(o: dict, t: dict) -> dict:
    sh, mo, cs = o["shortage"], o["mitigation_option"], o["shortage_cause"]
    sel = mo[mo.selected]
    act = sel[sel.option_type != "ACCEPT_SHORTFALL"]
    need = sh.mitigated_qty + sh.residual_qty
    pab = o["projected_balance"]
    total_dem = int(pab.forecast_qty.sum() + pab.dependent_demand_qty.sum())
    return {
        "sku_locations": int(pab[["sku_id", "location_id"]].drop_duplicates().shape[0]),
        "shortages": int(len(sh)),
        "sku_locations_with_shortage": int(sh[["sku_id", "location_id"]].drop_duplicates().shape[0]),
        "shortage_units": int(sh.shortage_qty.sum()),
        "shortage_units_pct_of_demand": round(100 * sh.shortage_qty.sum() / max(total_dem, 1), 2),
        "recoverable_pct": round(100 * sh.recoverable.mean(), 2) if len(sh) else 0.0,
        "status_counts": sh.status.value_counts().to_dict(),
        "fill_rate_pct": round(100 * sh.mitigated_qty.sum() / max(need.sum(), 1), 2),
        "mitigation_cost": round(float(act.selected_cost.sum()), 2),
        "accepted_lost_margin": round(float(sel[sel.option_type == "ACCEPT_SHORTFALL"].selected_cost.sum()), 2),
        "options_generated": int(len(mo)),
        "options_feasible": int(mo.feasible.sum()),
        "options_dominated": int(mo.dominated.sum()),
        "selected_by_type": act.option_type.value_counts().to_dict(),
        "selected_units_by_type": act.groupby("option_type").selected_qty.sum().astype(int).to_dict(),
        "rejection_reasons": mo.rejection_reason.dropna().str.replace(r"\(.*\)", "", regex=True).value_counts().to_dict(),
        "cause_units": cs.groupby("cause_type").contributed_qty.sum().astype(int).to_dict(),
        "below_safety_stock_weeks_pct": round(100 * pab.below_safety_stock.mean(), 2),
    }


def top_shortages(o: dict, t: dict, n: int = 20) -> list:
    sh = o["shortage"].sort_values("priority_rank").head(n)
    cs = o["shortage_cause"]
    mo = o["mitigation_option"]
    abc = t["sku"].set_index("sku_id").abc_class
    out = []
    for r in sh.itertuples(index=False):
        causes = cs[cs.shortage_id == r.shortage_id].sort_values("contributed_qty", ascending=False)
        opts = mo[mo.shortage_id == r.shortage_id]
        out.append({
            "rank": int(r.priority_rank), "shortage_id": r.shortage_id, "sku_id": r.sku_id, "abc": abc[r.sku_id],
            "location_id": r.location_id, "start_week": r.start_week, "end_week": r.end_week,
            "shortage_qty": int(r.shortage_qty), "priority_score": float(r.priority_score),
            "recoverable": bool(r.recoverable), "status": r.status, "fill_pct": float(r.fill_pct),
            "causes": [{"type": c.cause_type, "qty": int(c.contributed_qty), "pct": float(c.share_pct),
                        "evidence": c.source_record_ids} for c in causes.itertuples(index=False)],
            "options": [{"id": x.mitigation_id, "type": x.option_type,
                         "source": x.source_id if isinstance(x.source_id, str) else None, "offered": int(x.offered_qty),
                         "cost": float(x.cost), "fill_pct": float(x.fill_pct), "feasible": bool(x.feasible),
                         "dominated": bool(x.dominated), "selected": bool(x.selected), "selected_qty": int(x.selected_qty),
                         "reason": x.rejection_reason} for x in opts.itertuples(index=False)],
        })
    return out


def data_profile(t: dict) -> dict:
    d = t["forecast_demand"]
    abc = t["sku"].set_index("sku_id").abc_class
    d = d.assign(abc=d.sku_id.map(abc))
    g = d.groupby(["sku_id", "location_id"]).forecast_qty
    stats = pd.DataFrame({"mean": g.mean(), "std": g.std(), "zero": g.apply(lambda s: (s == 0).mean())})
    stats["cv"] = stats["std"] / stats["mean"].replace(0, np.nan)
    stats["abc"] = stats.index.get_level_values(0).map(abc)
    by_abc = stats.groupby("abc").agg(sku_locations=("mean", "size"), mean_weekly=("mean", "mean"),
                                      median_cv=("cv", "median"), zero_week_share=("zero", "mean")).round(3)
    po = t["purchase_order"]
    lt = t["lead_time"].lead_time_weeks
    sh = t["inbound_shipment"]
    ev = t["po_event"]
    return {
        "demand_by_abc": by_abc.reset_index().to_dict("records"),
        "spike_week_share": round(float((d.uplift_qty > 0).mean()), 4),
        "sku_mix": t["sku"].groupby(["abc_class", "make_or_buy"]).size().rename("n").reset_index().to_dict("records"),
        "lead_time_weeks": {"min": int(lt.min()), "median": float(lt.median()), "p90": float(lt.quantile(0.9)), "max": int(lt.max())},
        "po_status": po.status.value_counts().to_dict(),
        "po_uom": po.order_uom.value_counts().to_dict(),
        "capacity_cut_pos": int((po.confirmed_base_qty.astype("float64") < po.requested_base_qty.astype("float64")).sum()),
        "constrained_suppliers": int(t["supplier"].capacity_constrained.astype(bool).sum()),
        "suppliers_on_hold": int((t["supplier"].status == "ON_HOLD").sum()),
        "transport_delayed_shipments_pct": round(100 * float((sh.delay_weeks > 0).mean()), 2) if len(sh) else 0.0,
        "supplier_delayed_pos": int(((ev.event_type == "DELAYED") & (ev.actor == "SUPPLIER")).sum()),
        "substitute_pairs": t["sku_substitute"].review_status.value_counts().to_dict(),
        "substitute_pos": int(po.substitute_for_sku_id.notna().sum()),
        "assortment_locations_per_sku": round(float(t["sku_location"].groupby("sku_id").size().mean()), 2),
    }


def evaluate(t: dict, o: dict, exc: pd.DataFrame, gt: pd.DataFrame) -> dict:
    return {"detector": detector_metrics(exc, gt), "anomaly_impact": anomaly_impact(o, gt, t),
            "planning": planning_kpis(o, t), "top_shortages": top_shortages(o, t), "data_profile": data_profile(t)}


def to_markdown(ev: dict, scale: str) -> str:
    d = ev["detector"]
    out = [f"# Evaluation report ({scale})", "", "## 1. Anomaly detection vs ground truth", "",
           "The detector reads only input tables. Scores compare its exceptions with `ground_truth.csv`.", "",
           "| Issue type | Labelled | Flagged | TP | FP | FN | Precision | Recall | F1 |", "|---|---|---|---|---|---|---|---|---|"]
    for it in ISSUE_TYPES:
        m = d[it]
        out.append(f"| {it} | {m['labelled']} | {m['flagged']} | {m['tp']} | {m['fp']} | {m['fn']} | "
                   f"{m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} |")
    mi = d["_micro"]
    out.append(f"| **micro average** |  |  | {mi['tp']} | {mi['fp']} | {mi['fn']} | {mi['precision']:.3f} | {mi['recall']:.3f} | {mi['f1']:.3f} |")
    b = d["_boundary"]
    out += ["", f"Boundary (valid edge) records: {b['boundary_records']}; wrongly flagged: **{b['false_positives']}**.", "",
            "## 2. Impact of anomalies on the plan", "",
            f"Shortages that the raw (uncleaned) plan would have hidden: **{ev['anomaly_impact']['shortages_hidden_in_raw_plan']}**", "",
            "Raw plan = anomalies left in; cleaned plan = detector corrections applied. Hidden weeks: shortage weeks the raw "
            "plan would miss. False weeks: shortage weeks the raw plan would wrongly report.", "",
            "| Issue type | Records | Raw balance error | Hidden shortage weeks | False shortage weeks | Max abs balance error (EA) |",
            "|---|---|---|---|---|---|"]
    for r in ev["anomaly_impact"]["by_issue_type"]:
        out.append(f"| {r['issue_type']} | {r['records']} | {r['direction']} | {r['hidden_shortage_weeks']} | "
                   f"{r['false_shortage_weeks']} | {r['max_abs_balance_error']:,} |")
    p = ev["planning"]
    out += ["", "## 3. Planning KPIs", "", "| KPI | Value |", "|---|---|"]
    for k in ("sku_locations", "shortages", "sku_locations_with_shortage", "shortage_units", "shortage_units_pct_of_demand",
              "recoverable_pct", "fill_rate_pct", "mitigation_cost", "accepted_lost_margin", "options_generated",
              "options_feasible", "options_dominated", "below_safety_stock_weeks_pct"):
        v = p[k]
        out.append(f"| {k} | {v:,} |" if isinstance(v, (int, float)) else f"| {k} | {v} |")
    for k in ("status_counts", "selected_by_type", "selected_units_by_type", "cause_units", "rejection_reasons"):
        out.append(f"| {k} | " + ", ".join(f"{a}: {b:,}" for a, b in sorted(p[k].items())) + " |")
    out += ["", "## 4. Top 20 shortages by priority", "",
            "| Rank | Shortage | SKU (ABC) | Location | Weeks | Qty | Recoverable | Main causes | Selected mitigation | Fill % |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for r in ev["top_shortages"]:
        causes = "; ".join(f"{c['type']} {c['qty']:,} ({c['pct']:.0f}%)" for c in r["causes"][:3])
        sel = "; ".join(f"{o['type']}{' ' + o['source'] if o['source'] else ''} x{o['selected_qty']:,}" for o in r["options"] if o["selected"])
        out.append(f"| {r['rank']} | {r['shortage_id']} | {r['sku_id']} ({r['abc']}) | {r['location_id']} | "
                   f"{r['start_week']}-{r['end_week']} | {r['shortage_qty']:,} | {'yes' if r['recoverable'] else 'no'} | {causes} | {sel} | {r['fill_pct']:.1f} |")
    dp = ev["data_profile"]
    out += ["", "## 5. Generated data profile (realism)", "", "| ABC | SKU-locations | Mean weekly demand | Median CV | Zero-demand week share |",
            "|---|---|---|---|---|"]
    for r in dp["demand_by_abc"]:
        out.append(f"| {r['abc']} | {r['sku_locations']} | {r['mean_weekly']} | {r['median_cv']} | {r['zero_week_share']} |")
    out += ["", "| Measure | Value |", "|---|---|"]
    for k, v in dp.items():
        if k not in ("demand_by_abc", "sku_mix"):
            out.append(f"| {k} | {v} |")
    return "\n".join(out) + "\n"
