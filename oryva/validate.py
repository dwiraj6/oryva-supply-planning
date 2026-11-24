"""Validation suite (brief Section 5 step 8 and Section 7).

Two categories:
  integrity      must have ZERO violations (PK, FK, enums, patterns, dates,
                 lifecycle, arithmetic reconciliation, mitigation policy)
  business_rule  violations are allowed ONLY when every violating record is a
                 labelled anomaly in ground truth (deliberate edge cases).
Ground truth is read here only to explain business-rule violations; it is
never used by detect.py or plan.py.
"""
from __future__ import annotations

import math
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from . import calendar as cal
from .config import HORIZON_WEEKS, P, SNAPSHOT_WEEK
from .schema import INPUT_TABLES, OUTPUT_TABLES, TABLES, to_sql_ddl

H = HORIZON_WEEKS


class Checks:
    def __init__(self):
        self.results = []

    def add(self, name, category, bad, detail="", sample=None):
        bad = list(bad) if not isinstance(bad, int) else bad
        n = bad if isinstance(bad, int) else len(bad)
        smp = [] if isinstance(bad, int) else [str(x) for x in bad[:5]]
        self.results.append({"check": name, "category": category, "violations": int(n),
                             "status": "PASS" if n == 0 else "FAIL", "detail": detail,
                             "sample": sample if sample is not None else smp,
                             "_ids": [] if isinstance(bad, int) else [str(x) for x in bad]})


def _wk(series) -> np.ndarray:
    return cal.indices(series)


# --------------------------------------------------------------------- generic schema checks
def schema_checks(ck: Checks, tabs: dict) -> None:
    for name, df in tabs.items():
        t = TABLES[name]
        pk = df[t.pk]
        ck.add(f"{name}: primary key unique & non-null", "integrity",
               pk[pk.isna() | pk.duplicated(keep=False)].astype(str).tolist())
        if t.natural_key:
            d = df[df.duplicated(list(t.natural_key), keep=False)]
            ck.add(f"{name}: natural key {t.natural_key} unique", "integrity", d[t.pk].astype(str).tolist())
        for c in t.cols:
            s = df[c.name]
            if c.required:
                ck.add(f"{name}.{c.name}: required", "integrity", df.loc[s.isna(), t.pk].astype(str).tolist())
            nn = s.dropna()
            if c.allowed is not None and len(nn):
                allowed = set(c.allowed)
                vals = nn.astype(int) if c.type == "int" else nn
                bad = df.loc[nn.index[~vals.isin(allowed)], t.pk]
                ck.add(f"{name}.{c.name}: allowed values", "integrity", bad.astype(str).tolist())
            if c.pattern and len(nn):
                rx = re.compile(rf"^{c.pattern}$")
                bad = df.loc[nn.index[~nn.astype(str).map(lambda v: bool(rx.match(v)))], t.pk]
                ck.add(f"{name}.{c.name}: pattern {c.pattern}", "integrity", bad.astype(str).tolist())
            if c.type == "week" and len(nn):
                bad = df.loc[nn.index[~nn.map(cal.is_valid)], t.pk]
                ck.add(f"{name}.{c.name}: valid ISO week", "integrity", bad.astype(str).tolist())
            if c.type == "date" and len(nn):
                bad = df.loc[nn.index[pd.to_datetime(nn, errors="coerce", format="%Y-%m-%d").isna()], t.pk]
                ck.add(f"{name}.{c.name}: valid date", "integrity", bad.astype(str).tolist())


def fk_checks(ck: Checks, tabs: dict) -> None:
    for name, df in tabs.items():
        for c in TABLES[name].cols:
            if not c.fk:
                continue
            ft, fc = c.fk.split(".")
            if ft not in tabs:
                continue
            ref = set(tabs[ft][fc])
            s = df[c.name].dropna()
            bad = df.loc[s.index[~s.isin(ref)], TABLES[name].pk]
            ck.add(f"FK {name}.{c.name} -> {c.fk}", "integrity", bad.astype(str).tolist())


def sqlite_check(ck: Checks, tabs: dict, db_path: Path) -> None:
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(to_sql_ddl().replace("PRAGMA foreign_keys = ON;", "PRAGMA foreign_keys = OFF;"))
    errors = []
    for name in INPUT_TABLES + OUTPUT_TABLES:
        if name not in tabs:
            continue
        df = tabs[name]
        cols = [c.name for c in TABLES[name].cols]
        rows = []
        for rec in df[cols].itertuples(index=False, name=None):
            rows.append(tuple(None if (v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA)
                              else (int(v) if isinstance(v, (bool, np.bool_)) else
                                    (int(v) if isinstance(v, np.integer) else v)) for v in rec))
        try:
            con.executemany(f"INSERT INTO {name} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", rows)
        except sqlite3.DatabaseError as e:
            errors.append(f"{name}: {e}")
    con.commit()
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    con.close()
    ck.add("SQLite load with CHECK/UNIQUE constraints", "integrity", errors)
    ck.add("SQLite PRAGMA foreign_key_check", "integrity", [f"{a}:{b}" for a, b, *_ in fk])


