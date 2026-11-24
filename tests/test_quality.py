"""Edge cases, ground-truth separation, detector quality and validation."""
import builtins
import inspect
from pathlib import Path

import pandas as pd

from oryva import detect, engine, io, pipeline, plan
from oryva.schema import INPUT_TABLES, ISSUE_TYPES
from oryva.config import SCALES


def test_all_five_edge_cases_injected_and_traceable(run):
    gt, t = run["gt"], run["t"]
    k = SCALES["starter"].edge_cases_per_type
    counts = gt[gt.expected_flag].issue_type.value_counts()
    for it in ISSUE_TYPES:
        assert counts.get(it, 0) == k, it
    ids = {"purchase_order": set(t["purchase_order"].po_id), "inbound_shipment": set(t["inbound_shipment"].shipment_id),
           "inventory": set(t["inventory"].inventory_id), "supplier_capacity": set(t["supplier_capacity"].supplier_capacity_id)}
    for e, r in zip(gt.entity, gt.record_id):
        assert r in ids[e]


def test_ground_truth_is_not_in_input_files(run):
    p = run["paths"]
    assert not any("ground_truth" in f.name for f in p.data.iterdir())
    for name in INPUT_TABLES:
        cols = set(run["t"][name].columns)
        assert not cols & {"issue_type", "expected_flag", "ground_truth", "is_anomaly"}, name


def test_detector_and_planner_never_read_ground_truth(run, monkeypatch):
    for mod in (detect, plan, engine):
        assert "ground_truth" not in inspect.getsource(mod)
    opened = []
    real_open = builtins.open
    real_read = pd.read_csv

    def spy_open(f, *a, **k):
        opened.append(str(f))
        return real_open(f, *a, **k)

    def spy_read(f, *a, **k):
        opened.append(str(f))
        return real_read(f, *a, **k)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(pd, "read_csv", spy_read)
    p = run["paths"]
    t = pipeline.load_inputs(p)
    exc = detect.detect(t)
    plan.run(t, exc)
    assert opened and not any("ground_truth" in f for f in opened)


def test_detector_scores(run):
    d = run["evaluation"]["detector"]
    for it in ISSUE_TYPES:
        assert d[it]["recall"] >= 0.8, it
        assert d[it]["precision"] >= 0.8, it
    assert d["_boundary"]["false_positives"] == 0


def test_anomalies_change_the_plan(run):
    imp = run["evaluation"]["anomaly_impact"]["by_issue_type"]
    by = {r["issue_type"]: r for r in imp}
    assert by["INBOUND_DOUBLE_COUNT"]["direction"] == "overstated"
    assert by["UOM_MISMATCH"]["direction"] == "understated"
    assert sum(r["hidden_shortage_weeks"] + r["false_shortage_weeks"] for r in imp) > 0


def test_validation_passes_with_only_labelled_violations(run):
    v = run["validation"]
    assert v["overall_status"] == "PASS"
    assert v["integrity_failed"] == 0
    assert v["business_rule_violations_unexplained"] == 0
    assert v["labelled_anomalies_caught_by_rules"] == v["labelled_anomalies"]


def test_boundary_cases_behave(run):
    gt, o = run["gt"], run["o"]
    zero = gt[gt.issue_type == "BOUNDARY_ZERO_BALANCE"]
    sh = set(zip(o["shortage"].sku_id, o["shortage"].location_id))
    pab = o["projected_balance"]
    for rel in zero.related_record_ids:
        s, l = rel.split("|")
        assert (s, l) not in sh
        assert pab[(pab.sku_id == s) & (pab.location_id == l)].closing_qty.min() == 0


def test_lifecycle_history_is_append_only(run):
    ev = run["t"]["po_event"].sort_values(["po_id", "event_seq"])
    assert (ev.groupby("po_id").event_seq.apply(lambda s: list(s) == list(range(1, len(s) + 1)))).all()
    assert (ev.groupby("po_id").event_type.first() == "CREATED").all()


def test_outputs_written(run):
    out = run["paths"].out
    for f in ("validation_summary.json", "validation_summary.md", "evaluation.json", "evaluation_report.md",
              "report.html", "exception.csv", "shortage.csv", "mitigation_option.csv"):
        assert (out / f).exists(), f


def test_reproduce_starter(tmp_path):
    a = pipeline.Paths(tmp_path / "a", "starter")
    b = pipeline.Paths(tmp_path / "b", "starter")
    pipeline.stage_generate(SCALES["starter"], 20261022, a.root)
    pipeline.stage_generate(SCALES["starter"], 20261022, b.root)
    ma, mb = io.manifest(a.data), io.manifest(b.data)
    assert ma == mb
    assert io.sha256(a.gt / "ground_truth.csv") == io.sha256(b.gt / "ground_truth.csv")


def test_all_five_actors_are_modelled(run):
    o, t = run["o"], run["t"]
    used = set(o["mitigation_event"].actor) | set(o["shortage_event"].actor) | set(t["po_event"].actor) | set(o["exception"].owner)
    assert {"SUPPLIER", "PLANNER", "CARRIER", "LOGISTICS_ANALYST", "OPERATIONS_MANAGER"} <= used
    mev = o["mitigation_event"].merge(o["mitigation_option"][["mitigation_id", "option_type"]], on="mitigation_id")
    acc = mev[(mev.event_type == "SELECTED") & (mev.option_type == "ACCEPT_SHORTFALL")]
    assert len(acc) and (acc.actor == "OPERATIONS_MANAGER").all()


def test_inbound_inventory_is_derived_from_shipments(run):
    t = run["t"]
    inv = t["inventory"]
    shp = t["inbound_shipment"].merge(t["purchase_order"][["po_id", "sku_id", "location_id"]], on="po_id")
    assert inv.in_transit_qty.sum() == shp.qty_base.sum() > 0
