"""Core planning arithmetic: SKU-location index, demand/supply matrices,
receipt lines and projected available balance (PAB).

Rules (see docs/business_rules.md):
  R1  all quantities are converted to base unit EA
  R2  opening(W01) = inventory.on_hand - inventory.allocated
  R3  closing[w] = opening[w] + receipts[w] + production[w] - forecast[w] - dependent[w]
  R4  opening[w+1] = closing[w]
  R5  shipped PO -> receipt at shipment eta_week; unshipped PO -> latest promised week
      (DELAYED event overrides); cancelled PO -> no receipt
  R6  receipts dated before W01 are overdue and land in W01; after W52 are outside horizon
  R7  an approved substitute PO credits the SKU it substitutes for (x conversion_ratio)
  R8  dependent demand = sum(parent planned_qty * bom.qty_per) at the plant
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import calendar as cal
from .config import HORIZON_WEEKS

H = HORIZON_WEEKS


@dataclass
class Index:
    rows: pd.DataFrame          # sku_id, location_id, stocking_role, row
    row_of: dict

    @property
    def n(self) -> int:
        return len(self.rows)


def build_index(t: dict) -> Index:
    rows = t["sku_location"][["sku_id", "location_id", "stocking_role"]].sort_values(
        ["sku_id", "location_id"], kind="mergesort").reset_index(drop=True)
    rows["row"] = np.arange(len(rows))
    row_of = {(s, l): i for s, l, i in zip(rows.sku_id, rows.location_id, rows.row)}
    return Index(rows, row_of)


def _rows_for(idx: Index, sku: pd.Series, loc: pd.Series) -> np.ndarray:
    return np.array([idx.row_of.get((s, l), -1) for s, l in zip(sku, loc)], dtype=np.int64)


def _matrix(rows: np.ndarray, weeks: np.ndarray, qty: np.ndarray, n: int) -> np.ndarray:
    m = np.zeros((n, H), dtype=np.int64)
    ok = (rows >= 0) & (weeks >= 1) & (weeks <= H)
    np.add.at(m, (rows[ok], weeks[ok] - 1), qty[ok].astype(np.int64))
    return m


def demand_matrices(t: dict, idx: Index):
    d = t["forecast_demand"]
    rows = _rows_for(idx, d.sku_id, d.location_id)
    w = cal.indices(d.week)
    F = _matrix(rows, w, d.forecast_qty.to_numpy(dtype=np.int64), idx.n)
    U = _matrix(rows, w, d.uplift_qty.to_numpy(dtype=np.int64), idx.n)
    return F, U


def production_matrix(t: dict, idx: Index) -> np.ndarray:
    p = t["production_plan"]
    rows = _rows_for(idx, p.sku_id, p.location_id)
    return _matrix(rows, cal.indices(p.week), p.planned_qty.to_numpy(dtype=np.int64), idx.n)


def dependent_matrix(t: dict, idx: Index, P: np.ndarray) -> np.ndarray:
    D = np.zeros((idx.n, H), dtype=np.int64)
    bom = t["bom"]
    comps: dict[str, list] = {}
    for p, c, q in zip(bom.parent_sku_id, bom.component_sku_id, bom.qty_per):
        comps.setdefault(p, []).append((c, int(q)))
    for r, s, l in zip(idx.rows.row, idx.rows.sku_id, idx.rows.location_id):
        if s in comps and P[r].any():
            for c, q in comps[s]:
                cr = idx.row_of.get((c, l))
                if cr is not None:
                    D[cr] += P[r] * q
    return D


def opening(t: dict, idx: Index) -> np.ndarray:
    inv = t["inventory"]
    rows = _rows_for(idx, inv.sku_id, inv.location_id)
    o = np.zeros(idx.n, dtype=np.int64)
    ok = rows >= 0
    o[rows[ok]] = (inv.on_hand_qty.to_numpy(dtype=np.int64) - inv.allocated_qty.to_numpy(dtype=np.int64))[ok]
    return o


def safety_stock(t: dict, idx: Index, F: np.ndarray, D: np.ndarray) -> np.ndarray:
    ssw = t["sku"].set_index("sku_id").safety_stock_weeks
    weeks = idx.rows.sku_id.map(ssw).to_numpy(dtype=float)
    return np.ceil(weeks * (F + D).mean(axis=1)).astype(np.int64)


def receipt_lines(t: dict, idx: Index, corrections: dict | None = None) -> pd.DataFrame:
    """One line per supply contribution, carrying counterfactual variants.

    corrections: {issue_type: {record_id: suggested_value}} from the detector.
    Empty/None -> the raw (uncleaned) plan.
    """
    corr = corrections or {}
    dup = corr.get("INBOUND_DOUBLE_COUNT", {})
    sub_bad = corr.get("SUBSTITUTE_NOT_APPROVED", {})
    cap = corr.get("SUPPLIER_CAPACITY_EXCEEDED", {})
    lt_fix = corr.get("SHORTAGE_WITHOUT_LEAD_TIME", {})
    uom_fix = corr.get("UOM_MISMATCH", {})

    po = t["purchase_order"].copy()
    po["promised_w"] = cal.indices(po.promised_week)
    ev = t["po_event"]
    dl = ev[ev.event_type == "DELAYED"].sort_values(["po_id", "event_seq"]).groupby("po_id").last()
    po["delayed_w"] = po.po_id.map(dl.new_promised_week).map(lambda x: cal.index(x) if isinstance(x, str) else np.nan)

    subs = t["sku_substitute"]
    ratio = {(a, b): float(r) for a, b, r in zip(subs.sku_id, subs.substitute_sku_id, subs.conversion_ratio)}
    credited = []
    for sid, sf, loc, pid in zip(po.sku_id, po.substitute_for_sku_id, po.location_id, po.po_id):
        if isinstance(sf, str) and pid not in sub_bad and (sf, loc) in idx.row_of:
            credited.append((sf, ratio.get((sf, sid), 1.0)))
        else:
            credited.append((sid, 1.0))
    po["credit_sku"] = [c[0] for c in credited]
    po["credit_ratio"] = [c[1] for c in credited]
    po["row"] = _rows_for(idx, po.credit_sku, po.location_id)

    ships = t["inbound_shipment"].merge(po[["po_id", "row", "credit_sku", "location_id", "credit_ratio",
                                            "requested_base_qty", "confirmed_base_qty"]], on="po_id", how="left")
    shipped_pos = set(ships.po_id)
    lines = []

    # ---- shipment lines (R5)
    if len(ships):
        ships = ships.sort_values(["po_id", "shipment_id"]).reset_index(drop=True)
        first = ~ships.po_id.duplicated()
        eta = cal.indices(ships.eta_week)
        delay = ships.delay_weeks.to_numpy(dtype=np.int64)
        q = np.floor(ships.qty_base.to_numpy(dtype=float) * ships.credit_ratio.to_numpy()).astype(np.int64)
        cut = (ships.requested_base_qty.astype("float64") - ships.confirmed_base_qty.astype("float64")).fillna(0).to_numpy()
        cut = np.where(first, cut, 0).astype(np.int64)
        excl = ships.shipment_id.isin(dup).to_numpy()
        q_act = np.where(excl, 0, q)
        sl = pd.DataFrame({
            "po_id": ships.po_id, "shipment_id": ships.shipment_id, "sku_id": ships.credit_sku,
            "location_id": ships.location_id, "row": ships.row,
            "w_actual": eta, "w_no_sd": eta, "w_no_sd_td": eta - delay,
            "q_actual": q_act, "q_no_cut": np.where(excl, 0, q + cut),
            "q_no_cut_cancel": np.where(excl, 0, q + cut),
            "basis": "SHIPMENT_ETA",
            "adjustment": np.where(excl, "EXCLUDED_DUPLICATE_SHIPMENT", None),
        })
        lines.append(sl)

    # ---- unshipped PO lines (R5)
    ps = po[~po.po_id.isin(shipped_pos)].copy()
    canc = (ps.status == "CANCELLED").to_numpy()
    req = ps.requested_base_qty.astype("float64").to_numpy()
    conf = ps.confirmed_base_qty.astype("float64").to_numpy()
    base_q = np.where(np.isnan(conf), req, conf)
    promised = ps.promised_w.to_numpy(dtype=np.int64)
    delayed = ps.delayed_w.to_numpy(dtype=float)
    adj = np.array([None] * len(ps), dtype=object)

    pids = ps.po_id.to_numpy()
    corrected_promised = promised.copy()
    no_cut = np.where(np.isnan(conf), req, req)
    for i, pid in enumerate(pids):
        if pid in lt_fix:
            corrected_promised[i] = cal.index(lt_fix[pid])
            adj[i] = "CORRECTED_LEAD_TIME"
        if pid in uom_fix:
            base_q[i] = float(uom_fix[pid])
            no_cut[i] = float(uom_fix[pid])
            adj[i] = "CORRECTED_UOM"
        if pid in cap:
            base_q[i] = float(cap[pid])
            no_cut[i] = float(cap[pid])
            adj[i] = "CAPPED_TO_CAPACITY"
    shift = np.where(np.isnan(delayed), 0, delayed - promised).astype(np.int64)
    w_act = corrected_promised + shift
    ratio_arr = ps.credit_ratio.to_numpy()
    q_act = np.where(canc, 0, np.floor(base_q * ratio_arr)).astype(np.int64)
    q_nc = np.where(canc, 0, np.floor(no_cut * ratio_arr)).astype(np.int64)
    q_ncc = np.floor(np.where(canc, req, no_cut) * ratio_arr).astype(np.int64)
    adj = np.where(canc, "CANCELLED", adj)
    pl = pd.DataFrame({
        "po_id": pids, "shipment_id": None, "sku_id": ps.credit_sku.to_numpy(),
        "location_id": ps.location_id.to_numpy(), "row": ps.row.to_numpy(),
        "w_actual": w_act, "w_no_sd": corrected_promised, "w_no_sd_td": corrected_promised,
        "q_actual": q_act, "q_no_cut": q_nc, "q_no_cut_cancel": q_ncc,
        "basis": np.where(shift > 0, "PO_DELAYED", "PO_PROMISED"),
        "adjustment": adj,
    })
    lines.append(pl)
    out = pd.concat(lines, ignore_index=True)
    for c in ("w_actual", "w_no_sd", "w_no_sd_td"):
        out[c] = out[c].clip(lower=1)          # R6 overdue -> W01
    return out.sort_values(["po_id", "shipment_id"], na_position="first", kind="mergesort").reset_index(drop=True)


def receipts(lines: pd.DataFrame, n: int, qcol: str = "q_actual", wcol: str = "w_actual") -> np.ndarray:
    return _matrix(lines.row.to_numpy(dtype=np.int64), lines[wcol].to_numpy(dtype=np.int64),
                   lines[qcol].to_numpy(dtype=np.int64), n)


def balance(open_: np.ndarray, R: np.ndarray, P: np.ndarray, F: np.ndarray, D: np.ndarray) -> np.ndarray:
    return open_[:, None] + np.cumsum(R + P - F - D, axis=1)


def base_plan(t: dict, corrections: dict | None = None) -> dict:
    idx = build_index(t)
    F, U = demand_matrices(t, idx)
    P = production_matrix(t, idx)
    D = dependent_matrix(t, idx, P)
    O = opening(t, idx)
    lines = receipt_lines(t, idx, corrections)
    R = receipts(lines, idx.n)
    C = balance(O, R, P, F, D)
    return {"idx": idx, "F": F, "U": U, "P": P, "D": D, "O": O, "lines": lines, "R": R, "C": C,
            "SS": safety_stock(t, idx, F, D)}