# --------------------------------------------------------------------- domain checks
ALLOWED_PO = {("CREATED", "CONFIRMED"), ("CREATED", "CANCELLED"), ("CONFIRMED", "SHIPPED"),
              ("CONFIRMED", "DELAYED"), ("CONFIRMED", "CANCELLED"), ("SHIPPED", "DELAYED")}


def input_checks(ck: Checks, t: dict) -> None:
    d = t["forecast_demand"]
    ck.add("forecast_qty = baseline_qty + uplift_qty", "integrity",
           d.demand_id[d.forecast_qty != d.baseline_qty + d.uplift_qty].tolist())
    inv = t["inventory"]
    ck.add("inventory: available = on_hand - allocated; 0 <= allocated <= on_hand", "integrity",
           inv.inventory_id[(inv.available_qty != inv.on_hand_qty - inv.allocated_qty) |
                            (inv.allocated_qty < 0) | (inv.allocated_qty > inv.on_hand_qty)].tolist())
    shp = t["inbound_shipment"].merge(t["purchase_order"][["po_id", "sku_id", "location_id"]], on="po_id")
    transit = shp.groupby(["sku_id", "location_id"]).qty_base.sum()
    ck.add("inventory: in_transit_qty = sum of inbound shipments to the SKU-location", "integrity",
           inv.inventory_id[[int(transit.get((s, l), 0)) != int(q) for s, l, q in
                             zip(inv.sku_id, inv.location_id, inv.in_transit_qty)]].tolist())
    sl = set(zip(t["sku_location"].sku_id, t["sku_location"].location_id))
    ck.add("forecast_demand SKU-location is in assortment", "integrity",
           d.demand_id[[(s, l) not in sl for s, l in zip(d.sku_id, d.location_id)]].tolist())
    ck.add("inventory SKU-location is in assortment", "integrity",
           inv.inventory_id[[(s, l) not in sl for s, l in zip(inv.sku_id, inv.location_id)]].tolist())
    sku = t["sku"]
    ck.add("sku: unit_price > unit_cost > 0", "integrity",
           sku.sku_id[(sku.unit_cost <= 0) | (sku.unit_price <= sku.unit_cost)].tolist())
    for name in ("sku", "supplier_sku", "lead_time"):
        df = t[name]
        m = df.effective_to.notna()
        bad = df.loc[m & (df.effective_to.astype(str) < df.effective_from.astype(str)), TABLES[name].pk]
        ck.add(f"{name}: effective_from <= effective_to", "integrity", bad.tolist())
    subs = t["sku_substitute"]
    ck.add("sku_substitute: approved == (review_status == APPROVED); approved_on iff approved", "integrity",
           subs.substitute_id[(subs.approved.astype(bool) != (subs.review_status == "APPROVED")) |
                              (subs.approved.astype(bool) != subs.approved_on.notna())].tolist())
    ss = t["supplier_sku"]
    prim = ss.groupby("sku_id").is_primary.sum()
    ck.add("supplier_sku: exactly one primary supplier per SKU", "integrity", prim[prim != 1].index.tolist())
    pack = sku.set_index("sku_id").pack_size
    ck.add("supplier_sku: MOQ is a multiple of order multiple = pack_size", "integrity",
           ss.supplier_sku_id[(ss.moq_base_qty % ss.order_multiple_base_qty != 0) |
                              (ss.order_multiple_base_qty != ss.sku_id.map(pack))].tolist())
    mob = sku.set_index("sku_id").make_or_buy
    bom = t["bom"]
    ck.add("bom: parent is MAKE and component is BUY", "integrity",
           bom.bom_id[(bom.parent_sku_id.map(mob) != "MAKE") | (bom.component_sku_id.map(mob) != "BUY")].tolist())
    lt = t["lead_time"]
    ck.add("lead_time: lead_time_weeks > transit_weeks >= 1", "integrity",
           lt.lead_time_id[(lt.lead_time_weeks <= lt.transit_weeks) | (lt.transit_weeks < 1)].tolist())
    pp = t["production_plan"]
    load = pp.groupby(["location_id", "week"]).planned_qty.sum()
    cap = t["production_capacity"].set_index(["location_id", "week"]).capacity_base_qty
    over = [f"{a}|{b}" for (a, b), q in load.items() if q > cap.get((a, b), -1)]
    ck.add("production_plan: plant load <= production capacity", "integrity", over)

    # purchase orders
    po = t["purchase_order"]
    uom = t["uom_conversion"].set_index(["sku_id", "from_uom"]).factor
    factor = np.array([int(uom[(s, u)]) for s, u in zip(po.sku_id, po.order_uom)])
    ck.add("purchase_order: requested_base_qty = order_qty * uom factor", "integrity",
           po.po_id[po.requested_base_qty.to_numpy() != po.order_qty.to_numpy() * factor].tolist())
    conf = po.confirmed_base_qty.astype("float64")
    ck.add("purchase_order: confirmed_base_qty <= requested_base_qty", "integrity",
           po.po_id[conf > po.requested_base_qty.astype("float64")].tolist())
    ck.add("purchase_order: confirmed qty null iff CREATED/CANCELLED", "integrity",
           po.po_id[conf.isna() != po.status.isin(["CREATED", "CANCELLED"])].tolist())
    cw, ow, pw = _wk(po.created_week), _wk(po.order_week), _wk(po.promised_week)
    ck.add("purchase_order: created_week <= order_week < promised_or_equal; created <= snapshot", "integrity",
           po.po_id[(cw > ow) | (ow > pw) | (cw > SNAPSHOT_WEEK)].tolist())

    ev = t["po_event"].sort_values(["po_id", "event_seq"])
    bad_seq, bad_trans, bad_week, bad_status = [], [], [], []
    last_status = {}
    evw = dict(zip(ev.event_id, _wk(ev.event_week)))
    for pid, g in ev.groupby("po_id", sort=False):
        seqs = g.event_seq.tolist()
        if seqs != list(range(1, len(seqs) + 1)):
            bad_seq.append(pid)
        types = g.event_type.tolist()
        weeks = [evw[e] for e in g.event_id]
        if types[0] != "CREATED" or any((a, b) not in ALLOWED_PO for a, b in zip(types, types[1:])):
            bad_trans.append(pid)
        if any(b < a for a, b in zip(weeks, weeks[1:])) or max(weeks) > SNAPSHOT_WEEK:
            bad_week.append(pid)
        last_status[pid] = [x for x in types if x != "DELAYED"][-1]
    ck.add("po_event: event_seq is 1..n per PO", "integrity", bad_seq)
    ck.add("po_event: lifecycle transitions are legal", "integrity", bad_trans)
    ck.add("po_event: event weeks non-decreasing and <= snapshot", "integrity", bad_week)
    ck.add("purchase_order.status == latest non-DELAYED event", "integrity",
           po.po_id[po.po_id.map(last_status) != po.status].tolist())
    ck.add("every PO has an event history", "integrity", po.po_id[~po.po_id.isin(ev.po_id)].tolist())
    dl = ev[ev.event_type == "DELAYED"]
    prom = po.set_index("po_id").promised_week
    ck.add("po_event: DELAYED new_promised_week later than promised_week", "integrity",
           dl.event_id[_wk(dl.new_promised_week) <= _wk(dl.po_id.map(prom))].tolist())

    sh = t["inbound_shipment"]
    tr = lt.set_index(["supplier_id", "location_id"]).transit_weeks
    pol = po.set_index("po_id")
    transit = np.array([int(tr[(pol.at[p, "supplier_id"], pol.at[p, "location_id"])]) for p in sh.po_id])
    ck.add("inbound_shipment: eta_week = ship_week + transit_weeks + delay_weeks", "integrity",
           sh.shipment_id[_wk(sh.eta_week) != _wk(sh.ship_week) + transit + sh.delay_weeks.to_numpy()].tolist())
    ck.add("inbound_shipment: only for SHIPPED POs", "integrity",
           sh.shipment_id[sh.po_id.map(pol.status) != "SHIPPED"].tolist())
    shipped = po.po_id[po.status == "SHIPPED"]
    ck.add("every SHIPPED PO has a shipment", "integrity", shipped[~shipped.isin(sh.po_id)].tolist())

    sup = t["supplier"]
    cut = set(po.supplier_id[conf < po.requested_base_qty.astype("float64")])
    ck.add("supplier.capacity_constrained derived from capacity cuts", "integrity",
           sup.supplier_id[sup.capacity_constrained.astype(bool) != sup.supplier_id.isin(cut)].tolist())


