"""Planning engine: hand-calculated balance, shortages, causes, mitigation policy."""
import math

import numpy as np
import pandas as pd

from oryva import calendar as cal
from oryva import engine
from oryva.plan import _deficit, _runs


def _tiny():
    """One SKU-location: on hand 100, forecast 30/week (+20 uplift in week 3),
    one confirmed PO of 60 promised for week 4."""
    w = [cal.label(i) for i in range(1, 53)]
    t = {
        "sku": pd.DataFrame({"sku_id": ["SKU-000001"], "safety_stock_weeks": [1.0], "make_or_buy": ["BUY"]}),
        "sku_location": pd.DataFrame({"sku_id": ["SKU-000001"], "location_id": ["LOC-002"], "stocking_role": ["SELL"]}),
        "forecast_demand": pd.DataFrame({"sku_id": "SKU-000001", "location_id": "LOC-002", "week": w,
                                         "baseline_qty": 30, "uplift_qty": [20 if i == 3 else 0 for i in range(1, 53)]}),
        "production_plan": pd.DataFrame(columns=["sku_id", "location_id", "week", "planned_qty"]),
        "bom": pd.DataFrame(columns=["parent_sku_id", "component_sku_id", "qty_per"]),
        "inventory": pd.DataFrame({"sku_id": ["SKU-000001"], "location_id": ["LOC-002"], "on_hand_qty": [110], "allocated_qty": [10]}),
        "purchase_order": pd.DataFrame({"po_id": ["PO-2026-000001"], "supplier_id": ["SUP-0001"], "sku_id": ["SKU-000001"],
                                        "location_id": ["LOC-002"], "substitute_for_sku_id": [None], "order_week": ["2026W01"],
                                        "promised_week": ["2026W04"], "requested_base_qty": [60], "confirmed_base_qty": [60.0],
                                        "status": ["CONFIRMED"]}),
        "po_event": pd.DataFrame(columns=["po_id", "event_seq", "event_type", "new_promised_week"]),
        "inbound_shipment": pd.DataFrame(columns=["shipment_id", "po_id", "eta_week", "delay_weeks", "qty_base"]),
        "sku_substitute": pd.DataFrame(columns=["sku_id", "substitute_sku_id", "conversion_ratio"]),
    }
    t["forecast_demand"]["forecast_qty"] = t["forecast_demand"].baseline_qty + t["forecast_demand"].uplift_qty
    return t


def test_hand_calculated_projected_balance():
    b = engine.base_plan(_tiny())
    c = b["C"][0]
    # opening 100 -> 70, 40, -10 (30+20 uplift), +60-30 -> 20, -10, -40 ...
    assert list(c[:6]) == [70, 40, -10, 20, -10, -40]
    assert c[-1] == 100 + 60 - 30 * 52 - 20
    assert b["SS"][0] == math.ceil(1.0 * (30 * 52 + 20) / 52)


def test_shortage_runs_and_deficit():
    c = engine.base_plan(_tiny())["C"]
    runs = _runs(c[0] < 0)
    assert runs[0] == (2, 2) and runs[1] == (4, 51)
    assert _deficit(c, 0, 2, 2) == 10


def test_delay_moves_receipt():
    t = _tiny()
    t["po_event"] = pd.DataFrame({"po_id": ["PO-2026-000001"], "event_seq": [3], "event_type": ["DELAYED"],
                                  "new_promised_week": ["2026W06"]})
    c = engine.base_plan(t)["C"][0]
    assert list(c[:6]) == [70, 40, -10, -40, -70, -40]


def test_pab_reconciles_week_by_week(run):
    pab = run["o"]["projected_balance"]
    assert (pab.closing_qty == pab.opening_qty + pab.receipt_qty + pab.production_qty
            - pab.forecast_qty - pab.dependent_demand_qty).all()


def test_every_shortage_has_causes_that_sum(run):
    sh, cs = run["o"]["shortage"], run["o"]["shortage_cause"]
    assert len(sh) > 0
    tot = cs.groupby("shortage_id").contributed_qty.sum()
    assert (sh.set_index("shortage_id").shortage_qty == tot.reindex(sh.shortage_id).values).all()
    assert (cs.contributed_qty > 0).all()
    assert cs.cause_type.nunique() >= 5


def test_mitigations_respect_policy_and_capacity(run):
    t, o = run["t"], run["o"]
    mo, sh = o["mitigation_option"], o["shortage"]
    sel = mo[mo.selected]
    assert sel.feasible.all()
    subs = t["sku_substitute"]
    ok = {(a, b) for a, b, x in zip(subs.sku_id, subs.substitute_sku_id, subs.approved) if x}
    sku_of = sh.set_index("shortage_id").sku_id
    for s, x in zip(sel[sel.option_type == "SUBSTITUTE"].shortage_id, sel[sel.option_type == "SUBSTITUTE"].source_id):
        assert (sku_of[s], x) in ok
    # unapproved substitutes are listed but rejected with a reason
    rej = mo[mo.rejection_reason.fillna("").str.startswith("SUBSTITUTE_NOT_APPROVED")]
    assert len(rej) > 0 and not rej.selected.any()
    on_hold = set(t["supplier"].supplier_id[t["supplier"].status == "ON_HOLD"])
    assert not sel[sel.option_type.isin(["PLACE_PO", "EXPEDITE"])].source_id.isin(on_hold).any()


def test_alternatives_show_cost_and_service_tradeoffs(run):
    mo = run["o"]["mitigation_option"]
    feas = mo[mo.feasible]
    per = feas.groupby("shortage_id").size()
    assert (per >= 2).mean() > 0.5               # most shortages have >1 feasible alternative
    assert feas.cost.notna().all() and feas.fill_pct.between(0, 100).all()
    assert feas.dominated.any()
    assert set(mo.option_type) >= {"TRANSFER", "PLACE_PO", "EXPEDITE", "ACCEPT_SHORTFALL"}


def test_priority_rank_is_a_permutation(run):
    sh = run["o"]["shortage"]
    assert sorted(sh.priority_rank) == list(range(1, len(sh) + 1))
    top = sh.sort_values("priority_rank")
    assert top.priority_score.is_monotonic_decreasing
