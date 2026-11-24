"""Data dictionary as code.

This module is the single source of truth for every table: it drives the
validator (types, required, enums, patterns, uniqueness, foreign keys), the
generated docs/data_dictionary.md and schema/schema.sql.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import CARRIERS, CATEGORIES, REGIONS
from .ids import PATTERNS


@dataclass(frozen=True)
class Col:
    name: str
    type: str                  # str | int | float | bool | week | date
    required: bool = True
    allowed: tuple | None = None
    unit: str = ""
    unique: bool = False
    pattern: str | None = None
    fk: str | None = None      # "table.column"
    rule: str = ""


@dataclass(frozen=True)
class Table:
    name: str
    kind: str                  # master | bridge | reference | transaction | event | derived | label
    pk: str
    desc: str
    cols: list = field(default_factory=list)
    natural_key: tuple = ()
    lifecycle: str = ""
    cardinality: str = ""


W = PATTERNS["week"]
SKU = PATTERNS["sku"]
LOC = PATTERNS["location"]
SUP = PATTERNS["supplier"]
PO = PATTERNS["po"]
SHORT = PATTERNS["shortage"]
MIT = PATTERNS["mitigation"]

PO_STATUS = ("CREATED", "CONFIRMED", "SHIPPED", "CANCELLED")
PO_EVENT = ("CREATED", "CONFIRMED", "SHIPPED", "DELAYED", "CANCELLED")
# the five actors named in the brief
ACTORS = ("SUPPLIER", "PLANNER", "CARRIER", "LOGISTICS_ANALYST", "OPERATIONS_MANAGER")
CAUSES = ("DEMAND_SPIKE", "DEPENDENT_DEMAND", "SUPPLIER_CAPACITY_CUT", "CANCELLED_PO",
          "SUPPLIER_DELAY", "TRANSPORT_DELAY", "BASE_SUPPLY_GAP")
OPTIONS = ("TRANSFER", "SUBSTITUTE", "PRODUCE", "PLACE_PO", "EXPEDITE", "ACCEPT_SHORTFALL")
SHORT_STATUS = ("MITIGATED", "PARTIALLY_MITIGATED", "UNMITIGATED", "COVERED_BY_PRIOR_MITIGATION")
ISSUE_TYPES = ("INBOUND_DOUBLE_COUNT", "SUBSTITUTE_NOT_APPROVED", "SUPPLIER_CAPACITY_EXCEEDED",
               "SHORTAGE_WITHOUT_LEAD_TIME", "UOM_MISMATCH")
BOUNDARY_TYPES = ("BOUNDARY_PO_AT_MOQ", "BOUNDARY_CAPACITY_AT_100PCT",
                  "BOUNDARY_ZERO_BALANCE", "BOUNDARY_RECEIPT_AT_HORIZON_END")

TABLES: dict[str, Table] = {}


def _t(t: Table) -> None:
    TABLES[t.name] = t


# ----------------------------------------------------------------- masters
_t(Table("sku", "master", "sku_id", "Stock keeping unit master.", [
    Col("sku_id", "str", unique=True, pattern=SKU, rule="SKU-000001 counter, immutable"),
    Col("sku_name", "str"),
    Col("category", "str", allowed=tuple(CATEGORIES)),
    Col("abc_class", "str", allowed=("A", "B", "C"), rule="A=top 20% by volume driver, B=30%, C=50%"),
    Col("make_or_buy", "str", allowed=("MAKE", "BUY")),
    Col("base_uom", "str", allowed=("EA",)),
    Col("pack_size", "int", allowed=(6, 12, 24, 48), unit="EA per CASE"),
    Col("unit_cost", "float", unit="currency/EA", rule="> 0"),
    Col("unit_price", "float", unit="currency/EA", rule="> unit_cost"),
    Col("safety_stock_weeks", "float", unit="weeks", rule="A=2.0, B=1.5, C=1.0"),
    Col("lifecycle_status", "str", allowed=("ACTIVE", "NEW", "PHASE_OUT")),
    Col("effective_from", "date"),
    Col("effective_to", "date", required=False, rule=">= effective_from when present"),
], lifecycle="NEW -> ACTIVE -> PHASE_OUT"))

_t(Table("location", "master", "location_id", "Plants, distribution centres and warehouses.", [
    Col("location_id", "str", unique=True, pattern=LOC),
    Col("location_name", "str"),
    Col("location_type", "str", allowed=("PLANT", "DC", "WAREHOUSE"), rule="every 10th location (LOC-001, LOC-011..) is a PLANT"),
    Col("region", "str", allowed=tuple(REGIONS)),
    Col("storage_capacity_units", "int", unit="EA", rule="> 0"),
]))

_t(Table("supplier", "master", "supplier_id", "Supplier master.", [
    Col("supplier_id", "str", unique=True, pattern=SUP),
    Col("supplier_name", "str"),
    Col("region", "str", allowed=tuple(REGIONS)),
    Col("reliability_score", "float", unit="0-1", rule="0 < x <= 1; drives supplier delay probability"),
    Col("status", "str", allowed=("ACTIVE", "ON_HOLD"), rule="ON_HOLD suppliers may not receive new POs"),
    Col("capacity_constrained", "bool", rule="DERIVED: true if any confirmed PO was cut below requested qty by weekly capacity"),
], lifecycle="ACTIVE <-> ON_HOLD"))

# ----------------------------------------------------------------- bridges / reference
_t(Table("uom_conversion", "reference", "uom_conversion_id", "Unit-of-measure conversion to base unit EA.", [
    Col("uom_conversion_id", "str", unique=True, rule="UOM-<sku>-<from_uom>"),
    Col("sku_id", "str", fk="sku.sku_id"),
    Col("from_uom", "str", allowed=("CASE", "EA")),
    Col("to_uom", "str", allowed=("EA",)),
    Col("factor", "int", unit="EA per from_uom", rule="CASE factor = sku.pack_size; EA factor = 1"),
], natural_key=("sku_id", "from_uom"), cardinality="SKU 1:N UoM_Conversion"))

_t(Table("sku_location", "bridge", "sku_location_id", "Assortment bridge (SKU N:M Location).", [
    Col("sku_location_id", "str", unique=True, rule="SL-<sku>-<location>"),
    Col("sku_id", "str", fk="sku.sku_id"),
    Col("location_id", "str", fk="location.location_id"),
    Col("stocking_role", "str", allowed=("SELL", "COMPONENT"), rule="COMPONENT rows exist only at plants for BOM components"),
    Col("effective_from", "date"),
], natural_key=("sku_id", "location_id"), cardinality="SKU N:M Location"))

_t(Table("supplier_sku", "bridge", "supplier_sku_id", "Approved sourcing bridge (Supplier N:M SKU) with commercial terms.", [
    Col("supplier_sku_id", "str", unique=True, rule="SS-<supplier>-<sku>"),
    Col("supplier_id", "str", fk="supplier.supplier_id"),
    Col("sku_id", "str", fk="sku.sku_id", rule="BUY SKUs only"),
    Col("is_primary", "bool", rule="exactly one primary per SKU"),
    Col("unit_cost", "float", unit="currency/EA"),
    Col("moq_base_qty", "int", unit="EA", rule="multiple of order_multiple_base_qty"),
    Col("order_multiple_base_qty", "int", unit="EA", rule="= sku.pack_size"),
    Col("order_uom", "str", allowed=("CASE", "EA")),
    Col("effective_from", "date"),
    Col("effective_to", "date", required=False),
], natural_key=("supplier_id", "sku_id"), cardinality="Supplier N:M SKU"))

_t(Table("sku_substitute", "bridge", "substitute_id", "Substitute bridge (SKU N:M SKU). substitute_sku_id may replace sku_id.", [
    Col("substitute_id", "str", unique=True, rule="SUB-<sku>-<substitute>"),
    Col("sku_id", "str", fk="sku.sku_id"),
    Col("substitute_sku_id", "str", fk="sku.sku_id", rule="same category, != sku_id"),
    Col("conversion_ratio", "float", unit="EA of sku per EA of substitute"),
    Col("review_status", "str", allowed=("APPROVED", "PENDING", "REJECTED")),
    Col("approved", "bool", rule="DERIVED: review_status == APPROVED"),
    Col("approved_on", "date", required=False, rule="required iff approved"),
], natural_key=("sku_id", "substitute_sku_id"), cardinality="SKU N:M SKU", lifecycle="PENDING -> APPROVED | REJECTED"))

_t(Table("bom", "bridge", "bom_id", "Bill of materials (MAKE parent N:M BUY component).", [
    Col("bom_id", "str", unique=True, rule="BOM-<parent>-<component>"),
    Col("parent_sku_id", "str", fk="sku.sku_id", rule="MAKE SKU"),
    Col("component_sku_id", "str", fk="sku.sku_id", rule="BUY SKU"),
    Col("qty_per", "int", unit="EA component per EA parent", rule="1..4"),
    Col("effective_from", "date"),
], natural_key=("parent_sku_id", "component_sku_id"), cardinality="SKU N:M SKU"))

_t(Table("lead_time", "reference", "lead_time_id", "Supplier -> location replenishment lead time.", [
    Col("lead_time_id", "str", unique=True, rule="LT-<supplier>-<location>"),
    Col("supplier_id", "str", fk="supplier.supplier_id"),
    Col("location_id", "str", fk="location.location_id"),
    Col("lead_time_weeks", "int", unit="weeks", rule="1..16; > transit_weeks"),
    Col("transit_weeks", "int", unit="weeks", rule="1..3"),
    Col("effective_from", "date"),
    Col("effective_to", "date", required=False),
], natural_key=("supplier_id", "location_id"), cardinality="Supplier 1:N LeadTime; Location 1:N LeadTime"))

_t(Table("supplier_capacity", "reference", "supplier_capacity_id", "Weekly supplier delivery capacity (by promised week).", [
    Col("supplier_capacity_id", "str", unique=True, rule="SCAP-<supplier>-<week>"),
    Col("supplier_id", "str", fk="supplier.supplier_id"),
    Col("week", "week", pattern=W),
    Col("capacity_base_qty", "int", unit="EA/week", rule=">= 0"),
], natural_key=("supplier_id", "week"), cardinality="Supplier 1:N SupplierCapacity"))

_t(Table("production_capacity", "reference", "production_capacity_id", "Weekly plant production capacity.", [
    Col("production_capacity_id", "str", unique=True, rule="PCAP-<location>-<week>"),
    Col("location_id", "str", fk="location.location_id", rule="PLANT"),
    Col("week", "week", pattern=W),
    Col("capacity_base_qty", "int", unit="EA/week"),
], natural_key=("location_id", "week"), cardinality="Location 1:N ProductionCapacity"))

# ----------------------------------------------------------------- transactions
_t(Table("forecast_demand", "transaction", "demand_id", "Weekly SKU-location forecast (independent demand).", [
    Col("demand_id", "str", unique=True, pattern=PATTERNS["demand"]),
    Col("sku_id", "str", fk="sku.sku_id"),
    Col("location_id", "str", fk="location.location_id"),
    Col("week", "week", pattern=W),
    Col("baseline_qty", "int", unit="EA", rule=">= 0"),
    Col("uplift_qty", "int", unit="EA", rule=">= 0; promotion/event spike component"),
    Col("forecast_qty", "int", unit="EA", rule="DERIVED: baseline_qty + uplift_qty"),
    Col("uom", "str", allowed=("EA",)),
], natural_key=("sku_id", "location_id", "week"), cardinality="SKU-Location 1:N ForecastDemand (52 weeks)"))

_t(Table("inventory", "transaction", "inventory_id", "On-hand snapshot at the start of 2026W01.", [
    Col("inventory_id", "str", unique=True, rule="INV-<sku>-<location>"),
    Col("sku_id", "str", fk="sku.sku_id"),
    Col("location_id", "str", fk="location.location_id"),
    Col("snapshot_week", "week", pattern=W),
    Col("on_hand_qty", "int", unit="EA", rule=">= 0"),
    Col("allocated_qty", "int", unit="EA", rule="0 <= allocated <= on_hand"),
    Col("available_qty", "int", unit="EA", rule="DERIVED: on_hand_qty - allocated_qty"),
    Col("in_transit_qty", "int", unit="EA", rule="DERIVED: sum(inbound_shipment.qty_base) for POs to this SKU-location; "
        "informational - the plan credits inbound once, from shipment lines"),
    Col("uom", "str", allowed=("EA",)),
], natural_key=("sku_id", "location_id"), cardinality="SKU-Location 1:1 Inventory"))

_t(Table("purchase_order", "transaction", "po_id", "Inbound purchase orders. Status is derived from PO events.", [
    Col("po_id", "str", unique=True, pattern=PO),
    Col("supplier_id", "str", fk="supplier.supplier_id"),
    Col("sku_id", "str", fk="sku.sku_id"),
    Col("location_id", "str", fk="location.location_id"),
    Col("substitute_for_sku_id", "str", required=False, fk="sku.sku_id", rule="set when this PO buys a substitute to cover another SKU"),
    Col("created_week", "week", pattern=W, rule="<= snapshot week"),
    Col("order_week", "week", pattern=W, rule=">= created_week"),
    Col("promised_week", "week", pattern=W, rule="= order_week + lead_time_weeks"),
    Col("order_qty", "int", unit="order_uom", rule="> 0"),
    Col("order_uom", "str", allowed=("CASE", "EA")),
    Col("requested_base_qty", "int", unit="EA", rule="DERIVED: order_qty * uom factor; >= MOQ; multiple of order multiple"),
    Col("confirmed_base_qty", "int", required=False, unit="EA", rule="<= requested; null when CREATED or CANCELLED"),
    Col("unit_cost", "float", unit="currency/EA"),
    Col("status", "str", allowed=PO_STATUS, rule="DERIVED from latest non-DELAYED PO event"),
], cardinality="Supplier 1:N PO; SKU 1:N PO; Location 1:N PO",
    lifecycle="CREATED -> CONFIRMED -> SHIPPED (-> DELAYED); CREATED|CONFIRMED -> CANCELLED"))

_t(Table("po_event", "event", "event_id", "Append-only PO state-change history.", [
    Col("event_id", "str", unique=True, rule="POE-2026-0000001"),
    Col("po_id", "str", fk="purchase_order.po_id"),
    Col("event_seq", "int", rule="1..n per PO, strictly increasing"),
    Col("event_type", "str", allowed=PO_EVENT),
    Col("event_week", "week", pattern=W, rule="non-decreasing within a PO; <= snapshot"),
    Col("actor", "str", allowed=("PLANNER", "SUPPLIER", "CARRIER"), rule="CARRIER = carrier / warehouse operator (ASN, transport delays)"),
    Col("qty_base", "int", required=False, unit="EA"),
    Col("new_promised_week", "week", required=False, pattern=W, rule="DELAYED only; > previous promise"),
    Col("reason", "str", required=False),
], natural_key=("po_id", "event_seq"), cardinality="PO 1:N PO_Event"))

_t(Table("inbound_shipment", "transaction", "shipment_id", "Carrier advance shipping notices for shipped POs.", [
    Col("shipment_id", "str", unique=True, rule="SHP-2026-000001"),
    Col("po_id", "str", fk="purchase_order.po_id"),
    Col("carrier", "str", allowed=tuple(CARRIERS)),
    Col("ship_week", "week", pattern=W),
    Col("eta_week", "week", pattern=W, rule="= ship_week + transit_weeks + delay_weeks"),
    Col("delay_weeks", "int", unit="weeks", rule=">= 0"),
    Col("qty_base", "int", unit="EA", rule="sum per PO <= confirmed_base_qty"),
    Col("shipment_status", "str", allowed=("IN_TRANSIT",)),
], cardinality="PO 1:N InboundShipment (expected 1:1)"))

_t(Table("production_plan", "transaction", "production_plan_id", "Planned production of MAKE SKUs at plants.", [
    Col("production_plan_id", "str", unique=True, rule="PP-2026-000001"),
    Col("sku_id", "str", fk="sku.sku_id"),
    Col("location_id", "str", fk="location.location_id"),
    Col("week", "week", pattern=W),
    Col("planned_qty", "int", unit="EA", rule="> 0; plant total <= production capacity"),
    Col("status", "str", allowed=("FIRM", "PLANNED"), rule="FIRM for weeks 1-4"),
], natural_key=("sku_id", "location_id", "week"), cardinality="SKU-Plant 1:N ProductionPlan"))

# ----------------------------------------------------------------- derived planning outputs
_t(Table("projected_balance", "derived", "balance_id", "Projected available balance per SKU-location-week (cleaned plan).", [
    Col("balance_id", "str", unique=True, rule="PAB-<sku>-<location>-<week>"),
    Col("sku_id", "str", fk="sku.sku_id"),
    Col("location_id", "str", fk="location.location_id"),
    Col("week", "week", pattern=W),
    Col("opening_qty", "int", unit="EA", rule="week 1 = inventory.available_qty; else previous closing"),
    Col("receipt_qty", "int", unit="EA", rule="= sum(receipt_line.qty_base)"),
    Col("production_qty", "int", unit="EA"),
    Col("forecast_qty", "int", unit="EA"),
    Col("dependent_demand_qty", "int", unit="EA", rule="sum(parent planned_qty * qty_per)"),
    Col("closing_qty", "int", unit="EA", rule="opening + receipts + production - forecast - dependent"),
    Col("safety_stock_qty", "int", unit="EA"),
    Col("below_safety_stock", "bool"),
    Col("in_shortage", "bool", rule="closing_qty < 0"),
], natural_key=("sku_id", "location_id", "week")))

_t(Table("receipt_line", "derived", "receipt_line_id", "Every supply receipt credited to the plan, with its source record.", [
    Col("receipt_line_id", "str", unique=True),
    Col("po_id", "str", fk="purchase_order.po_id"),
    Col("shipment_id", "str", required=False, fk="inbound_shipment.shipment_id"),
    Col("sku_id", "str", fk="sku.sku_id", rule="credited SKU (substitute_for_sku_id when an approved substitute PO)"),
    Col("location_id", "str", fk="location.location_id"),
    Col("week", "week", pattern=W),
    Col("qty_base", "int", unit="EA"),
    Col("basis", "str", allowed=("SHIPMENT_ETA", "PO_PROMISED", "PO_DELAYED")),
    Col("adjustment", "str", required=False, rule="quarantine correction applied by the cleaned plan"),
]))

_t(Table("shortage", "derived", "shortage_id", "Shortage = contiguous run of weeks with negative projected balance.", [
    Col("shortage_id", "str", unique=True, pattern=SHORT),
    Col("sku_id", "str", fk="sku.sku_id"),
    Col("location_id", "str", fk="location.location_id"),
    Col("start_week", "week", pattern=W),
    Col("end_week", "week", pattern=W, rule=">= start_week"),
    Col("peak_week", "week", pattern=W),
    Col("shortage_qty", "int", unit="EA", rule="= -min(closing_qty) over the run"),
    Col("recoverable", "bool", rule="start_week - snapshot >= min replenishment lead time"),
    Col("min_lead_time_weeks", "int", unit="weeks"),
    Col("priority_score", "float", unit="0-100"),
    Col("priority_rank", "int", unique=True),
    Col("visible_in_raw_plan", "bool", rule="false = hidden by a data anomaly in the uncleaned plan"),
    Col("mitigated_qty", "int", unit="EA"),
    Col("residual_qty", "int", unit="EA"),
    Col("fill_pct", "float", unit="%"),
    Col("status", "str", allowed=SHORT_STATUS),
], lifecycle="DETECTED -> MITIGATION_PROPOSED -> " + " | ".join(SHORT_STATUS)))

_t(Table("shortage_cause", "derived", "cause_id", "Counterfactual cause attribution; contributions sum to shortage_qty.", [
    Col("cause_id", "str", unique=True),
    Col("shortage_id", "str", fk="shortage.shortage_id"),
    Col("cause_type", "str", allowed=CAUSES),
    Col("contributed_qty", "int", unit="EA", rule="> 0"),
    Col("share_pct", "float", unit="%"),
    Col("source_record_ids", "str", required=False, rule="pipe-separated evidence ids"),
]))

_t(Table("mitigation_option", "derived", "mitigation_id", "Candidate mitigations with cost/service trade-offs.", [
    Col("mitigation_id", "str", unique=True, pattern=MIT),
    Col("shortage_id", "str", fk="shortage.shortage_id"),
    Col("option_type", "str", allowed=OPTIONS),
    Col("source_id", "str", required=False, rule="supplier / donor location / substitute SKU / plant"),
    Col("order_week", "week", required=False, pattern=W),
    Col("arrival_week", "week", required=False, pattern=W),
    Col("offered_qty", "int", unit="EA"),
    Col("cost", "float", unit="currency"),
    Col("cost_per_unit", "float", required=False, unit="currency/EA"),
    Col("fill_pct", "float", unit="%"),
    Col("feasible", "bool"),
    Col("rejection_reason", "str", required=False),
    Col("dominated", "bool", rule="another feasible option has >= fill and <= cost"),
    Col("selected", "bool"),
    Col("selected_qty", "int", unit="EA"),
    Col("selected_cost", "float", unit="currency"),
], lifecycle="PROPOSED -> SELECTED | REJECTED"))

_t(Table("capacity_ledger", "derived", "ledger_id", "Every unit of shared capacity/stock consumed by selected mitigations.", [
    Col("ledger_id", "str", unique=True),
    Col("mitigation_id", "str", fk="mitigation_option.mitigation_id"),
    Col("resource_type", "str", allowed=("SUPPLIER_CAPACITY", "PLANT_CAPACITY", "DONOR_STOCK", "SUBSTITUTE_STOCK", "COMPONENT_STOCK")),
    Col("resource_id", "str"),
    Col("week", "week", pattern=W),
    Col("qty_base", "int", unit="EA"),
]))

_t(Table("shortage_event", "event", "event_id", "Shortage lifecycle history.", [
    Col("event_id", "str", unique=True),
    Col("shortage_id", "str", fk="shortage.shortage_id"),
    Col("event_seq", "int"),
    Col("event_type", "str", allowed=("DETECTED", "MITIGATION_PROPOSED") + SHORT_STATUS),
    Col("event_week", "week", pattern=W),
    Col("actor", "str", allowed=ACTORS, rule="PLANNER detects/proposes; OPERATIONS_MANAGER closes when any selected option needed approval"),
    Col("detail", "str", required=False),
]))

_t(Table("mitigation_event", "event", "event_id", "Mitigation option lifecycle history.", [
    Col("event_id", "str", unique=True),
    Col("mitigation_id", "str", fk="mitigation_option.mitigation_id"),
    Col("event_seq", "int"),
    Col("event_type", "str", allowed=("PROPOSED", "SELECTED", "REJECTED")),
    Col("event_week", "week", pattern=W),
    Col("actor", "str", allowed=ACTORS, rule="proposer: LOGISTICS_ANALYST for TRANSFER/EXPEDITE else PLANNER; "
        "SELECTED approver: OPERATIONS_MANAGER for ACCEPT_SHORTFALL or selected_cost >= threshold"),
    Col("reason", "str", required=False),
]))

_t(Table("exception", "derived", "exception_id", "Anomalies found by the blind detector (never reads ground truth).", [
    Col("exception_id", "str", unique=True),
    Col("issue_type", "str", allowed=ISSUE_TYPES),
    Col("entity", "str"),
    Col("record_id", "str"),
    Col("related_record_ids", "str", required=False),
    Col("rule", "str"),
    Col("owner", "str", allowed=ACTORS, rule="role that resolves it: LOGISTICS_ANALYST for shipment issues, PLANNER otherwise"),
    Col("observed_value", "str", required=False),
    Col("suggested_value", "str", required=False, rule="correction applied by the cleaned plan"),
]))

_t(Table("ground_truth", "label", "issue_id", "Labels for injected anomalies and boundary cases. NEVER an input to detect/plan.", [
    Col("issue_id", "str", unique=True),
    Col("issue_type", "str", allowed=ISSUE_TYPES + BOUNDARY_TYPES),
    Col("expected_flag", "bool", rule="true = detector must flag; false = valid boundary, must not be flagged"),
    Col("entity", "str"),
    Col("record_id", "str"),
    Col("related_record_ids", "str", required=False),
    Col("field", "str", required=False),
    Col("correct_value", "str", required=False),
    Col("corrupted_value", "str", required=False),
    Col("impact_base_qty", "int", required=False, unit="EA"),
    Col("rule", "str"),
]))

INPUT_TABLES = ["sku", "location", "supplier", "uom_conversion", "sku_location", "supplier_sku",
                "sku_substitute", "bom", "lead_time", "supplier_capacity", "production_capacity",
                "forecast_demand", "inventory", "purchase_order", "po_event", "inbound_shipment",
                "production_plan"]
OUTPUT_TABLES = ["exception", "receipt_line", "projected_balance", "shortage", "shortage_cause",
                 "mitigation_option", "capacity_ledger", "shortage_event", "mitigation_event"]


def columns(table: str) -> list[str]:
    return [c.name for c in TABLES[table].cols]


SQL_TYPES = {"str": "TEXT", "int": "INTEGER", "float": "REAL", "bool": "INTEGER", "week": "TEXT", "date": "TEXT"}


def to_sql_ddl() -> str:
    order = INPUT_TABLES + OUTPUT_TABLES
    out = ["-- Generated from oryva/schema.py. Load order respects foreign keys.", "PRAGMA foreign_keys = ON;", ""]
    for name in order:
        t = TABLES[name]
        lines = []
        for c in t.cols:
            s = f"  {c.name} {SQL_TYPES[c.type]}"
            if c.name == t.pk:
                s += " PRIMARY KEY"
            elif c.required:
                s += " NOT NULL"
            if c.allowed and c.type == "str":
                vals = ", ".join(f"'{v}'" for v in c.allowed)
                s += f" CHECK ({c.name} IN ({vals}))"
            lines.append(s)
        for c in t.cols:
            if c.fk:
                ft, fc = c.fk.split(".")
                lines.append(f"  FOREIGN KEY ({c.name}) REFERENCES {ft}({fc})")
        if t.natural_key:
            lines.append(f"  UNIQUE ({', '.join(t.natural_key)})")
        out.append(f"CREATE TABLE {name} (\n" + ",\n".join(lines) + "\n);\n")
    return "\n".join(out)


def to_markdown() -> str:
    out = ["# Data dictionary", "",
           "Generated from `oryva/schema.py` (the same definitions drive the validator and `schema/schema.sql`).",
           "Quantities are in base unit **EA** unless the column says otherwise. Weeks are ISO labels (`2026W01`).", ""]
    for name, t in TABLES.items():
        out.append(f"## `{name}` ({t.kind})")
        out.append("")
        out.append(t.desc)
        out.append("")
        meta = [f"**Primary key:** `{t.pk}`"]
        if t.natural_key:
            meta.append(f"**Unique natural key:** `({', '.join(t.natural_key)})`")
        if t.cardinality:
            meta.append(f"**Cardinality:** {t.cardinality}")
        if t.lifecycle:
            meta.append(f"**Lifecycle:** {t.lifecycle}")
        out.append("  \n".join(meta))
        out.append("")
        out.append("| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |")
        out.append("|---|---|---|---|---|---|---|---|")
        for c in t.cols:
            allowed = ", ".join(map(str, c.allowed)) if c.allowed else (f"`{c.pattern}`" if c.pattern else "")
            out.append(f"| `{c.name}` | {c.type} | {'yes' if c.required else 'no'} | {allowed} | {c.unit} | "
                       f"{'yes' if (c.unique or c.name == t.pk) else ''} | {c.fk or ''} | {c.rule} |")
        out.append("")
    return "\n".join(out)