def business_rules(ck: Checks, t: dict) -> None:
    po = t["purchase_order"]
    sh = t["inbound_shipment"].sort_values(["po_id", "shipment_id"])
    conf = po.set_index("po_id").confirmed_base_qty.astype("float64")
    extra = sh[sh.po_id.duplicated(keep="first")].shipment_id.tolist()
    tot = sh.groupby("po_id").qty_base.sum()
    over = [p for p, q in tot.items() if q > conf.get(p, np.inf)]
    ck.add("BR1 at most one ASN per PO (inbound not double counted)", "business_rule", extra,
           detail=f"POs whose shipped qty > confirmed: {len(over)}")
    dup = sh[sh.duplicated(["po_id", "carrier", "ship_week", "qty_base"], keep="first")].shipment_id.tolist()
    ck.add("BR6 no duplicate shipment records (po, carrier, ship week, qty)", "business_rule", dup)

    subs = t["sku_substitute"]
    ok = {(a, b) for a, b, x in zip(subs.sku_id, subs.substitute_sku_id, subs.approved) if bool(x)}
    m = po.substitute_for_sku_id.notna()
    ck.add("BR2 substitute POs use an APPROVED substitute pair", "business_rule",
           [p for p, x, y in zip(po.po_id[m], po.sku_id[m], po.substitute_for_sku_id[m]) if (y, x) not in ok])

    cap = t["supplier_capacity"].set_index(["supplier_id", "week"]).capacity_base_qty
    live = po[po.status.isin(["CONFIRMED", "SHIPPED"])].sort_values(["supplier_id", "promised_week", "po_id"])
    bad = []
    for (s, w), g in live.groupby(["supplier_id", "promised_week"]):
        c = cap.get((s, w))
        if c is not None:
            cum = g.confirmed_base_qty.astype("float64").cumsum()
            bad += g.po_id[cum > c].tolist()
    ck.add("BR3 confirmed supplier load <= weekly capacity", "business_rule", bad)

    lt = t["lead_time"].set_index(["supplier_id", "location_id"]).lead_time_weeks
    need = np.array([int(lt[(s, l)]) for s, l in zip(po.supplier_id, po.location_id)])
    gap = _wk(po.promised_week) - _wk(po.order_week)
    ck.add("BR4 promised_week >= order_week + lead_time_weeks", "business_rule",
           po.po_id[(gap < need) & (po.status != "CANCELLED").to_numpy()].tolist())

    contract = t["supplier_sku"].set_index(["supplier_id", "sku_id"])
    pack = t["sku"].set_index("sku_id").pack_size
    bad_uom, bad_moq = [], []
    for p, s, k, u, q, rq, st in zip(po.po_id, po.supplier_id, po.sku_id, po.order_uom, po.order_qty,
                                     po.requested_base_qty, po.status):
        if st == "CANCELLED":
            continue
        c = contract.loc[(s, k)]
        if u != c.order_uom or (u == "EA" and int(q) % int(pack[k]) != 0):
            bad_uom.append(p)
        if int(rq) < int(c.moq_base_qty) or int(rq) % int(c.order_multiple_base_qty) != 0:
            bad_moq.append(p)
    ck.add("BR5 PO unit of measure matches contract and pack multiple", "business_rule", bad_uom)
    ck.add("BR7 requested qty >= MOQ and multiple of order multiple", "business_rule", bad_moq)


