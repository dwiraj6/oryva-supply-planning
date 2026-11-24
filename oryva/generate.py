"""Synthetic data generator (brief Section 5, steps 2-7).

Order: masters -> bridges/reference -> demand -> production -> inventory ->
purchase orders -> capacity & confirmations -> shipments -> events ->
labelled boundary cases -> injected anomalies (+ ground truth).
Derived values (forecast_qty, available_qty, requested_base_qty, status,
capacity_constrained ...) are computed from source fields, never drawn.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import calendar as cal
from . import engine
from . import ids
from .config import CARRIERS, CATEGORIES, HORIZON_WEEKS, P, PACK_SIZES, REGIONS, Scale, SNAPSHOT_WEEK
from .rng import rng

H = HORIZON_WEEKS
CAT_COST = {"BEVERAGES": 2.5, "SNACKS": 1.8, "DAIRY": 3.0, "HOUSEHOLD": 6.0,
            "PERSONAL_CARE": 5.0, "ELECTRONICS": 45.0, "HARDWARE": 12.0, "PHARMA": 9.0}


# ============================================================ masters
def _skus(scale: Scale, seed: int):
    rows, latent = [], {}
    a, b, _ = P["abc_split"]
    for i in range(1, scale.n_skus + 1):
        r = rng(seed, "sku", i)
        cat = CATEGORIES[r.integers(len(CATEGORIES))]
        u = r.random()
        abc = "A" if u < a else ("B" if u < a + b else "C")
        mob = "MAKE" if r.random() < P["make_share"] else "BUY"
        pack = PACK_SIZES[r.integers(len(PACK_SIZES))]
        cost = round(float(r.lognormal(math.log(CAT_COST[cat]), 0.5)), 2) + 0.01
        price = round(cost * float(r.uniform(1.25, 1.9)), 2)
        lu = r.random()
        life = "ACTIVE" if lu < 0.90 else ("NEW" if lu < 0.96 else "PHASE_OUT")
        eff_from = f"2025-{int(r.integers(1, 13)):02d}-01" if life == "NEW" else "2024-01-01"
        level = P["level_median"][abc] * float(r.lognormal(0, P["level_sigma"]))
        sid = ids.sku(i)
        rows.append({
            "sku_id": sid, "sku_name": f"{cat.title().replace('_', ' ')} item {i:06d}", "category": cat,
            "abc_class": abc, "make_or_buy": mob, "base_uom": "EA", "pack_size": pack,
            "unit_cost": cost, "unit_price": price, "safety_stock_weeks": P["safety_stock_weeks"][abc],
            "lifecycle_status": life, "effective_from": eff_from,
            "effective_to": "2026-12-31" if life == "PHASE_OUT" else None,
        })
        latent[sid] = {"level": level}
    return pd.DataFrame(rows), latent


def _locations(scale: Scale, seed: int):
    rows, weight = [], {}
    for i in range(1, scale.n_locations + 1):
        r = rng(seed, "location", i)
        plant = (i - 1) % P["plant_every_n_locations"] == 0
        typ = "PLANT" if plant else ("DC" if r.random() < P["dc_share_of_non_plants"] else "WAREHOUSE")
        region = REGIONS[r.integers(len(REGIONS))]
        w = float(r.lognormal(0, P["location_weight_sigma"]))
        lid = ids.location(i)
        rows.append({"location_id": lid, "location_name": f"{region.title()} {typ.title()} {i:03d}",
                     "location_type": typ, "region": region,
                     "storage_capacity_units": int(round(float(r.uniform(50_000, 500_000)), -3))})
        weight[lid] = w
    return pd.DataFrame(rows), weight


def _suppliers(scale: Scale, seed: int):
    rows, latent = [], {}
    for i in range(1, scale.n_suppliers + 1):
        r = rng(seed, "supplier", i)
        region = REGIONS[r.integers(len(REGIONS))]
        rel = round(min(0.99, float(r.beta(8, 2))), 3)
        hold = r.random() < P["supplier_on_hold_share"]
        tight = r.random() < P["supplier_tight_share"]
        base_lt = int(np.clip(round(float(r.lognormal(math.log(4), 0.45))), 1, 12))
        sid = ids.supplier(i)
        rows.append({"supplier_id": sid, "supplier_name": f"Supplier {i:04d} {region.title()}",
                     "region": region, "reliability_score": rel,
                     "status": "ON_HOLD" if hold else "ACTIVE", "capacity_constrained": False})
        latent[sid] = {"tight": tight, "base_lt": base_lt, "rel": rel}
    return pd.DataFrame(rows), latent


# ============================================================ bridges / reference
def _assortment(skus, locs, loc_w, seed):
    plants = locs[locs.location_type == "PLANT"].location_id.tolist()
    others = locs[locs.location_type != "PLANT"].location_id.tolist()
    pw = np.array([loc_w[x] for x in others])
    pw = pw / pw.sum()
    rows = []
    for i, s in enumerate(skus.itertuples(), start=1):
        r = rng(seed, "assortment", i)
        if s.make_or_buy == "MAKE":
            k = min(len(plants), int(r.integers(1, 3)))
            chosen = sorted(r.choice(plants, k, replace=False).tolist())
        else:
            lo, hi = P["locations_per_sku"][s.abc_class]
            k = min(len(others), int(r.integers(lo, hi + 1)))
            chosen = sorted(r.choice(others, k, replace=False, p=pw).tolist())
        for lid in chosen:
            rows.append({"sku_id": s.sku_id, "location_id": lid, "stocking_role": "SELL"})
    return pd.DataFrame(rows)


def _bom(skus, assort, seed):
    buy = skus[skus.make_or_buy == "BUY"].sku_id.to_numpy()
    rows, extra = [], []
    for i, s in enumerate(skus.itertuples(), start=1):
        if s.make_or_buy != "MAKE":
            continue
        r = rng(seed, "bom", i)
        comps = sorted(r.choice(buy, int(r.integers(2, 5)), replace=False).tolist())
        for c in comps:
            rows.append({"bom_id": f"BOM-{s.sku_id}-{c}", "parent_sku_id": s.sku_id, "component_sku_id": c,
                         "qty_per": int(r.integers(1, 5)), "effective_from": "2025-01-01"})
        for lid in assort[assort.sku_id == s.sku_id].location_id:
            for c in comps:
                extra.append({"sku_id": c, "location_id": lid, "stocking_role": "COMPONENT"})
    bom = pd.DataFrame(rows, columns=["bom_id", "parent_sku_id", "component_sku_id", "qty_per", "effective_from"])
    assort = pd.concat([assort, pd.DataFrame(extra, columns=assort.columns)], ignore_index=True)
    assort = assort.drop_duplicates(["sku_id", "location_id"], keep="first")
    assort["sku_location_id"] = "SL-" + assort.sku_id + "-" + assort.location_id
    assort["effective_from"] = "2025-01-01"
    return bom, assort.sort_values("sku_location_id").reset_index(drop=True)


def _supplier_sku(skus, sku_lat, n_sup, seed):
    rows = []
    for i, s in enumerate(skus.itertuples(), start=1):
        if s.make_or_buy != "BUY":
            continue
        r = rng(seed, "supplier_sku", i)
        n = int(r.choice([1, 2, 3], p=[0.35, 0.45, 0.20]))
        sups = (r.choice(n_sup, min(n, n_sup), replace=False) + 1).tolist()
        level = sku_lat[s.sku_id]["level"]
        for j, k in enumerate(sups):
            primary = j == 0
            uc = s.unit_cost * float(r.uniform(0.97, 1.03) if primary else r.uniform(1.03, 1.20))
            moq = s.pack_size * max(1, int(round(level * float(r.uniform(0.5, 2.0)) / s.pack_size)))
            rows.append({"supplier_sku_id": f"SS-{ids.supplier(k)}-{s.sku_id}", "supplier_id": ids.supplier(k),
                         "sku_id": s.sku_id, "is_primary": primary, "unit_cost": round(uc, 2),
                         "moq_base_qty": moq, "order_multiple_base_qty": s.pack_size,
                         "order_uom": "CASE" if r.random() < P["case_uom_share"] else "EA",
                         "effective_from": "2025-01-01", "effective_to": None})
    return pd.DataFrame(rows)


def _substitutes(skus, assort, seed):
    locs_of = assort[assort.stocking_role == "SELL"].groupby("sku_id").location_id.apply(set).to_dict()
    buy = skus[skus.make_or_buy == "BUY"]
    by_cat = buy.groupby("category").sku_id.apply(list).to_dict()
    rows = []
    for i, s in enumerate(skus.itertuples(), start=1):
        if s.make_or_buy != "BUY":
            continue
        r = rng(seed, "substitute", i)
        if r.random() >= P["substitute_share"]:
            continue
        cands = [x for x in by_cat.get(s.category, []) if x != s.sku_id
                 and locs_of.get(x, set()) & locs_of.get(s.sku_id, set())]
        if not cands:
            continue
        x = cands[int(r.integers(len(cands)))]
        u = r.random()
        status = "APPROVED" if u < P["substitute_approved_share"] else ("PENDING" if u < 0.85 else "REJECTED")
        rows.append({"substitute_id": f"SUB-{s.sku_id}-{x}", "sku_id": s.sku_id, "substitute_sku_id": x,
                     "conversion_ratio": 1.0, "review_status": status, "approved": status == "APPROVED",
                     "approved_on": f"2025-{int(r.integers(1, 13)):02d}-15" if status == "APPROVED" else None})
    return pd.DataFrame(rows, columns=["substitute_id", "sku_id", "substitute_sku_id", "conversion_ratio",
                                       "review_status", "approved", "approved_on"])


def _lead_times(sup_sku, assort, locs, sups, sup_lat):
    region = locs.set_index("location_id").region.to_dict()
    sup_region = sups.set_index("supplier_id").region.to_dict()
    pairs = sup_sku[["supplier_id", "sku_id"]].merge(assort[["sku_id", "location_id"]], on="sku_id")
    pairs = pairs[["supplier_id", "location_id"]].drop_duplicates().sort_values(["supplier_id", "location_id"])
    rows = []
    for s, l in zip(pairs.supplier_id, pairs.location_id):
        gap = abs(REGIONS.index(sup_region[s]) - REGIONS.index(region[l]))
        transit = min(3, 1 + (gap + 1) // 2)
        lt = int(min(16, max(sup_lat[s]["base_lt"] + gap, transit + 1)))
        rows.append({"lead_time_id": f"LT-{s}-{l}", "supplier_id": s, "location_id": l,
                     "lead_time_weeks": lt, "transit_weeks": transit,
                     "effective_from": "2025-01-01", "effective_to": None})
    return pd.DataFrame(rows)


# ============================================================ demand & production
def _demand(skus, assort, sku_lat, loc_w, seed):
    sell = assort[assort.stocking_role == "SELL"].sort_values(["sku_id", "location_id"]).reset_index(drop=True)
    info = skus.set_index("sku_id")
    m_rows = len(sell)
    cat_amp, cat_phase = {}, {}
    for j, c in enumerate(CATEGORIES):
        r = rng(seed, "category", j)
        cat_amp[c] = float(r.uniform(0.0, 0.4))
        cat_phase[c] = float(r.uniform(0, 52))
    level = np.array([sku_lat[s]["level"] * loc_w[l] for s, l in zip(sell.sku_id, sell.location_id)])
    amp = sell.sku_id.map(info.category).map(cat_amp).to_numpy()
    phase = sell.sku_id.map(info.category).map(cat_phase).to_numpy()
    abc = sell.sku_id.map(info.abc_class).to_numpy()
    w = np.arange(1, H + 1)
    mean = level[:, None] * (1 + amp[:, None] * np.sin(2 * np.pi * (w[None, :] + phase[:, None]) / 52))
    mean = np.maximum(mean, 0.05)
    r = rng(seed, "demand")
    k = P["nb_dispersion"]
    nb = r.negative_binomial(k, k / (k + mean))
    p_occ = r.uniform(*P["c_occurrence"], size=m_rows)
    occ = r.random((m_rows, H)) < p_occ[:, None]
    inter = occ * r.poisson(mean / p_occ[:, None])
    base = np.where((abc == "C")[:, None], inter, nb).astype(np.int64)
    spike = r.random((m_rows, H)) < P["spike_rate"]
    mult = r.uniform(*P["spike_multiplier"], size=(m_rows, H))
    uplift = np.where(spike, np.round(mean * mult), 0).astype(np.int64)
    weeks = np.tile(cal.labels(w), m_rows)
    df = pd.DataFrame({
        "sku_id": np.repeat(sell.sku_id.to_numpy(), H), "location_id": np.repeat(sell.location_id.to_numpy(), H),
        "week": weeks, "baseline_qty": base.ravel(), "uplift_qty": uplift.ravel(),
    })
    df["forecast_qty"] = df.baseline_qty + df.uplift_qty
    df["uom"] = "EA"
    df["demand_id"] = ids.demand_ids(df.sku_id, df.location_id, df.week)
    return df


def _production(t, seed):
    idx = engine.build_index(t)
    F, _ = engine.demand_matrices(t, idx)
    make = set(t["sku"][t["sku"].make_or_buy == "MAKE"].sku_id)
    r = rng(seed, "production")
    recs = []
    for row, s, l in zip(idx.rows.row, idx.rows.sku_id, idx.rows.location_id):
        if s not in make:
            continue
        f = F[row].astype(float)
        padded = np.concatenate([f, np.repeat(f.mean(), 3)])
        roll = np.convolve(padded, np.ones(4) / 4, mode="valid")[:H]
        planned = np.round(roll * float(r.uniform(0.92, 1.05))).astype(np.int64)
        for wk in range(H):
            if planned[wk] > 0:
                recs.append((s, l, wk + 1, int(planned[wk])))
    pp = pd.DataFrame(recs, columns=["sku_id", "location_id", "w", "planned_qty"])
    pp = pp.sort_values(["w", "location_id", "sku_id"]).reset_index(drop=True)
    pp["production_plan_id"] = ids.seq("PP-2026-", len(pp), 6)
    pp["week"] = cal.labels(pp.w)
    pp["status"] = np.where(pp.w <= 4, "FIRM", "PLANNED")
    plants = t["location"][t["location"].location_type == "PLANT"].location_id.tolist()
    caps = []
    for j, l in enumerate(plants):
        rr = rng(seed, "production", 1000 + j)
        load = np.zeros(H, dtype=np.int64)
        sub = pp[pp.location_id == l]
        np.add.at(load, sub.w.to_numpy() - 1, sub.planned_qty.to_numpy())
        base = max(float(load.max()) * float(rr.uniform(0.97, 1.30)), 100.0)
        cap = np.maximum(load, np.round(base * (1 + rr.normal(0, 0.02, H)))).astype(np.int64)
        for wk in range(H):
            caps.append({"production_capacity_id": f"PCAP-{l}-{cal.label(wk + 1)}", "location_id": l,
                         "week": cal.label(wk + 1), "capacity_base_qty": int(cap[wk])})
    return pp.drop(columns="w"), pd.DataFrame(caps, columns=["production_capacity_id", "location_id", "week", "capacity_base_qty"])


def _inventory(t, seed):
    idx = engine.build_index(t)
    F, _ = engine.demand_matrices(t, idx)
    Pm = engine.production_matrix(t, idx)
    D = engine.dependent_matrix(t, idx, Pm)
    mean = (F + D).mean(axis=1)
    info = t["sku"].set_index("sku_id")
    r = rng(seed, "inventory")
    rows = []
    for row, s, l, role in zip(idx.rows.row, idx.rows.sku_id, idx.rows.location_id, idx.rows.stocking_role):
        if info.at[s, "make_or_buy"] == "MAKE":
            key = "MAKE"
        elif role == "COMPONENT":
            key = "COMPONENT"
        else:
            key = info.at[s, "abc_class"]
        lo, hi = P["cover_weeks"][key]
        on_hand = int(round(mean[row] * float(r.uniform(lo, hi))))
        alloc = int(round(on_hand * float(r.uniform(*P["allocated_share"]))))
        rows.append({"inventory_id": f"INV-{s}-{l}", "sku_id": s, "location_id": l,
                     "snapshot_week": cal.label(SNAPSHOT_WEEK), "on_hand_qty": on_hand,
                     "allocated_qty": alloc, "available_qty": on_hand - alloc, "uom": "EA"})
    return pd.DataFrame(rows), mean, idx


# ============================================================ purchase orders
def _apportion(total: int, weights: np.ndarray) -> np.ndarray:
    """Largest-remainder apportionment: integer counts summing exactly to total."""
    if total <= 0 or weights.sum() <= 0:
        return np.zeros(len(weights), dtype=np.int64)
    raw = weights / weights.sum() * total
    base = np.floor(raw).astype(np.int64)
    rem = total - base.sum()
    order = np.lexsort((np.arange(len(raw)), -(raw - base)))
    base[order[:rem]] += 1
    return base


def _purchase_orders(t, scale, seed, mean, idx, sup_lat):
    """Baseline inbound POs as a competent planner would have placed them
    BEFORE the latest forecast uplifts were known: sized against the baseline
    requirement (forecast without uplift + dependent demand) and timed to keep
    projected stock above safety stock. Row-level sizing accuracy varies, so
    some SKU-locations are deliberately under-ordered (a real planning gap).
    """
    sku = t["sku"].set_index("sku_id")
    ss = t["supplier_sku"]
    sups_of = {s: g.sort_values(["is_primary", "supplier_id"], ascending=[False, True]).to_dict("records")
               for s, g in ss.groupby("sku_id")}
    lt = {(a, b): (int(c), int(d)) for a, b, c, d in zip(t["lead_time"].supplier_id, t["lead_time"].location_id,
                                                         t["lead_time"].lead_time_weeks, t["lead_time"].transit_weeks)}
    F, U = engine.demand_matrices(t, idx)
    Pm = engine.production_matrix(t, idx)
    D = engine.dependent_matrix(t, idx, Pm)
    need = F - U + D
    O = engine.opening(t, idx)
    SS = engine.safety_stock(t, idx, F, D)
    buy_rows = idx.rows[idx.rows.sku_id.map(sku.make_or_buy) == "BUY"].reset_index(drop=True)
    rows = buy_rows.row.to_numpy()
    gap = np.maximum(0, need[rows].sum(axis=1) + SS[rows] - O[rows]).astype(float)
    # number of POs per row: 1 for each row with a gap (largest gaps first), rest by desired count
    has_gap = np.where(gap > 0)[0]
    counts = np.zeros(len(rows), dtype=np.int64)
    by_size = has_gap[np.argsort(-gap[has_gap] * np.array([sku.at[s, "unit_cost"] for s in buy_rows.sku_id[has_gap]]), kind="mergesort")]
    first = by_size[: scale.n_pos]
    counts[first] = 1
    left = scale.n_pos - len(first)
    desired = np.maximum(gap / np.maximum(mean[rows] * P["po_cover_weeks"][1], 1.0) - 1, 0)
    desired[counts == 0] = 0
    counts += _apportion(left, desired)
    r = rng(seed, "po")
    recs = []
    for i, (row, s, l) in enumerate(buy_rows[["row", "sku_id", "location_id"]].itertuples(index=False)):
        k = int(counts[i])
        if k == 0:
            continue
        opts = sups_of[s]
        accuracy = float(r.uniform(0.85, 1.15))          # planner sizing accuracy for this row
        total = gap[i] * accuracy
        bal = O[row] - np.cumsum(need[row])
        added, prev = 0, 0
        for j in range(k):
            o = opts[0] if (r.random() < P["primary_supplier_prob"] or len(opts) == 1) else opts[int(r.integers(1, len(opts)))]
            ltw, transit = lt[(o["supplier_id"], l)]
            mult = int(o["order_multiple_base_qty"])
            q = max(int(o["moq_base_qty"]), int(math.ceil(total / k / mult)) * mult)
            below = np.where(bal + added < SS[row])[0]
            below = below[below + 1 >= prev]
            pw = int(below[0]) + 1 if len(below) else min(H, prev + 4)
            pw = int(min(max(pw, 1, prev), H))
            prev = pw
            added += q
            recs.append({"supplier_id": o["supplier_id"], "sku_id": s, "location_id": l, "promised_w": pw,
                         "order_w": pw - ltw, "lt": ltw, "transit": transit, "requested_base_qty": q,
                         "order_uom": o["order_uom"], "pack": int(sku.at[s, "pack_size"]), "moq": int(o["moq_base_qty"]),
                         "unit_cost": float(o["unit_cost"])})
    po = pd.DataFrame(recs)
    po = po.sort_values(["order_w", "sku_id", "location_id", "supplier_id", "promised_w"], kind="mergesort").reset_index(drop=True)
    po["po_id"] = [ids.po(i) for i in range(1, len(po) + 1)]
    po["substitute_for_sku_id"] = None
    return po


def _finalise_order_qty(po: pd.DataFrame) -> None:
    case = po.order_uom == "CASE"
    po["order_qty"] = np.where(case, po.requested_base_qty // po.pack, po.requested_base_qty)


def _status(po, seed, sup_lat):
    r = rng(seed, "po_status")
    n = len(po)
    u = r.random(n)
    po["cancelled"] = u < P["cancel_rate"]
    po["unconfirmed"] = (~po.cancelled) & (po.order_w > SNAPSHOT_WEEK) & (r.random(n) < P["unconfirmed_rate"])
    back = r.integers(0, 4, size=n)
    po["created_w"] = np.where(po.order_w <= SNAPSHOT_WEEK, po.order_w, SNAPSHOT_WEEK - back)
    rel = po.supplier_id.map(lambda s: sup_lat[s]["rel"]).to_numpy()
    po["sdelay_draw"] = r.random(n) < np.minimum(0.5, (1 - rel) * 1.5)
    po["sdelay_weeks"] = r.integers(1, 5, size=n)
    po["cancel_w"] = np.minimum(SNAPSHOT_WEEK, po.created_w + r.integers(0, 3, size=n))


def _derive_flow(po):
    """Shipped / delayed flags from the (possibly edited) promise dates."""
    confirmed = ~po.cancelled & ~po.unconfirmed
    po["ship_w"] = po.promised_w - po.transit
    po["shipped"] = confirmed & (po.ship_w <= SNAPSHOT_WEEK)
    po["sdelayed"] = confirmed & ~po.shipped & po.sdelay_draw
    po["delayed_w"] = np.where(po.sdelayed, po.promised_w + po.sdelay_weeks, np.nan)


def _capacity(po, t, seed, sup_lat):
    confirmed = ~po.cancelled & ~po.unconfirmed
    sups = t["supplier"].supplier_id.tolist()
    load = {s: np.zeros(H, dtype=np.int64) for s in sups}
    for s, wk, q in zip(po.supplier_id[confirmed], po.promised_w[confirmed], po.requested_base_qty[confirmed]):
        if 1 <= wk <= H:
            load[s][wk - 1] += q
    caps, cap_arr = [], {}
    for j, s in enumerate(sups):
        r = rng(seed, "capacity", j + 1)
        lo = load[s]
        mx = float(lo.max())
        noise = 1 + r.normal(0, 0.03, H)
        if sup_lat[s]["tight"] and mx > 0:
            base = mx * float(r.uniform(0.55, 0.85))
            cap = np.round(base * noise).astype(np.int64)
        else:
            base = max(mx * float(r.uniform(1.05, 1.35)), lo.mean() * 3, 50.0)
            cap = np.maximum(lo, np.round(base * noise)).astype(np.int64)
        cap_arr[s] = cap
    po["confirmed_base_qty"] = np.where(confirmed, po.requested_base_qty, np.nan)
    for s in sups:
        over = np.where(load[s] > cap_arr[s])[0]
        for wi in over:
            m = confirmed & (po.supplier_id == s) & (po.promised_w == wi + 1)
            f = cap_arr[s][wi] / load[s][wi]
            mult = po.loc[m, "pack"]
            po.loc[m, "confirmed_base_qty"] = (np.floor(po.loc[m, "requested_base_qty"] * f / mult) * mult).astype(float)
    return cap_arr


def _shipments(po, seed):
    r = rng(seed, "shipment")
    carriers = list(CARRIERS)
    sh = po[po.shipped].copy()
    n = len(sh)
    c_idx = r.integers(0, len(carriers), size=n)
    rel = np.array([CARRIERS[carriers[i]] for i in c_idx])
    delayed = r.random(n) > rel
    delay = np.where(delayed, r.integers(1, 4, size=n), 0)
    out = pd.DataFrame({
        "po_id": sh.po_id.to_numpy(), "carrier": [carriers[i] for i in c_idx],
        "ship_w": sh.ship_w.to_numpy(), "eta_w": sh.promised_w.to_numpy() + delay, "delay_weeks": delay,
        "qty_base": sh.confirmed_base_qty.astype(np.int64).to_numpy(), "shipment_status": "IN_TRANSIT",
    })
    out["shipment_id"] = [f"SHP-2026-{i:06d}" for i in range(1, n + 1)]
    return out


def _events(po, ships):
    ev = []
    tdelay = ships.groupby("po_id").agg(eta_w=("eta_w", "max"), delay=("delay_weeks", "max"), ship_w=("ship_w", "min"))
    for p in po.itertuples(index=False):
        seq = 1
        ev.append((p.po_id, seq, "CREATED", p.created_w, "PLANNER", p.requested_base_qty, None, None))
        if p.cancelled:
            ev.append((p.po_id, seq + 1, "CANCELLED", max(p.created_w, p.cancel_w), "SUPPLIER", None, None, "SUPPLIER_DECLINED"))
            continue
        if p.unconfirmed:
            continue
        seq += 1
        ev.append((p.po_id, seq, "CONFIRMED", p.created_w, "SUPPLIER", int(p.confirmed_base_qty), None,
                   "CAPACITY_CUT" if p.confirmed_base_qty < p.requested_base_qty else None))
        if p.po_id in tdelay.index:
            row = tdelay.loc[p.po_id]
            seq += 1
            ev.append((p.po_id, seq, "SHIPPED", max(int(row.ship_w), p.created_w), "CARRIER", int(p.confirmed_base_qty), None, None))
            if row.delay > 0:
                seq += 1
                ev.append((p.po_id, seq, "DELAYED", SNAPSHOT_WEEK, "CARRIER", None, int(row.eta_w), "TRANSPORT_DELAY"))
        elif p.sdelayed:
            seq += 1
            ev.append((p.po_id, seq, "DELAYED", SNAPSHOT_WEEK, "SUPPLIER", None, int(p.delayed_w), "SUPPLIER_DELAY"))
    df = pd.DataFrame(ev, columns=["po_id", "event_seq", "event_type", "w", "actor", "qty_base", "new_w", "reason"])
    df["event_id"] = ids.seq("POE-2026-", len(df), 7)
    df["event_week"] = cal.labels(df.w)
    df["new_promised_week"] = [cal.label(int(x)) if pd.notna(x) else None for x in df.new_w]
    return df


def _po_table(po):
    status = np.where(po.cancelled, "CANCELLED", np.where(po.unconfirmed, "CREATED",
                      np.where(po.shipped.astype(bool), "SHIPPED", "CONFIRMED")))
    return pd.DataFrame({
        "po_id": po.po_id, "supplier_id": po.supplier_id, "sku_id": po.sku_id, "location_id": po.location_id,
        "substitute_for_sku_id": po.substitute_for_sku_id, "created_week": cal.labels(po.created_w),
        "order_week": cal.labels(po.order_w), "promised_week": cal.labels(po.promised_w),
        "order_qty": po.order_qty, "order_uom": po.order_uom, "requested_base_qty": po.requested_base_qty,
        "confirmed_base_qty": po.confirmed_base_qty, "unit_cost": po.unit_cost, "status": status,
    })


def _ship_table(ships):
    s = ships.copy()
    s["ship_week"] = cal.labels(s.ship_w)
    s["eta_week"] = cal.labels(s.eta_w)
    return s


def _assemble(t, po, ships):
    t["purchase_order"] = _po_table(po)
    t["inbound_shipment"] = _ship_table(ships)
    t["po_event"] = _events(po, ships)
    # DERIVED inbound inventory: quantity already shipped and in transit to each SKU-location
    loc = po.set_index("po_id")[["sku_id", "location_id"]]
    it = ships.join(loc, on="po_id").groupby(["sku_id", "location_id"]).qty_base.sum()
    inv = t["inventory"]
    inv["in_transit_qty"] = [int(it.get((s, l), 0)) for s, l in zip(inv.sku_id, inv.location_id)]


# ============================================================ boundary + injection
class GT:
    def __init__(self):
        self.rows = []

    def add(self, issue_type, expected, entity, record_id, rule, related=None, field=None,
            correct=None, corrupted=None, impact=None):
        self.rows.append({"issue_type": issue_type, "expected_flag": expected, "entity": entity,
                          "record_id": record_id, "related_record_ids": related, "field": field,
                          "correct_value": None if correct is None else str(correct),
                          "corrupted_value": None if corrupted is None else str(corrupted),
                          "impact_base_qty": impact, "rule": rule})

    def frame(self):
        df = pd.DataFrame(self.rows)
        df["issue_id"] = ids.seq("GT-", len(df), 6)
        return df


def _sup_load(po):
    m = ~po.cancelled & ~po.unconfirmed
    return po[m].groupby(["supplier_id", "promised_w"]).confirmed_base_qty.sum().to_dict()


def _boundaries(t, po, ships, cap_arr, scale, seed, gt, protected):
    r = rng(seed, "boundary")
    k = scale.boundary_per_type
    # PO exactly at MOQ (set during generation, labelled here)
    moq_ids = po.loc[po.attrs["moq_boundary"], "po_id"].tolist()
    for pid in moq_ids:
        protected["po"].add(pid)
        gt.add("BOUNDARY_PO_AT_MOQ", False, "purchase_order", pid, "requested_base_qty == supplier_sku.moq_base_qty (valid)")
    # receipt exactly at horizon end
    for pid in po.attrs["horizon_boundary"]:
        protected["po"].add(pid)
        gt.add("BOUNDARY_RECEIPT_AT_HORIZON_END", False, "purchase_order", pid,
               "promised_week == 2026W52; receipt must be counted in the last horizon week")
    # supplier capacity exactly 100% used
    load = _sup_load(po)
    tight = {s for s, v in t["supplier"].set_index("supplier_id").capacity_constrained.items() if v}
    cands = sorted((s, w) for (s, w), q in load.items() if q > 0 and 1 <= w <= H and s not in tight)
    pick = r.choice(len(cands), min(k, len(cands)), replace=False)
    for i in sorted(pick):
        s, w = cands[i]
        cap_arr[s][w - 1] = int(load[(s, w)])
        protected["sup_week"].add((s, w))
        gt.add("BOUNDARY_CAPACITY_AT_100PCT", False, "supplier_capacity", f"SCAP-{s}-{cal.label(w)}",
               "confirmed load == capacity_base_qty (valid, 0 spare)")
    # projected balance exactly zero at its minimum
    _assemble(t, po, ships)
    plan = engine.base_plan(t)
    C, idx = plan["C"], plan["idx"]
    mins = C.min(axis=1)
    inv = t["inventory"].set_index("inventory_id")
    cand_rows = [i for i in range(idx.n) if 0 < mins[i] and (C[i] > 0).all()]
    pick = r.choice(len(cand_rows), min(k, len(cand_rows)), replace=False) if cand_rows else []
    for i in sorted(pick):
        row = cand_rows[i]
        s, l = idx.rows.sku_id[row], idx.rows.location_id[row]
        iid = f"INV-{s}-{l}"
        inv.at[iid, "on_hand_qty"] = int(inv.at[iid, "on_hand_qty"]) - int(mins[row])
        inv.at[iid, "available_qty"] = int(inv.at[iid, "on_hand_qty"]) - int(inv.at[iid, "allocated_qty"])
        protected["row"].add((s, l))
        gt.add("BOUNDARY_ZERO_BALANCE", False, "inventory", iid,
               "on-hand set so the minimum projected closing balance is exactly 0: no shortage expected",
               related=f"{s}|{l}")
    t["inventory"] = inv.reset_index()


def _new_po(po, base, **kw):
    rec = base.copy()
    rec.update(kw)
    return rec


def _inject(t, po, ships, cap_arr, scale, seed, gt, protected):
    r = rng(seed, "inject")
    k = scale.edge_cases_per_type
    lt = {(a, b): (int(c), int(d)) for a, b, c, d in zip(t["lead_time"].supplier_id, t["lead_time"].location_id,
                                                         t["lead_time"].lead_time_weeks, t["lead_time"].transit_weeks)}
    assorted = set(zip(t["sku_location"].sku_id, t["sku_location"].location_id))
    used_po = set(protected["po"])
    used_sw = set(protected["sup_week"])

    def ok_row(s, l):
        return (s, l) not in protected["row"]

    # 1) INBOUND_DOUBLE_COUNT: duplicate ASN for an already shipped PO
    cands = ships[ships.po_id.map(lambda p: p not in used_po)].reset_index(drop=True)
    cands = cands[[ok_row(s, l) for s, l in zip(po.set_index("po_id").loc[cands.po_id, "sku_id"],
                                                  po.set_index("po_id").loc[cands.po_id, "location_id"])]]
    pick = cands.iloc[sorted(r.choice(len(cands), min(k, len(cands)), replace=False))]
    new = []
    nxt = len(ships) + 1
    for s in pick.itertuples(index=False):
        d = s._asdict()
        d["shipment_id"] = f"SHP-2026-{nxt:06d}"
        nxt += 1
        new.append(d)
        used_po.add(s.po_id)
        gt.add("INBOUND_DOUBLE_COUNT", True, "inbound_shipment", d["shipment_id"],
               "second ASN for a PO already in transit: receipt would be counted twice",
               related=f"{s.po_id}|{s.shipment_id}", field="shipment_id", correct="(none)",
               corrupted=d["shipment_id"], impact=int(s.qty_base))
    ships = pd.concat([ships, pd.DataFrame(new)], ignore_index=True)

    load = _sup_load(po)
    next_po = len(po) + 1
    new_pos = []

    def spare(s, w):
        return int(cap_arr[s][w - 1]) - int(load.get((s, w), 0))

    # 2) SUBSTITUTE_NOT_APPROVED: PO buys an unapproved substitute to cover another SKU
    subs = t["sku_substitute"]
    bad = subs[~subs.approved.astype(bool)]
    ss = t["supplier_sku"]
    pairs = []
    for y, x in zip(bad.sku_id, bad.substitute_sku_id):
        for l in sorted(t["sku_location"][t["sku_location"].sku_id == y].location_id):
            if (x, l) in assorted and ok_row(y, l) and ok_row(x, l):
                pairs.append((y, x, l))
    made = 0
    attempts = 0
    while pairs and made < k and attempts < 50 * k:
        attempts += 1
        y, x, l = pairs[int(r.integers(len(pairs)))]
        o = ss[ss.sku_id == x].sort_values("supplier_id").iloc[0]
        s = o.supplier_id
        ltw, transit = lt[(s, l)]
        w = int(r.integers(max(2 + ltw, 2), H + 1))
        q = int(o.moq_base_qty)
        if (s, w) in used_sw or spare(s, w) < q:
            continue
        pack = int(t["sku"].set_index("sku_id").at[x, "pack_size"])
        pid = ids.po(next_po)
        next_po += 1
        new_pos.append({"supplier_id": s, "sku_id": x, "location_id": l, "promised_w": w, "order_w": w - ltw,
                        "lt": ltw, "transit": transit, "requested_base_qty": q, "order_uom": o.order_uom,
                        "pack": pack, "moq": q, "unit_cost": float(o.unit_cost), "po_id": pid,
                        "substitute_for_sku_id": y, "cancelled": False, "unconfirmed": False,
                        "created_w": SNAPSHOT_WEEK, "sdelay_draw": False, "sdelay_weeks": 1,
                        "cancel_w": SNAPSHOT_WEEK, "confirmed_base_qty": float(q)})
        load[(s, w)] = load.get((s, w), 0) + q
        used_sw.add((s, w))
        made += 1
        gt.add("SUBSTITUTE_NOT_APPROVED", True, "purchase_order", pid,
               "substitute_for_sku_id set but sku_substitute pair is not APPROVED",
               related=f"SUB-{y}-{x}", field="substitute_for_sku_id", correct="(null)", corrupted=y, impact=q)

    # 3) SUPPLIER_CAPACITY_EXCEEDED: extra confirmed PO beyond weekly capacity
    sw = sorted({(s, l) for s, l in lt})
    made = 0
    attempts = 0
    while made < k and attempts < 50 * k:
        attempts += 1
        s, l = sw[int(r.integers(len(sw)))]
        ltw, transit = lt[(s, l)]
        opts = ss[(ss.supplier_id == s)]
        opts = opts[[(x, l) in assorted and ok_row(x, l) for x in opts.sku_id]]
        if not len(opts):
            continue
        w = int(r.integers(max(2 + ltw, 2), H + 1))
        if (s, w) in used_sw or w > H:
            continue
        o = opts.iloc[int(r.integers(len(opts)))]
        mult = int(o.order_multiple_base_qty)
        c = int(cap_arr[s][w - 1])
        extra = max(mult, int(math.ceil(c * float(r.uniform(0.2, 0.6)) / mult)) * mult)
        q = max(int(o.moq_base_qty), int(math.ceil((max(spare(s, w), 0) + extra) / mult)) * mult)
        pid = ids.po(next_po)
        next_po += 1
        new_pos.append({"supplier_id": s, "sku_id": o.sku_id, "location_id": l, "promised_w": w, "order_w": w - ltw,
                        "lt": ltw, "transit": transit, "requested_base_qty": q, "order_uom": o.order_uom,
                        "pack": mult, "moq": int(o.moq_base_qty), "unit_cost": float(o.unit_cost), "po_id": pid,
                        "substitute_for_sku_id": None, "cancelled": False, "unconfirmed": False,
                        "created_w": SNAPSHOT_WEEK, "sdelay_draw": False, "sdelay_weeks": 1,
                        "cancel_w": SNAPSHOT_WEEK, "confirmed_base_qty": float(q)})
        before = int(load.get((s, w), 0))
        load[(s, w)] = before + q
        used_sw.add((s, w))
        made += 1
        gt.add("SUPPLIER_CAPACITY_EXCEEDED", True, "purchase_order", pid,
               "confirmed load for supplier-week exceeds supplier_capacity.capacity_base_qty",
               related=f"SCAP-{s}-{cal.label(w)}", field="confirmed_base_qty",
               correct=max(c - before, 0), corrupted=q, impact=q - max(c - before, 0))

    if new_pos:
        add = pd.DataFrame(new_pos)
        add["ship_w"] = add.promised_w - add.transit
        add["shipped"] = False
        add["sdelayed"] = False
        add["delayed_w"] = np.nan
        po = pd.concat([po, add], ignore_index=True)

    def eligible(mask):
        m = mask & ~po.po_id.isin(used_po) & po.substitute_for_sku_id.isna()
        m &= np.array([ok_row(s, l) for s, l in zip(po.sku_id, po.location_id)])
        m &= np.array([(s, w) not in used_sw for s, w in zip(po.supplier_id, po.promised_w)])
        return po.index[m].tolist()

    # 4) SHORTAGE_WITHOUT_LEAD_TIME: promised week equals order week (lead time ignored)
    base_mask = ~po.cancelled & ~po.unconfirmed & ~po.shipped & ~po.sdelayed & (po.order_w >= 2) \
        & (po.confirmed_base_qty == po.requested_base_qty)
    cands = eligible(base_mask)
    order = r.permutation(len(cands))
    made = 0
    for j in order:
        if made >= k:
            break
        i = cands[j]
        s, ow, pw, q = po.at[i, "supplier_id"], int(po.at[i, "order_w"]), int(po.at[i, "promised_w"]), int(po.at[i, "confirmed_base_qty"])
        if (s, ow) in used_sw or spare(s, ow) < q:
            continue
        load[(s, pw)] -= q
        load[(s, ow)] = load.get((s, ow), 0) + q
        used_sw.update({(s, ow), (s, pw)})
        used_po.add(po.at[i, "po_id"])
        po.at[i, "promised_w"] = ow
        made += 1
        gt.add("SHORTAGE_WITHOUT_LEAD_TIME", True, "purchase_order", po.at[i, "po_id"],
               "promised_week < order_week + lead_time_weeks: supply credited before it can arrive",
               related=f"LT-{s}-{po.at[i, 'location_id']}", field="promised_week",
               correct=cal.label(pw), corrupted=cal.label(ow), impact=q)

    # 5) UOM_MISMATCH: case quantity keyed with EA unit of measure
    base_mask = ~po.cancelled & ~po.unconfirmed & ~po.shipped & (po.order_uom == "CASE") \
        & (po.confirmed_base_qty == po.requested_base_qty)
    cands = eligible(base_mask)
    pick = sorted(r.choice(len(cands), min(k, len(cands)), replace=False)) if cands else []
    for j in pick:
        i = cands[j]
        right = int(po.at[i, "requested_base_qty"])
        wrong = int(po.at[i, "order_qty"])
        s, w = po.at[i, "supplier_id"], int(po.at[i, "promised_w"])
        load[(s, w)] -= right - wrong
        po.at[i, "order_uom"] = "EA"
        po.at[i, "requested_base_qty"] = wrong
        po.at[i, "confirmed_base_qty"] = float(wrong)
        used_po.add(po.at[i, "po_id"])
        gt.add("UOM_MISMATCH", True, "purchase_order", po.at[i, "po_id"],
               "order_qty was entered in CASE but tagged EA: base quantity understated by pack_size",
               related=f"UOM-{po.at[i, 'sku_id']}-CASE", field="order_uom", correct="CASE", corrupted="EA",
               impact=right - wrong)
    # shipped/delayed flags are frozen: injections never create or remove physical events
    return po, ships


# ============================================================ orchestration
def generate(scale: Scale, seed: int):
    t: dict[str, pd.DataFrame] = {}
    t["sku"], sku_lat = _skus(scale, seed)
    t["location"], loc_w = _locations(scale, seed)
    t["supplier"], sup_lat = _suppliers(scale, seed)
    assort = _assortment(t["sku"], t["location"], loc_w, seed)
    t["bom"], t["sku_location"] = _bom(t["sku"], assort, seed)
    t["supplier_sku"] = _supplier_sku(t["sku"], sku_lat, scale.n_suppliers, seed)
    t["sku_substitute"] = _substitutes(t["sku"], t["sku_location"], seed)
    t["lead_time"] = _lead_times(t["supplier_sku"], t["sku_location"], t["location"], t["supplier"], sup_lat)
    uom = t["sku"][["sku_id", "pack_size"]]
    t["uom_conversion"] = pd.concat([
        pd.DataFrame({"uom_conversion_id": "UOM-" + uom.sku_id + "-CASE", "sku_id": uom.sku_id,
                      "from_uom": "CASE", "to_uom": "EA", "factor": uom.pack_size}),
        pd.DataFrame({"uom_conversion_id": "UOM-" + uom.sku_id + "-EA", "sku_id": uom.sku_id,
                      "from_uom": "EA", "to_uom": "EA", "factor": 1}),
    ], ignore_index=True)

    t["forecast_demand"] = _demand(t["sku"], t["sku_location"], sku_lat, loc_w, seed)
    t["production_plan"] = pd.DataFrame(columns=["production_plan_id", "sku_id", "location_id", "week", "planned_qty", "status"])
    t["production_plan"], t["production_capacity"] = _production(t, seed)
    t["inventory"], mean, idx = _inventory(t, seed)

    po = _purchase_orders(t, scale, seed, mean, idx, sup_lat)
    _status(po, seed, sup_lat)
    _derive_flow(po)
    rb = rng(seed, "boundary", 99)
    # boundary: some POs exactly at MOQ
    elig = po.index[~po.cancelled & ~po.unconfirmed].tolist()
    moq_pick = sorted(rb.choice(elig, min(scale.boundary_per_type, len(elig)), replace=False).tolist())
    po.loc[moq_pick, "requested_base_qty"] = po.loc[moq_pick, "moq"]
    # boundary: some receipts exactly at the horizon end
    elig = po.index[~po.cancelled & ~po.unconfirmed & ~po.shipped & ~po.sdelayed].difference(moq_pick).tolist()
    hz_pick = sorted(rb.choice(elig, min(scale.boundary_per_type, len(elig)), replace=False).tolist())
    po.loc[hz_pick, "promised_w"] = H
    po.loc[hz_pick, "order_w"] = H - po.loc[hz_pick, "lt"]
    po.loc[hz_pick, "created_w"] = np.minimum(po.loc[hz_pick, "created_w"], SNAPSHOT_WEEK)
    _derive_flow(po)
    # baseline approved-substitute POs
    subs = t["sku_substitute"]
    good = subs[subs.approved.astype(bool)]
    by_x = {}
    for y, x in zip(good.sku_id, good.substitute_sku_id):
        by_x.setdefault(x, []).append(y)
    assorted = set(zip(t["sku_location"].sku_id, t["sku_location"].location_id))
    cand = [i for i, (x, l) in enumerate(zip(po.sku_id, po.location_id))
            if i not in moq_pick and i not in hz_pick and any((y, l) in assorted for y in by_x.get(x, []))]
    n_sub = min(len(cand), int(round(P["substitute_po_rate"] * len(po))))
    for i in sorted(rb.choice(cand, n_sub, replace=False).tolist()) if n_sub else []:
        ys = [y for y in by_x[po.at[i, "sku_id"]] if (y, po.at[i, "location_id"]) in assorted]
        po.at[i, "substitute_for_sku_id"] = ys[0]

    cap_arr = _capacity(po, t, seed, sup_lat)
    _derive_flow(po)
    ships = _shipments(po, seed)
    po.attrs["moq_boundary"] = moq_pick
    po.attrs["horizon_boundary"] = po.loc[hz_pick, "po_id"].tolist()
    _finalise_order_qty(po)

    # supplier capacity_constrained is DERIVED from cuts
    cut = po[(po.confirmed_base_qty.notna()) & (po.confirmed_base_qty < po.requested_base_qty)].supplier_id.unique()
    t["supplier"]["capacity_constrained"] = t["supplier"].supplier_id.isin(cut)

    gt = GT()
    protected = {"po": set(), "sup_week": set(), "row": set()}
    _boundaries(t, po, ships, cap_arr, scale, seed, gt, protected)
    po, ships = _inject(t, po, ships, cap_arr, scale, seed, gt, protected)
    _finalise_order_qty_keep_uom(po)
    _assemble(t, po, ships)

    caps = []
    for s, cap in cap_arr.items():
        for wk in range(H):
            caps.append((f"SCAP-{s}-{cal.label(wk + 1)}", s, cal.label(wk + 1), int(max(cap[wk], 0))))
    t["supplier_capacity"] = pd.DataFrame(caps, columns=["supplier_capacity_id", "supplier_id", "week", "capacity_base_qty"])
    t["sku_location"] = t["sku_location"][["sku_location_id", "sku_id", "location_id", "stocking_role", "effective_from"]]
    return t, gt.frame()


def _finalise_order_qty_keep_uom(po: pd.DataFrame) -> None:
    """order_qty for rows created after the first pass; injected UoM rows keep their keyed qty."""
    missing = po.order_qty.isna() if "order_qty" in po else pd.Series(True, index=po.index)
    case = po.order_uom == "CASE"
    calc = np.where(case, po.requested_base_qty // po.pack, po.requested_base_qty)
    po["order_qty"] = np.where(missing, calc, po.order_qty)
