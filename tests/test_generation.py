"""Generator: IDs, volumes, determinism, dependency order, derived values."""
import re

import pandas as pd

from oryva import calendar as cal
from oryva import generate as g
from oryva import ids
from oryva.config import DEFAULT_SEED, SCALES


def test_id_formats_are_zero_padded():
    assert ids.sku(1) == "SKU-000001"
    assert ids.po(1) == "PO-2026-000001"
    assert ids.shortage(42) == "SHORT-2026-000042"
    assert ids.mitigation("SHORT-2026-000001", 1) == "MIT-SHORT-2026-000001-01"
    assert cal.label(1) == "2026W01" and cal.label(52) == "2026W52" and cal.label(0) == "2025W52"


def test_demand_id_pattern(run):
    d = run["t"]["forecast_demand"]
    rx = re.compile(r"^DEM-SKU-\d{6}-LOC-\d{3}-2026W\d{2}$")
    assert d.demand_id.map(lambda v: bool(rx.match(v))).all()
    # one row per SKU-location-week for all 52 weeks
    assert (d.groupby(["sku_id", "location_id"]).size() == 52).all()


def test_same_seed_gives_identical_tables():
    a, gta = g.generate(SCALES["starter"], DEFAULT_SEED)
    b, gtb = g.generate(SCALES["starter"], DEFAULT_SEED)
    for name in a:
        pd.testing.assert_frame_equal(a[name].reset_index(drop=True), b[name].reset_index(drop=True))
    pd.testing.assert_frame_equal(gta, gtb)


def test_different_seed_changes_data():
    a, _ = g.generate(SCALES["starter"], DEFAULT_SEED)
    b, _ = g.generate(SCALES["starter"], DEFAULT_SEED + 1)
    assert not a["forecast_demand"].forecast_qty.equals(b["forecast_demand"].forecast_qty)


def test_starter_masters_are_a_subset_of_full():
    """Per-entity RNG streams: SKU-000042 is identical at every scale."""
    s_small, _ = g._skus(SCALES["starter"], DEFAULT_SEED)
    s_full, _ = g._skus(SCALES["full"], DEFAULT_SEED)
    pd.testing.assert_frame_equal(s_small, s_full.iloc[: len(s_small)].reset_index(drop=True))
    l_small, _ = g._locations(SCALES["starter"], DEFAULT_SEED)
    l_full, _ = g._locations(SCALES["full"], DEFAULT_SEED)
    pd.testing.assert_frame_equal(l_small, l_full.iloc[: len(l_small)].reset_index(drop=True))
    p_small, _ = g._suppliers(SCALES["starter"], DEFAULT_SEED)
    p_full, _ = g._suppliers(SCALES["full"], DEFAULT_SEED)
    pd.testing.assert_frame_equal(p_small.drop(columns="capacity_constrained"),
                                  p_full.iloc[: len(p_small)].drop(columns="capacity_constrained").reset_index(drop=True))


def test_starter_volumes(run):
    t = run["t"]
    sc = SCALES["starter"]
    assert len(t["sku"]) == sc.n_skus
    assert len(t["location"]) == sc.n_locations
    assert len(t["supplier"]) == sc.n_suppliers
    injected_pos = (run["gt"].entity == "purchase_order") & run["gt"].issue_type.isin(
        ["SUBSTITUTE_NOT_APPROVED", "SUPPLIER_CAPACITY_EXCEEDED"])
    assert len(t["purchase_order"]) == sc.n_pos + int(injected_pos.sum())


def test_derived_values_come_from_source_fields(run):
    t = run["t"]
    d = t["forecast_demand"]
    assert (d.forecast_qty == d.baseline_qty + d.uplift_qty).all()
    inv = t["inventory"]
    assert (inv.available_qty == inv.on_hand_qty - inv.allocated_qty).all()
    po = t["purchase_order"]
    pack = t["sku"].set_index("sku_id").pack_size
    factor = po.order_uom.map({"EA": 1}).fillna(po.sku_id.map(pack)).astype(int)
    assert (po.requested_base_qty == po.order_qty * factor).all()


def test_realistic_variation(run):
    """Demand is not uniform: A > B > C volume, C items are intermittent, spikes exist."""
    d = run["t"]["forecast_demand"]
    abc = run["t"]["sku"].set_index("sku_id").abc_class
    mean = d.groupby(d.sku_id.map(abc)).forecast_qty.mean()
    assert mean["A"] > mean["B"] > mean["C"]
    zero_c = (d[d.sku_id.map(abc) == "C"].baseline_qty == 0).mean()
    assert 0.15 < zero_c < 0.8
    assert 0.01 < (d.uplift_qty > 0).mean() < 0.08
    assert run["t"]["inbound_shipment"].delay_weeks.gt(0).any()
    assert run["t"]["supplier"].capacity_constrained.any()