def plan_checks(ck: Checks, t: dict, o: dict, exc: pd.DataFrame) -> None:
    pab = o["projected_balance"]
    pab = pab.sort_values(["sku_id", "location_id", "week"]).reset_index(drop=True)
    ck.add("PAB: closing = opening + receipts + production - forecast - dependent", "integrity",
           pab.balance_id[pab.closing_qty != pab.opening_qty + pab.receipt_qty + pab.production_qty
                          - pab.forecast_qty - pab.dependent_demand_qty].tolist())
    same = pab.sku_id.eq(pab.sku_id.shift()) & pab.location_id.eq(pab.location_id.shift())
    ck.add("PAB: opening[w+1] = closing[w] (week-by-week roll)", "integrity",
           pab.balance_id[same & (pab.opening_qty != pab.closing_qty.shift())].tolist())
    first = pab[~same]
    avail = t["inventory"].set_index(["sku_id", "location_id"]).available_qty
    ck.add("PAB: opening(W01) = inventory.available_qty", "integrity",
           first.balance_id[[int(avail.get((s, l), 0)) != int(q) for s, l, q in
                             zip(first.sku_id, first.location_id, first.opening_qty)]].tolist())
    key = ["sku_id", "location_id", "week"]
    f = t["forecast_demand"].groupby(key).forecast_qty.sum()
    g = pab.set_index(key)
    ck.add("PAB: forecast_qty reconciles to forecast_demand", "integrity",
           g.index[g.forecast_qty.to_numpy() != f.reindex(g.index).fillna(0).to_numpy()].map("|".join).tolist())
    pp = t["production_plan"].groupby(key).planned_qty.sum()
    ck.add("PAB: production_qty reconciles to production_plan", "integrity",
           g.index[g.production_qty.to_numpy() != pp.reindex(g.index).fillna(0).to_numpy()].map("|".join).tolist())
    rl = o["receipt_line"].groupby(key).qty_base.sum()
    ck.add("PAB: receipt_qty reconciles to receipt_line", "integrity",
           g.index[g.receipt_qty.to_numpy() != rl.reindex(g.index).fillna(0).to_numpy()].map("|".join).tolist())
    # dependent demand recomputed from BOM x production plan
    bom = t["bom"]
    dep = t["production_plan"].merge(bom, left_on="sku_id", right_on="parent_sku_id")
    dep["q"] = dep.planned_qty * dep.qty_per
    dep = dep.groupby(["component_sku_id", "location_id", "week"]).q.sum()
    dep.index.names = key
    ck.add("PAB: dependent_demand_qty = sum(parent planned_qty * qty_per)", "integrity",
           g.index[g.dependent_demand_qty.to_numpy() != dep.reindex(g.index).fillna(0).to_numpy()].map("|".join).tolist())
    # receipt lines trace to valid, non-cancelled POs and never exceed PO quantity
    po = t["purchase_order"].set_index("po_id")
    rlx = o["receipt_line"]
    ck.add("receipt_line: never credits a CANCELLED PO", "integrity",
           rlx.receipt_line_id[(rlx.po_id.map(po.status) == "CANCELLED") & (rlx.qty_base > 0)].tolist())

    # shortages
    sh = o["shortage"]
    closing = {(s, l): grp.closing_qty.to_numpy() for (s, l), grp in pab.groupby(["sku_id", "location_id"])}
    bad_qty, bad_run = [], []
    for r in sh.itertuples(index=False):
        c = closing[(r.sku_id, r.location_id)]
        a, b = cal.index(r.start_week), cal.index(r.end_week)
        if int(-c[a - 1:b].min()) != r.shortage_qty:
            bad_qty.append(r.shortage_id)
        if (c[a - 1:b] >= 0).any() or (a > 1 and c[a - 2] < 0) or (b < H and c[b] < 0):
            bad_run.append(r.shortage_id)
    ck.add("shortage_qty = -min(closing) over the run", "integrity", bad_qty)
    ck.add("shortage run boundaries match negative-balance weeks", "integrity", bad_run)
    neg_rows = pab[pab.in_shortage]
    covered = set()
    for r in sh.itertuples(index=False):
        for w in range(cal.index(r.start_week), cal.index(r.end_week) + 1):
            covered.add((r.sku_id, r.location_id, w))
    ck.add("every negative-balance week belongs to a shortage", "integrity",
           neg_rows.balance_id[[(s, l, cal.index(w)) not in covered for s, l, w in
                                zip(neg_rows.sku_id, neg_rows.location_id, neg_rows.week)]].tolist())

    cs = o["shortage_cause"]
    tot = cs.groupby("shortage_id").contributed_qty.sum()
    ck.add("every shortage has explainable causes summing to shortage_qty", "integrity",
           sh.shortage_id[sh.shortage_id.map(tot).fillna(-1).astype(int) != sh.shortage_qty].tolist())
    ck.add("cause contributions are positive", "integrity", cs.cause_id[cs.contributed_qty <= 0].tolist())

    # mitigations
    mo = o["mitigation_option"]
    sel = mo[mo.selected]
    ck.add("mitigated_qty + residual_qty consistent with selected options", "integrity",
           sh.shortage_id[(sh.mitigated_qty < 0) | (sh.residual_qty < 0)].tolist())
    accept_sel = sel[sel.option_type == "ACCEPT_SHORTFALL"].set_index("shortage_id").selected_qty
    ck.add("residual qty is explicitly accepted (ACCEPT_SHORTFALL selected)", "integrity",
           sh.shortage_id[(sh.residual_qty > 0) & (sh.shortage_id.map(accept_sel).fillna(0) != sh.residual_qty)].tolist())
    ck.add("only feasible options are selected", "integrity", sel.mitigation_id[~sel.feasible.astype(bool)].tolist())
    subs = t["sku_substitute"]
    ok = {(a, b) for a, b, x in zip(subs.sku_id, subs.substitute_sku_id, subs.approved) if bool(x)}
    short_sku = sh.set_index("shortage_id").sku_id
    ss_sel = sel[sel.option_type == "SUBSTITUTE"]
    ck.add("policy: selected substitutes are APPROVED", "integrity",
           ss_sel.mitigation_id[[(short_sku[s], x) not in ok for s, x in zip(ss_sel.shortage_id, ss_sel.source_id)]].tolist())
    status = t["supplier"].set_index("supplier_id").status
    po_sel = sel[sel.option_type.isin(["PLACE_PO", "EXPEDITE"])]
    ck.add("policy: no PO/expedite placed with an ON_HOLD supplier", "integrity",
           po_sel.mitigation_id[po_sel.source_id.map(status) != "ACTIVE"].tolist())
    lt = t["lead_time"].set_index(["supplier_id", "location_id"]).lead_time_weeks
    short_loc = sh.set_index("shortage_id").location_id
    bad_lt = []
    for r in po_sel.itertuples(index=False):
        L = int(lt[(r.source_id, short_loc[r.shortage_id])])
        need = L if r.option_type == "PLACE_PO" else int(math.ceil(L / 2))
        if cal.index(r.arrival_week) - cal.index(r.order_week) != need or cal.index(r.order_week) < SNAPSHOT_WEEK:
            bad_lt.append(r.mitigation_id)
    ck.add("policy: PO/expedite arrival honours (expedited) lead time", "integrity", bad_lt)
    led = o["capacity_ledger"]
    contract = t["supplier_sku"].set_index(["supplier_id", "sku_id"])
    supl = led[led.resource_type == "SUPPLIER_CAPACITY"].merge(mo[["mitigation_id", "shortage_id"]], on="mitigation_id")
    bad_moq = [m for m, s, sid, q in zip(supl.mitigation_id, supl.shortage_id, supl.resource_id, supl.qty_base)
               if q < contract.loc[(sid, short_sku[s])].moq_base_qty or q % contract.loc[(sid, short_sku[s])].order_multiple_base_qty]
    ck.add("policy: mitigation POs respect MOQ and order multiple", "integrity", bad_moq)

    # capacity: cleaned confirmed load + mitigation draws <= capacity
    corr = {}
    for it, rid, v in zip(exc.issue_type, exc.record_id, exc.suggested_value):
        corr.setdefault(it, {})[rid] = v
    load = {}
    for pid, s, pw, req, conf, st in zip(t["purchase_order"].po_id, t["purchase_order"].supplier_id,
                                          t["purchase_order"].promised_week, t["purchase_order"].requested_base_qty,
                                          t["purchase_order"].confirmed_base_qty, t["purchase_order"].status):
        if st == "CANCELLED":
            continue
        q = float(conf) if pd.notna(conf) else float(req)
        q = float(corr.get("UOM_MISMATCH", {}).get(pid, q))
        q = float(corr.get("SUPPLIER_CAPACITY_EXCEEDED", {}).get(pid, q))
        w = corr.get("SHORTAGE_WITHOUT_LEAD_TIME", {}).get(pid, pw)
        load[(s, w)] = load.get((s, w), 0) + q
    capd = t["supplier_capacity"].set_index(["supplier_id", "week"]).capacity_base_qty
    used = led[led.resource_type == "SUPPLIER_CAPACITY"].groupby(["resource_id", "week"]).qty_base.sum()
    ck.add("mitigations never exceed spare supplier capacity", "integrity",
           [f"{s}|{w}" for (s, w), u in used.items() if u > max(0, capd.get((s, w), 0) - load.get((s, w), 0))])
    pl = t["production_plan"].groupby(["location_id", "week"]).planned_qty.sum()
    pcap = t["production_capacity"].set_index(["location_id", "week"]).capacity_base_qty
    pused = led[led.resource_type == "PLANT_CAPACITY"].groupby(["resource_id", "week"]).qty_base.sum()
    ck.add("mitigations never exceed spare plant capacity", "integrity",
           [f"{l}|{w}" for (l, w), u in pused.items() if pl.get((l, w), 0) + u > pcap.get((l, w), 0)])
    # donor / substitute / component stock never pushed below safety stock
    pabi = pab.set_index(["sku_id", "location_id"])
    ss = pab.groupby(["sku_id", "location_id"]).safety_stock_qty.first()
    stock = led[led.resource_type.isin(["DONOR_STOCK", "SUBSTITUTE_STOCK", "COMPONENT_STOCK"])].copy()
    bad_stock = []
    if len(stock):
        stock["sku_id"] = stock.resource_id.str.split("|").str[0]
        stock["location_id"] = stock.resource_id.str.split("|").str[1]
        # donor stock leaves one transfer-lead week before arrival; others are drawn in the ledger week
        stock["start"] = _wk(stock.week) - np.where(stock.resource_type == "DONOR_STOCK", 2, 1)
        for (s, l), g2 in stock.groupby(["sku_id", "location_id"]):
            c = closing[(s, l)].copy()
            for st, q in zip(g2.start, g2.qty_base):
                c[max(st, 0):] -= q
            if c[max(int(g2.start.min()), 0):].min() < ss[(s, l)]:
                bad_stock.append(f"{s}|{l}")
    ck.add("donor/substitute/component stock stays >= safety stock after mitigation", "integrity", bad_stock)

    for name, seq_ok in (("shortage_event", ("DETECTED",)), ("mitigation_event", ("PROPOSED",))):
        ev = o[name]
        keycol = "shortage_id" if name == "shortage_event" else "mitigation_id"
        first_ev = ev.sort_values([keycol, "event_seq"]).groupby(keycol).event_type.first()
        ck.add(f"{name}: lifecycle starts with {seq_ok[0]}", "integrity", first_ev[first_ev != seq_ok[0]].index.tolist())
    final = o["shortage_event"].sort_values(["shortage_id", "event_seq"]).groupby("shortage_id").event_type.last()
    ck.add("shortage.status == final shortage event", "integrity",
           sh.shortage_id[sh.shortage_id.map(final) != sh.status].tolist())

    # actor / approval matrix
    mev = o["mitigation_event"].merge(mo[["mitigation_id", "option_type", "selected_cost"]], on="mitigation_id")
    selev = mev[mev.event_type == "SELECTED"]
    needs_om = (selev.option_type == "ACCEPT_SHORTFALL") | (selev.selected_cost >= P["ops_approval_threshold"])
    ck.add("approval: accepted shortfalls and spend >= threshold approved by OPERATIONS_MANAGER", "integrity",
           selev.event_id[needs_om != (selev.actor == "OPERATIONS_MANAGER")].tolist())
    prop = mev[mev.event_type == "PROPOSED"]
    logistic = prop.option_type.isin(["TRANSFER", "EXPEDITE"])
    ck.add("roles: TRANSFER/EXPEDITE proposed by LOGISTICS_ANALYST, others by PLANNER", "integrity",
           prop.event_id[np.where(logistic, "LOGISTICS_ANALYST", "PLANNER") != prop.actor].tolist())
    sev = o["shortage_event"]
    om = set(mo.shortage_id[mo.mitigation_id.isin(selev.mitigation_id[selev.actor == "OPERATIONS_MANAGER"])])
    last = sev.sort_values(["shortage_id", "event_seq"]).groupby("shortage_id").actor.last()
    ck.add("roles: shortage closed by OPERATIONS_MANAGER iff a selected option needed approval", "integrity",
           [s for s, a in last.items() if (a == "OPERATIONS_MANAGER") != (s in om)])
    used = set(o["mitigation_event"].actor) | set(sev.actor) | set(t["po_event"].actor) | set(exc.owner)
    ck.add("all five actors from the brief appear in the event history", "integrity",
           sorted({"SUPPLIER", "PLANNER", "CARRIER", "LOGISTICS_ANALYST", "OPERATIONS_MANAGER"} - used))


