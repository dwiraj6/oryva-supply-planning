"""Planning run: projected balance -> shortages -> causes -> priority -> mitigations.

The official plan is the CLEANED plan (detector corrections applied). The raw
plan is computed alongside so the impact of each data anomaly is visible.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import calendar as cal
from . import detect as det
from . import engine
from . import ids
from .config import HORIZON_WEEKS, P, SNAPSHOT_WEEK

H = HORIZON_WEEKS
CAUSE_ORDER = ["DEMAND_SPIKE", "DEPENDENT_DEMAND", "SUPPLIER_CAPACITY_CUT", "CANCELLED_PO",
               "SUPPLIER_DELAY", "TRANSPORT_DELAY"]
SNAP = cal.label(SNAPSHOT_WEEK)


def _runs(neg: np.ndarray):
    runs, start = [], None
    for w, v in enumerate(neg):
        if v and start is None:
            start = w
        if not v and start is not None:
            runs.append((start, w - 1))
            start = None
    if start is not None:
        runs.append((start, len(neg) - 1))
    return runs


def _deficit(C: np.ndarray, row: int, s: int, e: int) -> int:
    return int(max(0, -C[row, s:e + 1].min()))


def run(t: dict, exceptions: pd.DataFrame) -> dict:
    corr = det.corrections(exceptions)
    base = engine.base_plan(t, corr)
    idx, F, U, Pm, D, O, lines, R, C, SS = (base[k] for k in ("idx", "F", "U", "P", "D", "O", "lines", "R", "C", "SS"))
    n = idx.n

    raw_lines = engine.receipt_lines(t, idx, None)
    C_raw = engine.balance(O, engine.receipts(raw_lines, n), Pm, F, D)

    # ---- counterfactual scenarios (cumulative removal, fixed order)
    F1, Z = F - U, np.zeros_like(D)
    R_cut = engine.receipts(lines, n, "q_no_cut", "w_actual")
    R_cc = engine.receipts(lines, n, "q_no_cut_cancel", "w_actual")
    R_sd = engine.receipts(lines, n, "q_no_cut_cancel", "w_no_sd")
    R_td = engine.receipts(lines, n, "q_no_cut_cancel", "w_no_sd_td")
    scen = [C,
            engine.balance(O, R, Pm, F1, D),
            engine.balance(O, R, Pm, F1, Z),
            engine.balance(O, R_cut, Pm, F1, Z),
            engine.balance(O, R_cc, Pm, F1, Z),
            engine.balance(O, R_sd, Pm, F1, Z),
            engine.balance(O, R_td, Pm, F1, Z)]

    # ---- evidence lookups
    dem = t["forecast_demand"]
    spikes = dem[dem.uplift_qty > 0]
    spike_ev: dict = {}
    for s, l, w, did in zip(spikes.sku_id, spikes.location_id, cal.indices(spikes.week), spikes.demand_id):
        spike_ev.setdefault((s, l), []).append((w, did))
    parents_of: dict = {}
    for p, c, bid in zip(t["bom"].parent_sku_id, t["bom"].component_sku_id, t["bom"].bom_id):
        parents_of.setdefault(c, []).append(bid)
    lines_by_row = {r: g for r, g in lines.groupby("row")}

    def evidence(cause, row, s, l, end_w):
        g = lines_by_row.get(row)
        if cause == "DEMAND_SPIKE":
            ev = [d for w, d in spike_ev.get((s, l), []) if w <= end_w]
        elif cause == "DEPENDENT_DEMAND":
            ev = parents_of.get(s, [])
        elif g is None:
            ev = []
        elif cause == "SUPPLIER_CAPACITY_CUT":
            m = (g.q_no_cut > g.q_actual) & (g.w_actual <= end_w)
            ev = g.po_id[m].tolist()
        elif cause == "CANCELLED_PO":
            m = (g.q_no_cut_cancel > g.q_no_cut) & (g.w_actual <= end_w)
            ev = g.po_id[m].tolist()
        elif cause == "SUPPLIER_DELAY":
            m = (g.w_no_sd < g.w_actual) & (g.w_no_sd <= end_w)
            ev = g.po_id[m].tolist()
        elif cause == "TRANSPORT_DELAY":
            m = (g.w_no_sd_td < g.w_no_sd) & (g.w_no_sd_td <= end_w)
            ev = g.shipment_id[m].dropna().tolist()
        else:
            ev = []
        ev = list(dict.fromkeys(ev))
        return "|".join(ev[:12]) + ("|..." if len(ev) > 12 else "") if ev else None

    # ---- shortages
    sku = t["sku"].set_index("sku_id")
    ss_tab = t["supplier_sku"]
    sup_status = t["supplier"].set_index("supplier_id").status.to_dict()
    lt_map = {(a, b): int(c) for a, b, c in zip(t["lead_time"].supplier_id, t["lead_time"].location_id,
                                                 t["lead_time"].lead_time_weeks)}
    sups_of: dict = {}
    for r in ss_tab.sort_values(["sku_id", "is_primary", "supplier_id"], ascending=[True, False, True]).itertuples(index=False):
        sups_of.setdefault(r.sku_id, []).append(r)

    recs, cause_recs = [], []
    for row in np.where((C < 0).any(axis=1))[0]:
        s, l = idx.rows.sku_id[row], idx.rows.location_id[row]
        for a, b in _runs(C[row] < 0):
            qty = _deficit(C, row, a, b)
            peak = a + int(np.argmin(C[row, a:b + 1]))
            defs = [_deficit(sc, row, a, b) for sc in scen]
            parts = []
            for k, cause in enumerate(CAUSE_ORDER):
                contrib = defs[k] - defs[k + 1]
                if contrib > 0:
                    parts.append((cause, contrib))
            if defs[-1] > 0:
                parts.append(("BASE_SUPPLY_GAP", defs[-1]))
            if sku.at[s, "make_or_buy"] == "MAKE":
                min_lt = P["production_lead_weeks"]
            else:
                lts = [lt_map[(o.supplier_id, l)] for o in sups_of.get(s, [])
                       if sup_status.get(o.supplier_id) == "ACTIVE" and (o.supplier_id, l) in lt_map]
                min_lt = min(lts) if lts else 99
            recs.append({"row": row, "sku_id": s, "location_id": l, "a": a + 1, "b": b + 1, "peak": peak + 1,
                         "shortage_qty": qty, "min_lt": min_lt, "parts": parts,
                         "visible_raw": bool((C_raw[row, a:b + 1] < 0).any())})
    sh = pd.DataFrame(recs)
    if len(sh) == 0:
        sh = pd.DataFrame(columns=["row", "sku_id", "location_id", "a", "b", "peak", "shortage_qty", "min_lt", "parts", "visible_raw"])
    sh = sh.sort_values(["a", "sku_id", "location_id"], kind="mergesort").reset_index(drop=True)
    sh["shortage_id"] = [ids.shortage(i) for i in range(1, len(sh) + 1)]
    sh["recoverable"] = (sh.a - SNAPSHOT_WEEK) >= sh.min_lt

    # ---- priority (R9)
    margin = sh.sku_id.map(sku.unit_price - sku.unit_cost).astype(float)
    weight = sh.sku_id.map(sku.abc_class).map(P["abc_weight"]).astype(float)
    urgency = 0.5 ** ((sh.a - SNAPSHOT_WEEK) / P["urgency_halflife_weeks"])
    raw_score = sh.shortage_qty * margin * weight * urgency
    sh["priority_score"] = (100 * raw_score / raw_score.max()).round(4) if len(sh) else []
    sh = sh.sort_values(["priority_score", "shortage_id"], ascending=[False, True], kind="mergesort")
    sh["priority_rank"] = np.arange(1, len(sh) + 1)
    sh = sh.sort_values("shortage_id").reset_index(drop=True)

    for r in sh.itertuples(index=False):
        for k, (cause, q) in enumerate(r.parts, start=1):
            cause_recs.append({"cause_id": f"CAU-{r.shortage_id}-{k:02d}", "shortage_id": r.shortage_id,
                               "cause_type": cause, "contributed_qty": q,
                               "share_pct": round(100 * q / r.shortage_qty, 2),
                               "source_record_ids": evidence(cause, r.row, r.sku_id, r.location_id, r.b)
                               if cause != "BASE_SUPPLY_GAP" else f"INV-{r.sku_id}-{r.location_id}"})

    mit = _mitigate(t, idx, C, SS, sh, sku, sups_of, lt_map, sup_status, corr, Pm)

    # ---- assemble outputs
    sel = mit["options"][mit["options"].selected & (mit["options"].option_type != "ACCEPT_SHORTFALL")]
    mitigated = sel.groupby("shortage_id").selected_qty.sum()
    need = mit["need"]
    sh["mitigated_qty"] = sh.shortage_id.map(mitigated).fillna(0).astype(int)
    sh["need"] = sh.shortage_id.map(need).astype(int)
    sh["mitigated_qty"] = np.minimum(sh.mitigated_qty, sh.need)
    sh["residual_qty"] = sh.need - sh.mitigated_qty
    sh["fill_pct"] = np.where(sh.need > 0, 100 * sh.mitigated_qty / sh.need.where(sh.need > 0, 1), 100.0).round(2)
    sh["status"] = np.select([sh.need == 0, sh.residual_qty == 0, sh.mitigated_qty > 0],
                             ["COVERED_BY_PRIOR_MITIGATION", "MITIGATED", "PARTIALLY_MITIGATED"], "UNMITIGATED")

    shortage = pd.DataFrame({
        "shortage_id": sh.shortage_id, "sku_id": sh.sku_id, "location_id": sh.location_id,
        "start_week": cal.labels(sh.a.astype(int)) if len(sh) else [], "end_week": cal.labels(sh.b.astype(int)) if len(sh) else [],
        "peak_week": cal.labels(sh.peak.astype(int)) if len(sh) else [], "shortage_qty": sh.shortage_qty,
        "recoverable": sh.recoverable, "min_lead_time_weeks": sh.min_lt, "priority_score": sh.priority_score,
        "priority_rank": sh.priority_rank, "visible_in_raw_plan": sh.visible_raw, "mitigated_qty": sh.mitigated_qty,
        "residual_qty": sh.residual_qty, "fill_pct": sh.fill_pct, "status": sh.status,
    })

    # shortage events
    # shortage events: the planner detects and proposes; the plan is closed by the operations
    # manager whenever any selected option needed their approval, otherwise by the planner
    mev, mopt = mit["events"], mit["options"]
    om_mits = set(mev.mitigation_id[(mev.event_type == "SELECTED") & (mev.actor == "OPERATIONS_MANAGER")])
    om_shorts = set(mopt.shortage_id[mopt.mitigation_id.isin(om_mits)])
    sev = []
    for r in shortage.itertuples(index=False):
        k = 1
        sev.append((r.shortage_id, k, "DETECTED", "PLANNER", f"qty={r.shortage_qty};start={r.start_week};rank={r.priority_rank}"))
        if r.status != "COVERED_BY_PRIOR_MITIGATION":
            k += 1
            sev.append((r.shortage_id, k, "MITIGATION_PROPOSED", "PLANNER", None))
        closer = "OPERATIONS_MANAGER" if r.shortage_id in om_shorts else "PLANNER"
        sev.append((r.shortage_id, k + 1, r.status, closer, f"fill_pct={r.fill_pct}"))
    sev = pd.DataFrame(sev, columns=["shortage_id", "event_seq", "event_type", "actor", "detail"])
    sev["event_id"] = ids.seq("SHE-2026-", len(sev), 7)
    sev["event_week"] = SNAP

    pab = _pab_table(idx, O, R, Pm, F, D, C, SS)
    rl = lines[(lines.w_actual <= H)].copy()
    rl["receipt_line_id"] = ids.seq("RCL-2026-", len(rl), 7)
    rl["week"] = cal.labels(rl.w_actual)
    rl["qty_base"] = rl.q_actual

    return {
        "receipt_line": rl, "projected_balance": pab, "shortage": shortage,
        "shortage_cause": pd.DataFrame(cause_recs, columns=["cause_id", "shortage_id", "cause_type", "contributed_qty", "share_pct", "source_record_ids"]),
        "mitigation_option": mit["options"], "capacity_ledger": mit["ledger"],
        "shortage_event": sev, "mitigation_event": mit["events"],
        "_raw": {"C_raw": C_raw, "C": C, "idx": idx, "raw_lines": raw_lines, "lines": lines},
    }


def _pab_table(idx, O, R, Pm, F, D, C, SS) -> pd.DataFrame:
    n = idx.n
    opening = np.concatenate([O[:, None], C[:, :-1]], axis=1)
    weeks = np.tile(cal.labels(np.arange(1, H + 1)), n)
    sku = np.repeat(idx.rows.sku_id.to_numpy(), H)
    loc = np.repeat(idx.rows.location_id.to_numpy(), H)
    df = pd.DataFrame({
        "sku_id": sku, "location_id": loc, "week": weeks, "opening_qty": opening.ravel(),
        "receipt_qty": R.ravel(), "production_qty": Pm.ravel(), "forecast_qty": F.ravel(),
        "dependent_demand_qty": D.ravel(), "closing_qty": C.ravel(), "safety_stock_qty": np.repeat(SS, H),
    })
    df["below_safety_stock"] = df.closing_qty < df.safety_stock_qty
    df["in_shortage"] = df.closing_qty < 0
    df["balance_id"] = "PAB-" + df.sku_id + "-" + df.location_id + "-" + df.week
    return df


# ====================================================================== mitigation
def _mitigate(t, idx, C, SS, sh, sku, sups_of, lt_map, sup_status, corr, Pm):
    n = idx.n
    SM = np.minimum.accumulate(C[:, ::-1], axis=1)[:, ::-1]           # suffix minimum of closing
    rows_of_sku: dict = {}
    for r, s in zip(idx.rows.row, idx.rows.sku_id):
        rows_of_sku.setdefault(s, []).append(r)
    subs = t["sku_substitute"]
    subs_of: dict = {}
    for r in subs.itertuples(index=False):
        subs_of.setdefault(r.sku_id, []).append(r)
    bom_of: dict = {}
    for p, c, q in zip(t["bom"].parent_sku_id, t["bom"].component_sku_id, t["bom"].qty_per):
        bom_of.setdefault(p, []).append((c, int(q)))

    # supplier load (cleaned) by promised week
    po = t["purchase_order"]
    capf = corr.get("SUPPLIER_CAPACITY_EXCEEDED", {})
    uomf = corr.get("UOM_MISMATCH", {})
    ltf = corr.get("SHORTAGE_WITHOUT_LEAD_TIME", {})
    sup_load: dict = {}
    for pid, s, pw, req, conf, st in zip(po.po_id, po.supplier_id, po.promised_week, po.requested_base_qty,
                                          po.confirmed_base_qty, po.status):
        if st == "CANCELLED":
            continue
        q = float(conf) if pd.notna(conf) else float(req)
        if pid in uomf:
            q = float(uomf[pid])
        if pid in capf:
            q = float(capf[pid])
        w = cal.index(ltf[pid]) if pid in ltf else cal.index(pw)
        sup_load[(s, w)] = sup_load.get((s, w), 0) + q
    sup_cap = {(s, cal.index(w)): int(c) for s, w, c in zip(t["supplier_capacity"].supplier_id,
                                                            t["supplier_capacity"].week, t["supplier_capacity"].capacity_base_qty)}
    plant_cap = {(l, cal.index(w)): int(c) for l, w, c in zip(t["production_capacity"].location_id,
                                                              t["production_capacity"].week, t["production_capacity"].capacity_base_qty)}
    plant_load: dict = {}
    for l, w, q in zip(t["production_plan"].location_id, t["production_plan"].week, t["production_plan"].planned_qty):
        k = (l, cal.index(w))
        plant_load[k] = plant_load.get(k, 0) + int(q)

    used_sup: dict = {}
    used_plant: dict = {}
    reserved = np.zeros(n, dtype=np.int64)
    adds = [[] for _ in range(n)]
    options, ledger, events = [], [], []
    need_map = {}

    def sup_spare(s, w):
        if not (1 <= w <= H):
            return 0
        return max(0, int(sup_cap.get((s, w), 0) - sup_load.get((s, w), 0) - used_sup.get((s, w), 0)))

    def plant_spare(l, w):
        return max(0, int(plant_cap.get((l, w), 0) - plant_load.get((l, w), 0) - used_plant.get((l, w), 0)))

    def stock_surplus(r, from_w):          # usable stock at row r from week from_w (1-based) onwards
        if from_w < 1:
            from_w = 1
        return int(SM[r, from_w - 1] - SS[r] - reserved[r])

    order = sh.sort_values("priority_rank").itertuples(index=False)
    for x in order:
        row, s, l, a, b = x.row, x.sku_id, x.location_id, int(x.a), int(x.b)
        add = np.zeros(H, dtype=np.int64)
        for w, q in adds[row]:
            add[w - 1:] += q
        need = int(max(0, -(C[row, a - 1:b] + add[a - 1:b]).min()))
        need_map[x.shortage_id] = need
        if need == 0:
            continue
        unit_cost = float(sku.at[s, "unit_cost"])
        margin = float(sku.at[s, "unit_price"] - sku.at[s, "unit_cost"])
        opts = []

        # TRANSFER from other locations (donor keeps safety stock)
        donors = []
        if a - P["transfer_lead_weeks"] >= 1:
            for d in rows_of_sku[s]:
                if d == row:
                    continue
                sp = stock_surplus(d, a - P["transfer_lead_weeks"])
                if sp > 0:
                    donors.append((sp, idx.rows.location_id[d], d))
            donors.sort(key=lambda z: (-z[0], z[1]))
            for sp, dl, d in donors[:2]:
                q = min(need, sp)
                opts.append({"option_type": "TRANSFER", "source_id": dl, "order_week": a - P["transfer_lead_weeks"],
                             "arrival_week": a, "offered_qty": q,
                             "cost": P["transfer_fixed_cost"] + q * unit_cost * P["transfer_unit_cost_rate"],
                             "feasible": True, "rejection_reason": None, "_res": ("DONOR_STOCK", d)})
            if not donors:
                opts.append(_infeasible("TRANSFER", None, "NO_SURPLUS_AT_OTHER_LOCATIONS"))
        else:
            opts.append(_infeasible("TRANSFER", None, "TRANSFER_LEAD_TIME_EXCEEDS_NEED_DATE"))

        # SUBSTITUTE at same location (approved pairs only)
        for sub in subs_of.get(s, []):
            xr = idx.row_of.get((sub.substitute_sku_id, l))
            if xr is None:
                continue
            if not bool(sub.approved):
                opts.append(_infeasible("SUBSTITUTE", sub.substitute_sku_id, f"SUBSTITUTE_NOT_APPROVED({sub.review_status})"))
                continue
            sp = stock_surplus(xr, a)
            q = min(need, int(math.floor(max(sp, 0) * float(sub.conversion_ratio))))
            if q <= 0:
                opts.append(_infeasible("SUBSTITUTE", sub.substitute_sku_id, "NO_SUBSTITUTE_SURPLUS"))
                continue
            xc = float(sku.at[sub.substitute_sku_id, "unit_cost"])
            opts.append({"option_type": "SUBSTITUTE", "source_id": sub.substitute_sku_id, "order_week": None,
                         "arrival_week": a, "offered_qty": q,
                         "cost": P["substitute_fixed_cost"] + q * max(0.0, xc - unit_cost),
                         "feasible": True, "rejection_reason": None, "_res": ("SUBSTITUTE_STOCK", xr)})

        # PRODUCE (MAKE SKUs at plants)
        if sku.at[s, "make_or_buy"] == "MAKE":
            pw = a - P["production_lead_weeks"]
            if pw < 1:
                opts.append(_infeasible("PRODUCE", l, "PRODUCTION_LEAD_TIME_EXCEEDS_NEED_DATE"))
            else:
                cap_q = plant_spare(l, pw)
                comp_q = need
                comp_rows = []
                for c, qp in bom_of.get(s, []):
                    cr = idx.row_of.get((c, l))
                    avail = stock_surplus(cr, pw) if cr is not None else 0
                    comp_q = min(comp_q, max(0, avail) // qp)
                    comp_rows.append((cr, qp))
                q = min(need, cap_q, comp_q)
                if q <= 0:
                    why = "PLANT_CAPACITY_FULL" if cap_q <= 0 else "COMPONENT_SHORTAGE"
                    opts.append(_infeasible("PRODUCE", l, why))
                else:
                    opts.append({"option_type": "PRODUCE", "source_id": l, "order_week": pw, "arrival_week": a,
                                 "offered_qty": q,
                                 "cost": P["produce_fixed_cost"] + q * unit_cost * P["produce_unit_cost_rate"],
                                 "feasible": True, "rejection_reason": None, "_res": ("PLANT", (l, pw, comp_rows))})

        # PLACE_PO / EXPEDITE with approved suppliers
        primary_cost = None
        for o in sups_of.get(s, []):
            if primary_cost is None:
                primary_cost = float(o.unit_cost)
            prem = max(0.0, float(o.unit_cost) - primary_cost)
            if sup_status.get(o.supplier_id) != "ACTIVE":
                opts.append(_infeasible("PLACE_PO", o.supplier_id, "SUPPLIER_ON_HOLD"))
                continue
            ltw = lt_map.get((o.supplier_id, l))
            if ltw is None:
                opts.append(_infeasible("PLACE_PO", o.supplier_id, "NO_LEAD_TIME_FOR_LANE"))
                continue
            for kind, lead, fixed, rate in (("PLACE_PO", ltw, P["order_fixed_cost"], 0.0),
                                             ("EXPEDITE", int(math.ceil(ltw / 2)), P["expedite_fixed_cost"], P["expedite_unit_cost_rate"])):
                ow = a - lead
                if ow < SNAPSHOT_WEEK:
                    opts.append(_infeasible(kind, o.supplier_id, "LEAD_TIME_EXCEEDS_NEED_DATE"))
                    continue
                if kind == "EXPEDITE" and a - ltw >= SNAPSHOT_WEEK:
                    continue          # a normal PO already arrives in time
                q = _po_qty(need, o, sup_spare(o.supplier_id, a))
                if q <= 0:
                    opts.append(_infeasible(kind, o.supplier_id, "INSUFFICIENT_SUPPLIER_CAPACITY"))
                    continue
                opts.append({"option_type": kind, "source_id": o.supplier_id, "order_week": ow, "arrival_week": a,
                             "offered_qty": q, "cost": fixed + q * (prem + float(o.unit_cost) * rate),
                             "feasible": True, "rejection_reason": None,
                             "_res": ("SUPPLIER", (o.supplier_id, a, o, fixed, prem, rate))})

        opts.append({"option_type": "ACCEPT_SHORTFALL", "source_id": None, "order_week": None, "arrival_week": None,
                     "offered_qty": 0, "cost": need * margin, "feasible": True, "rejection_reason": None, "_res": None})

        for o in opts:
            o["fill_pct"] = round(100 * min(o["offered_qty"], need) / need, 2) if o["feasible"] else 0.0
            o["cost"] = round(float(o["cost"]), 2) if o["feasible"] else 0.0
            o["cost_per_unit"] = round(o["cost"] / min(o["offered_qty"], need), 4) if o["feasible"] and o["offered_qty"] > 0 else None
        feas = [o for o in opts if o["feasible"]]
        for o in feas:
            o["dominated"] = any((p["fill_pct"] >= o["fill_pct"] and p["cost"] <= o["cost"]) and
                                 (p["fill_pct"] > o["fill_pct"] or p["cost"] < o["cost"]) for p in feas if p is not o)

        # greedy selection by unit cost against live ledgers
        remaining = need
        cand = sorted([o for o in feas if o["option_type"] != "ACCEPT_SHORTFALL" and o["offered_qty"] > 0],
                      key=lambda o: (o["cost_per_unit"], o["option_type"], str(o["source_id"])))
        for o in cand:
            o.setdefault("selected_qty", 0)
            if remaining <= 0:
                o["_why"] = "NOT_NEEDED"
                continue
            res = o["_res"]
            kind = res[0]
            take, draw = 0, []
            if kind in ("DONOR_STOCK", "SUBSTITUTE_STOCK"):
                r = res[1]
                avail = stock_surplus(r, o["arrival_week"] - (P["transfer_lead_weeks"] if kind == "DONOR_STOCK" else 0))
                take = min(remaining, max(0, avail))
                if take > 0:
                    reserved[r] += take
                    draw.append((kind, f"{idx.rows.sku_id[r]}|{idx.rows.location_id[r]}", o["arrival_week"], take))
                    o["_cost_fn"] = (P["transfer_fixed_cost"] + take * unit_cost * P["transfer_unit_cost_rate"]) \
                        if kind == "DONOR_STOCK" else (P["substitute_fixed_cost"] + take * max(0.0, float(sku.at[o["source_id"], "unit_cost"]) - unit_cost))
                credited = take
            elif kind == "PLANT":
                l2, pw, comp_rows = res[1]
                q = min(remaining, plant_spare(l2, pw))
                for cr, qp in comp_rows:
                    q = min(q, max(0, stock_surplus(cr, pw)) // qp if cr is not None else 0)
                take = max(0, q)
                if take > 0:
                    used_plant[(l2, pw)] = used_plant.get((l2, pw), 0) + take
                    draw.append(("PLANT_CAPACITY", l2, pw, take))
                    for cr, qp in comp_rows:
                        reserved[cr] += take * qp
                        draw.append(("COMPONENT_STOCK", f"{idx.rows.sku_id[cr]}|{l2}", pw, take * qp))
                    o["_cost_fn"] = P["produce_fixed_cost"] + take * unit_cost * P["produce_unit_cost_rate"]
                credited = take
            else:  # SUPPLIER
                sid, w, ss_row, fixed, prem, rate = res[1]
                take = _po_qty(remaining, ss_row, sup_spare(sid, w))
                if take > 0:
                    used_sup[(sid, w)] = used_sup.get((sid, w), 0) + take
                    draw.append(("SUPPLIER_CAPACITY", sid, w, take))
                    o["_cost_fn"] = fixed + take * (prem + float(ss_row.unit_cost) * rate)
                credited = min(take, remaining)
            if take <= 0:
                o["_why"] = "RESOURCE_TAKEN_BY_HIGHER_PRIORITY_SHORTAGE"
                continue
            o["selected"] = True
            o["selected_qty"] = credited
            o["selected_cost"] = round(float(o["_cost_fn"]), 2)
            o["_draw"] = draw
            adds[row].append((a, take))
            remaining -= credited
        acc = opts[-1]
        if remaining > 0:
            acc["selected"] = True
            acc["selected_qty"] = remaining
            acc["selected_cost"] = round(remaining * margin, 2)

        for k, o in enumerate(opts, start=1):
            mid = ids.mitigation(x.shortage_id, k)
            o["mitigation_id"] = mid
            o["shortage_id"] = x.shortage_id
            o.setdefault("selected", False)
            o.setdefault("selected_qty", 0)
            o.setdefault("selected_cost", 0.0)
            o.setdefault("dominated", False)
            options.append(o)
            proposer = proposer_of(o["option_type"])
            events.append((mid, 1, "PROPOSED", proposer, o["rejection_reason"]))
            if o["selected"]:
                events.append((mid, 2, "SELECTED", approver_of(o["option_type"], o["selected_cost"]),
                               f"selected_qty={o['selected_qty']};selected_cost={o['selected_cost']}"))
            else:
                why = o["rejection_reason"] or o.get("_why") or ("DOMINATED" if o["dominated"] else "HIGHER_UNIT_COST_OR_NOT_NEEDED")
                events.append((mid, 2, "REJECTED", proposer, why))
            for kind, rid, w, q in o.get("_draw", []):
                ledger.append((mid, kind, rid, w, q))

    opt = pd.DataFrame(options)
    cols = ["mitigation_id", "shortage_id", "option_type", "source_id", "order_week", "arrival_week", "offered_qty",
            "cost", "cost_per_unit", "fill_pct", "feasible", "rejection_reason", "dominated", "selected",
            "selected_qty", "selected_cost"]
    if len(opt) == 0:
        opt = pd.DataFrame(columns=cols)
    else:
        for c in ("order_week", "arrival_week"):
            opt[c] = [cal.label(int(v)) if v is not None and not (isinstance(v, float) and np.isnan(v)) else None for v in opt[c]]
        opt = opt[cols]
    led = pd.DataFrame(ledger, columns=["mitigation_id", "resource_type", "resource_id", "w", "qty_base"])
    led["ledger_id"] = ids.seq("LED-2026-", len(led), 7)
    led["week"] = cal.labels(led.w) if len(led) else []
    ev = pd.DataFrame(events, columns=["mitigation_id", "event_seq", "event_type", "actor", "reason"])
    ev["event_id"] = ids.seq("MIE-2026-", len(ev), 7)
    ev["event_week"] = SNAP
    return {"options": opt, "ledger": led, "events": ev, "need": need_map,
            "sup_load": sup_load, "sup_cap": sup_cap, "used_sup": used_sup,
            "plant_load": plant_load, "plant_cap": plant_cap, "used_plant": used_plant}


def proposer_of(option_type: str) -> str:
    """Logistics analyst owns movement options (transfers, expedites); planner owns the rest."""
    return "LOGISTICS_ANALYST" if option_type in ("TRANSFER", "EXPEDITE") else "PLANNER"


def approver_of(option_type: str, selected_cost: float) -> str:
    """Approval matrix: accepted shortfalls and spend at/above the threshold need the operations manager."""
    if option_type == "ACCEPT_SHORTFALL" or selected_cost >= P["ops_approval_threshold"]:
        return "OPERATIONS_MANAGER"
    return proposer_of(option_type)


def _infeasible(kind, source, reason):
    return {"option_type": kind, "source_id": source, "order_week": None, "arrival_week": None, "offered_qty": 0,
            "cost": 0.0, "feasible": False, "rejection_reason": reason, "_res": None}


def _po_qty(need: int, ss_row, spare: int) -> int:
    """Order qty honouring MOQ and order multiple, limited by spare capacity."""
    mult = int(ss_row.order_multiple_base_qty)
    moq = int(ss_row.moq_base_qty)
    want = max(moq, int(math.ceil(need / mult)) * mult)
    can = (spare // mult) * mult
    q = min(want, can)
    return q if q >= moq else 0
