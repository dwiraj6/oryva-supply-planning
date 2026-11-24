"""Blind anomaly detector.

Reads ONLY input tables (never the labels file). Each rule emits exceptions with
a suggested correction that the cleaned plan applies (quarantine policy).

D1 INBOUND_DOUBLE_COUNT       >1 shipment per PO, or shipped qty > confirmed qty
D2 SUBSTITUTE_NOT_APPROVED    substitute_for_sku_id set but pair not APPROVED
D3 SUPPLIER_CAPACITY_EXCEEDED cumulative confirmed qty (by po_id) > weekly capacity
D4 SHORTAGE_WITHOUT_LEAD_TIME promised_week - order_week < lead_time_weeks
D5 UOM_MISMATCH               order_uom differs from the contracted supplier_sku.order_uom,
                              or an EA quantity is not a multiple of the pack size
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import calendar as cal
from . import ids


def detect(t: dict) -> pd.DataFrame:
    out = []
    po = t["purchase_order"]
    conf = po.confirmed_base_qty.astype("float64")

    # D1
    sh = t["inbound_shipment"].sort_values(["po_id", "shipment_id"])
    tot = sh.groupby("po_id").qty_base.sum()
    po_conf = po.set_index("po_id").confirmed_base_qty.astype("float64")
    for pid, g in sh.groupby("po_id"):
        cum = 0
        limit = po_conf.get(pid, np.nan)
        for k, (sid, q) in enumerate(zip(g.shipment_id, g.qty_base)):
            cum += int(q)
            if k > 0 or (not np.isnan(limit) and cum > limit):
                out.append(("INBOUND_DOUBLE_COUNT", "inbound_shipment", sid, f"{pid}|{g.shipment_id.iloc[0]}",
                            "D1: more than one ASN for the PO / shipped qty exceeds confirmed qty",
                            f"shipments={len(g)};shipped={int(tot[pid])};confirmed={'' if np.isnan(limit) else int(limit)}", "0"))

    # D2
    subs = t["sku_substitute"]
    approved = {(a, b) for a, b, ok in zip(subs.sku_id, subs.substitute_sku_id, subs.approved) if bool(ok)}
    status = {(a, b): s for a, b, s in zip(subs.sku_id, subs.substitute_sku_id, subs.review_status)}
    m = po.substitute_for_sku_id.notna()
    for pid, x, y in zip(po.po_id[m], po.sku_id[m], po.substitute_for_sku_id[m]):
        if (y, x) not in approved:
            out.append(("SUBSTITUTE_NOT_APPROVED", "purchase_order", pid, f"SUB-{y}-{x}",
                        "D2: substitute pair is not APPROVED", f"review_status={status.get((y, x), 'MISSING')}", x))

    # D3
    cap = {(s, w): int(c) for s, w, c in zip(t["supplier_capacity"].supplier_id, t["supplier_capacity"].week,
                                                t["supplier_capacity"].capacity_base_qty)}
    live = po[po.status.isin(["CONFIRMED", "SHIPPED"]) & conf.notna()].sort_values(["supplier_id", "promised_week", "po_id"])
    for (s, w), g in live.groupby(["supplier_id", "promised_week"]):
        c = cap.get((s, w))
        if c is None:
            continue
        cum = 0
        for pid, q in zip(g.po_id, g.confirmed_base_qty):
            before = cum
            cum += int(q)
            if cum > c:
                out.append(("SUPPLIER_CAPACITY_EXCEEDED", "purchase_order", pid, f"SCAP-{s}-{w}",
                            "D3: cumulative confirmed qty exceeds supplier weekly capacity",
                            f"load={cum};capacity={c}", str(max(c - before, 0))))

    # D4
    lt = t["lead_time"].set_index(["supplier_id", "location_id"]).lead_time_weeks
    ow = cal.indices(po.order_week)
    pw = cal.indices(po.promised_week)
    need = np.array([int(lt.get((s, l), 0)) for s, l in zip(po.supplier_id, po.location_id)])
    bad = (pw - ow < need) & (po.status != "CANCELLED").to_numpy()
    for i in np.where(bad)[0]:
        out.append(("SHORTAGE_WITHOUT_LEAD_TIME", "purchase_order", po.po_id.iat[i],
                    f"LT-{po.supplier_id.iat[i]}-{po.location_id.iat[i]}",
                    "D4: promised_week earlier than order_week + lead_time_weeks",
                    f"order={po.order_week.iat[i]};promised={po.promised_week.iat[i]};lead_time={need[i]}",
                    cal.label(int(ow[i] + need[i]))))

    # D5
    contract = t["supplier_sku"].set_index(["supplier_id", "sku_id"]).order_uom
    pack = t["uom_conversion"][t["uom_conversion"].from_uom == "CASE"].set_index("sku_id").factor
    for pid, s, k, u, q, st in zip(po.po_id, po.supplier_id, po.sku_id, po.order_uom, po.order_qty, po.status):
        if st == "CANCELLED":
            continue
        cu = contract.get((s, k))
        pk = int(pack[k])
        off_contract = cu is not None and cu != u
        not_multiple = u == "EA" and int(q) % pk != 0
        if off_contract or not_multiple:
            fixed = int(q) * pk if u == "EA" else int(q)
            out.append(("UOM_MISMATCH", "purchase_order", pid, f"UOM-{k}-CASE",
                        "D5: order_uom deviates from contract" + (" and EA qty not a pack multiple" if not_multiple else ""),
                        f"order_qty={int(q)};order_uom={u};contract_uom={cu};pack={pk}", str(fixed)))

    df = pd.DataFrame(out, columns=["issue_type", "entity", "record_id", "related_record_ids", "rule",
                                    "observed_value", "suggested_value"])
    df["owner"] = np.where(df.issue_type == "INBOUND_DOUBLE_COUNT", "LOGISTICS_ANALYST", "PLANNER")
    df = df.sort_values(["issue_type", "record_id"], kind="mergesort").reset_index(drop=True)
    df["exception_id"] = ids.seq("EXC-", len(df), 6)
    return df


def corrections(exc: pd.DataFrame) -> dict:
    out: dict[str, dict] = {}
    for it, rid, val in zip(exc.issue_type, exc.record_id, exc.suggested_value):
        out.setdefault(it, {})[rid] = val
    return out