def ground_truth_checks(ck: Checks, t: dict, o: dict, gt: pd.DataFrame) -> None:
    po = t["purchase_order"].set_index("po_id")
    sh = o["shortage"]
    rl = o["receipt_line"]
    anomalies = gt[gt.expected_flag.astype(bool)]
    tabs_ids = {"purchase_order": set(t["purchase_order"].po_id), "inbound_shipment": set(t["inbound_shipment"].shipment_id),
                "inventory": set(t["inventory"].inventory_id), "supplier_capacity": set(t["supplier_capacity"].supplier_capacity_id)}
    ck.add("ground truth: every label traces to an existing source record", "integrity",
           gt.issue_id[[r not in tabs_ids.get(e, set()) for e, r in zip(gt.entity, gt.record_id)]].tolist())
    b = gt[gt.issue_type == "BOUNDARY_ZERO_BALANCE"]
    keys = set(zip(sh.sku_id, sh.location_id))
    ck.add("boundary: zero-balance rows produce no shortage", "integrity",
           b.issue_id[[tuple(x.split("|")) in keys for x in b.related_record_ids]].tolist())
    b = gt[gt.issue_type == "BOUNDARY_RECEIPT_AT_HORIZON_END"]
    w52 = set(rl.po_id[(rl.week == cal.label(H)) & (rl.qty_base > 0)])
    ck.add("boundary: receipt promised in W52 is counted in W52", "integrity", b.issue_id[~b.record_id.isin(w52)].tolist())
    b = gt[gt.issue_type == "BOUNDARY_PO_AT_MOQ"]
    moq = t["supplier_sku"].set_index(["supplier_id", "sku_id"]).moq_base_qty
    ck.add("boundary: MOQ POs requested exactly MOQ", "integrity",
           b.issue_id[[int(po.at[p, "requested_base_qty"]) != int(moq[(po.at[p, "supplier_id"], po.at[p, "sku_id"])])
                       for p in b.record_id]].tolist())
    ck.add("ground truth covers all 5 required edge-case types", "integrity",
           sorted({"INBOUND_DOUBLE_COUNT", "SUBSTITUTE_NOT_APPROVED", "SUPPLIER_CAPACITY_EXCEEDED",
                   "SHORTAGE_WITHOUT_LEAD_TIME", "UOM_MISMATCH"} - set(anomalies.issue_type)))


def explain(ck: Checks, gt: pd.DataFrame) -> dict:
    labelled = set(gt.record_id[gt.expected_flag.astype(bool)])
    boundary = set(gt.record_id[~gt.expected_flag.astype(bool)])
    explained_total, unexplained_total = 0, 0
    caught = set()
    for r in ck.results:
        if r["category"] != "business_rule":
            continue
        ids_ = set(r["_ids"])
        unexplained = sorted(ids_ - labelled)
        r["explained_by_ground_truth"] = len(ids_ & labelled)
        r["unexplained"] = len(unexplained)
        r["boundary_hits"] = len(ids_ & boundary)
        r["status"] = "PASS" if not unexplained else "FAIL"
        r["sample"] = unexplained[:5] if unexplained else r["sample"]
        explained_total += len(ids_ & labelled)
        unexplained_total += len(unexplained)
        caught |= ids_ & labelled
    return {"explained": explained_total, "unexplained": unexplained_total,
            "labelled_anomalies": len(labelled), "labelled_caught_by_rules": len(caught)}


def validate(t: dict, o: dict, exc: pd.DataFrame, gt: pd.DataFrame, db_path: Path) -> dict:
    ck = Checks()
    tabs = {**{k: t[k] for k in INPUT_TABLES}, **{k: o[k] for k in OUTPUT_TABLES if k != "exception"}, "exception": exc}
    schema_checks(ck, tabs)
    fk_checks(ck, tabs)
    sqlite_check(ck, tabs, db_path)
    input_checks(ck, t)
    business_rules(ck, t)
    plan_checks(ck, t, o, exc)
    ground_truth_checks(ck, t, o, gt)
    expl = explain(ck, gt)
    integ = [r for r in ck.results if r["category"] == "integrity"]
    failed = [r for r in ck.results if r["status"] == "FAIL"]
    for r in ck.results:
        r.pop("_ids", None)
    return {
        "overall_status": "PASS" if not failed else "FAIL",
        "integrity_checks": len(integ),
        "integrity_failed": sum(r["status"] == "FAIL" for r in integ),
        "business_rule_checks": len(ck.results) - len(integ),
        "business_rule_violations_explained_by_ground_truth": expl["explained"],
        "business_rule_violations_unexplained": expl["unexplained"],
        "labelled_anomalies": expl["labelled_anomalies"],
        "labelled_anomalies_caught_by_rules": expl["labelled_caught_by_rules"],
        "row_counts": {k: int(len(v)) for k, v in sorted(tabs.items())},
        "checks": ck.results,
    }


def to_markdown(v: dict, scale: str) -> str:
    out = [f"# Validation summary ({scale})", "",
           f"**Overall: {v['overall_status']}**  ",
           f"Integrity checks: {v['integrity_checks']} ({v['integrity_failed']} failed)  ",
           f"Business-rule checks: {v['business_rule_checks']}; violations explained by labelled anomalies: "
           f"{v['business_rule_violations_explained_by_ground_truth']}; unexplained: {v['business_rule_violations_unexplained']}  ",
           f"Labelled anomalies caught by at least one rule: {v['labelled_anomalies_caught_by_rules']} / {v['labelled_anomalies']}", "",
           "Business-rule violations are expected ONLY on records deliberately injected and labelled in "
           "`ground_truth.csv`; any unexplained violation fails validation.", "",
           "| Check | Category | Violations | Status | Notes |", "|---|---|---|---|---|"]
    for r in v["checks"]:
        note = ""
        if r["category"] == "business_rule":
            note = f"explained={r.get('explained_by_ground_truth', 0)}, unexplained={r.get('unexplained', 0)}"
        elif r["violations"]:
            note = ", ".join(r["sample"])
        out.append(f"| {r['check']} | {r['category']} | {r['violations']} | {r['status']} | {note} |")
    out += ["", "## Row counts", "", "| Table | Rows |", "|---|---|"]
    out += [f"| {k} | {n:,} |" for k, n in v["row_counts"].items()]
    return "\n".join(out) + "\n"
