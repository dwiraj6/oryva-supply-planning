# Data dictionary

Generated from `oryva/schema.py` (the same definitions drive the validator and `schema/schema.sql`).
Quantities are in base unit **EA** unless the column says otherwise. Weeks are ISO labels (`2026W01`).

## `sku` (master)

Stock keeping unit master.

**Primary key:** `sku_id`  
**Lifecycle:** NEW -> ACTIVE -> PHASE_OUT

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `sku_id` | str | yes | `SKU-\d{6}` |  | yes |  | SKU-000001 counter, immutable |
| `sku_name` | str | yes |  |  |  |  |  |
| `category` | str | yes | BEVERAGES, SNACKS, DAIRY, HOUSEHOLD, PERSONAL_CARE, ELECTRONICS, HARDWARE, PHARMA |  |  |  |  |
| `abc_class` | str | yes | A, B, C |  |  |  | A=top 20% by volume driver, B=30%, C=50% |
| `make_or_buy` | str | yes | MAKE, BUY |  |  |  |  |
| `base_uom` | str | yes | EA |  |  |  |  |
| `pack_size` | int | yes | 6, 12, 24, 48 | EA per CASE |  |  |  |
| `unit_cost` | float | yes |  | currency/EA |  |  | > 0 |
| `unit_price` | float | yes |  | currency/EA |  |  | > unit_cost |
| `safety_stock_weeks` | float | yes |  | weeks |  |  | A=2.0, B=1.5, C=1.0 |
| `lifecycle_status` | str | yes | ACTIVE, NEW, PHASE_OUT |  |  |  |  |
| `effective_from` | date | yes |  |  |  |  |  |
| `effective_to` | date | no |  |  |  |  | >= effective_from when present |

## `location` (master)

Plants, distribution centres and warehouses.

**Primary key:** `location_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `location_id` | str | yes | `LOC-\d{3}` |  | yes |  |  |
| `location_name` | str | yes |  |  |  |  |  |
| `location_type` | str | yes | PLANT, DC, WAREHOUSE |  |  |  | every 10th location (LOC-001, LOC-011..) is a PLANT |
| `region` | str | yes | NORTH, SOUTH, EAST, WEST, CENTRAL |  |  |  |  |
| `storage_capacity_units` | int | yes |  | EA |  |  | > 0 |

## `supplier` (master)

Supplier master.

**Primary key:** `supplier_id`  
**Lifecycle:** ACTIVE <-> ON_HOLD

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `supplier_id` | str | yes | `SUP-\d{4}` |  | yes |  |  |
| `supplier_name` | str | yes |  |  |  |  |  |
| `region` | str | yes | NORTH, SOUTH, EAST, WEST, CENTRAL |  |  |  |  |
| `reliability_score` | float | yes |  | 0-1 |  |  | 0 < x <= 1; drives supplier delay probability |
| `status` | str | yes | ACTIVE, ON_HOLD |  |  |  | ON_HOLD suppliers may not receive new POs |
| `capacity_constrained` | bool | yes |  |  |  |  | DERIVED: true if any confirmed PO was cut below requested qty by weekly capacity |

## `uom_conversion` (reference)

Unit-of-measure conversion to base unit EA.

**Primary key:** `uom_conversion_id`  
**Unique natural key:** `(sku_id, from_uom)`  
**Cardinality:** SKU 1:N UoM_Conversion

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `uom_conversion_id` | str | yes |  |  | yes |  | UOM-<sku>-<from_uom> |
| `sku_id` | str | yes |  |  |  | sku.sku_id |  |
| `from_uom` | str | yes | CASE, EA |  |  |  |  |
| `to_uom` | str | yes | EA |  |  |  |  |
| `factor` | int | yes |  | EA per from_uom |  |  | CASE factor = sku.pack_size; EA factor = 1 |

## `sku_location` (bridge)

Assortment bridge (SKU N:M Location).

**Primary key:** `sku_location_id`  
**Unique natural key:** `(sku_id, location_id)`  
**Cardinality:** SKU N:M Location

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `sku_location_id` | str | yes |  |  | yes |  | SL-<sku>-<location> |
| `sku_id` | str | yes |  |  |  | sku.sku_id |  |
| `location_id` | str | yes |  |  |  | location.location_id |  |
| `stocking_role` | str | yes | SELL, COMPONENT |  |  |  | COMPONENT rows exist only at plants for BOM components |
| `effective_from` | date | yes |  |  |  |  |  |

## `supplier_sku` (bridge)

Approved sourcing bridge (Supplier N:M SKU) with commercial terms.

**Primary key:** `supplier_sku_id`  
**Unique natural key:** `(supplier_id, sku_id)`  
**Cardinality:** Supplier N:M SKU

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `supplier_sku_id` | str | yes |  |  | yes |  | SS-<supplier>-<sku> |
| `supplier_id` | str | yes |  |  |  | supplier.supplier_id |  |
| `sku_id` | str | yes |  |  |  | sku.sku_id | BUY SKUs only |
| `is_primary` | bool | yes |  |  |  |  | exactly one primary per SKU |
| `unit_cost` | float | yes |  | currency/EA |  |  |  |
| `moq_base_qty` | int | yes |  | EA |  |  | multiple of order_multiple_base_qty |
| `order_multiple_base_qty` | int | yes |  | EA |  |  | = sku.pack_size |
| `order_uom` | str | yes | CASE, EA |  |  |  |  |
| `effective_from` | date | yes |  |  |  |  |  |
| `effective_to` | date | no |  |  |  |  |  |

## `sku_substitute` (bridge)

Substitute bridge (SKU N:M SKU). substitute_sku_id may replace sku_id.

**Primary key:** `substitute_id`  
**Unique natural key:** `(sku_id, substitute_sku_id)`  
**Cardinality:** SKU N:M SKU  
**Lifecycle:** PENDING -> APPROVED | REJECTED

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `substitute_id` | str | yes |  |  | yes |  | SUB-<sku>-<substitute> |
| `sku_id` | str | yes |  |  |  | sku.sku_id |  |
| `substitute_sku_id` | str | yes |  |  |  | sku.sku_id | same category, != sku_id |
| `conversion_ratio` | float | yes |  | EA of sku per EA of substitute |  |  |  |
| `review_status` | str | yes | APPROVED, PENDING, REJECTED |  |  |  |  |
| `approved` | bool | yes |  |  |  |  | DERIVED: review_status == APPROVED |
| `approved_on` | date | no |  |  |  |  | required iff approved |

## `bom` (bridge)

Bill of materials (MAKE parent N:M BUY component).

**Primary key:** `bom_id`  
**Unique natural key:** `(parent_sku_id, component_sku_id)`  
**Cardinality:** SKU N:M SKU

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `bom_id` | str | yes |  |  | yes |  | BOM-<parent>-<component> |
| `parent_sku_id` | str | yes |  |  |  | sku.sku_id | MAKE SKU |
| `component_sku_id` | str | yes |  |  |  | sku.sku_id | BUY SKU |
| `qty_per` | int | yes |  | EA component per EA parent |  |  | 1..4 |
| `effective_from` | date | yes |  |  |  |  |  |

## `lead_time` (reference)

Supplier -> location replenishment lead time.

**Primary key:** `lead_time_id`  
**Unique natural key:** `(supplier_id, location_id)`  
**Cardinality:** Supplier 1:N LeadTime; Location 1:N LeadTime

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `lead_time_id` | str | yes |  |  | yes |  | LT-<supplier>-<location> |
| `supplier_id` | str | yes |  |  |  | supplier.supplier_id |  |
| `location_id` | str | yes |  |  |  | location.location_id |  |
| `lead_time_weeks` | int | yes |  | weeks |  |  | 1..16; > transit_weeks |
| `transit_weeks` | int | yes |  | weeks |  |  | 1..3 |
| `effective_from` | date | yes |  |  |  |  |  |
| `effective_to` | date | no |  |  |  |  |  |

## `supplier_capacity` (reference)

Weekly supplier delivery capacity (by promised week).

**Primary key:** `supplier_capacity_id`  
**Unique natural key:** `(supplier_id, week)`  
**Cardinality:** Supplier 1:N SupplierCapacity

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `supplier_capacity_id` | str | yes |  |  | yes |  | SCAP-<supplier>-<week> |
| `supplier_id` | str | yes |  |  |  | supplier.supplier_id |  |
| `week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `capacity_base_qty` | int | yes |  | EA/week |  |  | >= 0 |

## `production_capacity` (reference)

Weekly plant production capacity.

**Primary key:** `production_capacity_id`  
**Unique natural key:** `(location_id, week)`  
**Cardinality:** Location 1:N ProductionCapacity

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `production_capacity_id` | str | yes |  |  | yes |  | PCAP-<location>-<week> |
| `location_id` | str | yes |  |  |  | location.location_id | PLANT |
| `week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `capacity_base_qty` | int | yes |  | EA/week |  |  |  |

## `forecast_demand` (transaction)

Weekly SKU-location forecast (independent demand).

**Primary key:** `demand_id`  
**Unique natural key:** `(sku_id, location_id, week)`  
**Cardinality:** SKU-Location 1:N ForecastDemand (52 weeks)

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `demand_id` | str | yes | `DEM-SKU-\d{6}-LOC-\d{3}-\d{4}W\d{2}` |  | yes |  |  |
| `sku_id` | str | yes |  |  |  | sku.sku_id |  |
| `location_id` | str | yes |  |  |  | location.location_id |  |
| `week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `baseline_qty` | int | yes |  | EA |  |  | >= 0 |
| `uplift_qty` | int | yes |  | EA |  |  | >= 0; promotion/event spike component |
| `forecast_qty` | int | yes |  | EA |  |  | DERIVED: baseline_qty + uplift_qty |
| `uom` | str | yes | EA |  |  |  |  |

## `inventory` (transaction)

On-hand snapshot at the start of 2026W01.

**Primary key:** `inventory_id`  
**Unique natural key:** `(sku_id, location_id)`  
**Cardinality:** SKU-Location 1:1 Inventory

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `inventory_id` | str | yes |  |  | yes |  | INV-<sku>-<location> |
| `sku_id` | str | yes |  |  |  | sku.sku_id |  |
| `location_id` | str | yes |  |  |  | location.location_id |  |
| `snapshot_week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `on_hand_qty` | int | yes |  | EA |  |  | >= 0 |
| `allocated_qty` | int | yes |  | EA |  |  | 0 <= allocated <= on_hand |
| `available_qty` | int | yes |  | EA |  |  | DERIVED: on_hand_qty - allocated_qty |
| `in_transit_qty` | int | yes |  | EA |  |  | DERIVED: sum(inbound_shipment.qty_base) for POs to this SKU-location; informational - the plan credits inbound once, from shipment lines |
| `uom` | str | yes | EA |  |  |  |  |

## `purchase_order` (transaction)

Inbound purchase orders. Status is derived from PO events.

**Primary key:** `po_id`  
**Cardinality:** Supplier 1:N PO; SKU 1:N PO; Location 1:N PO  
**Lifecycle:** CREATED -> CONFIRMED -> SHIPPED (-> DELAYED); CREATED|CONFIRMED -> CANCELLED

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `po_id` | str | yes | `PO-2026-\d{6}` |  | yes |  |  |
| `supplier_id` | str | yes |  |  |  | supplier.supplier_id |  |
| `sku_id` | str | yes |  |  |  | sku.sku_id |  |
| `location_id` | str | yes |  |  |  | location.location_id |  |
| `substitute_for_sku_id` | str | no |  |  |  | sku.sku_id | set when this PO buys a substitute to cover another SKU |
| `created_week` | week | yes | `\d{4}W\d{2}` |  |  |  | <= snapshot week |
| `order_week` | week | yes | `\d{4}W\d{2}` |  |  |  | >= created_week |
| `promised_week` | week | yes | `\d{4}W\d{2}` |  |  |  | = order_week + lead_time_weeks |
| `order_qty` | int | yes |  | order_uom |  |  | > 0 |
| `order_uom` | str | yes | CASE, EA |  |  |  |  |
| `requested_base_qty` | int | yes |  | EA |  |  | DERIVED: order_qty * uom factor; >= MOQ; multiple of order multiple |
| `confirmed_base_qty` | int | no |  | EA |  |  | <= requested; null when CREATED or CANCELLED |
| `unit_cost` | float | yes |  | currency/EA |  |  |  |
| `status` | str | yes | CREATED, CONFIRMED, SHIPPED, CANCELLED |  |  |  | DERIVED from latest non-DELAYED PO event |

## `po_event` (event)

Append-only PO state-change history.

**Primary key:** `event_id`  
**Unique natural key:** `(po_id, event_seq)`  
**Cardinality:** PO 1:N PO_Event

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `event_id` | str | yes |  |  | yes |  | POE-2026-0000001 |
| `po_id` | str | yes |  |  |  | purchase_order.po_id |  |
| `event_seq` | int | yes |  |  |  |  | 1..n per PO, strictly increasing |
| `event_type` | str | yes | CREATED, CONFIRMED, SHIPPED, DELAYED, CANCELLED |  |  |  |  |
| `event_week` | week | yes | `\d{4}W\d{2}` |  |  |  | non-decreasing within a PO; <= snapshot |
| `actor` | str | yes | PLANNER, SUPPLIER, CARRIER |  |  |  | CARRIER = carrier / warehouse operator (ASN, transport delays) |
| `qty_base` | int | no |  | EA |  |  |  |
| `new_promised_week` | week | no | `\d{4}W\d{2}` |  |  |  | DELAYED only; > previous promise |
| `reason` | str | no |  |  |  |  |  |

## `inbound_shipment` (transaction)

Carrier advance shipping notices for shipped POs.

**Primary key:** `shipment_id`  
**Cardinality:** PO 1:N InboundShipment (expected 1:1)

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `shipment_id` | str | yes |  |  | yes |  | SHP-2026-000001 |
| `po_id` | str | yes |  |  |  | purchase_order.po_id |  |
| `carrier` | str | yes | BLUEDART_FREIGHT, RAILCO, SEALINK, ROADSTAR, AIRFAST, CONTAINERX |  |  |  |  |
| `ship_week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `eta_week` | week | yes | `\d{4}W\d{2}` |  |  |  | = ship_week + transit_weeks + delay_weeks |
| `delay_weeks` | int | yes |  | weeks |  |  | >= 0 |
| `qty_base` | int | yes |  | EA |  |  | sum per PO <= confirmed_base_qty |
| `shipment_status` | str | yes | IN_TRANSIT |  |  |  |  |

## `production_plan` (transaction)

Planned production of MAKE SKUs at plants.

**Primary key:** `production_plan_id`  
**Unique natural key:** `(sku_id, location_id, week)`  
**Cardinality:** SKU-Plant 1:N ProductionPlan

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `production_plan_id` | str | yes |  |  | yes |  | PP-2026-000001 |
| `sku_id` | str | yes |  |  |  | sku.sku_id |  |
| `location_id` | str | yes |  |  |  | location.location_id |  |
| `week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `planned_qty` | int | yes |  | EA |  |  | > 0; plant total <= production capacity |
| `status` | str | yes | FIRM, PLANNED |  |  |  | FIRM for weeks 1-4 |

## `projected_balance` (derived)

Projected available balance per SKU-location-week (cleaned plan).

**Primary key:** `balance_id`  
**Unique natural key:** `(sku_id, location_id, week)`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `balance_id` | str | yes |  |  | yes |  | PAB-<sku>-<location>-<week> |
| `sku_id` | str | yes |  |  |  | sku.sku_id |  |
| `location_id` | str | yes |  |  |  | location.location_id |  |
| `week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `opening_qty` | int | yes |  | EA |  |  | week 1 = inventory.available_qty; else previous closing |
| `receipt_qty` | int | yes |  | EA |  |  | = sum(receipt_line.qty_base) |
| `production_qty` | int | yes |  | EA |  |  |  |
| `forecast_qty` | int | yes |  | EA |  |  |  |
| `dependent_demand_qty` | int | yes |  | EA |  |  | sum(parent planned_qty * qty_per) |
| `closing_qty` | int | yes |  | EA |  |  | opening + receipts + production - forecast - dependent |
| `safety_stock_qty` | int | yes |  | EA |  |  |  |
| `below_safety_stock` | bool | yes |  |  |  |  |  |
| `in_shortage` | bool | yes |  |  |  |  | closing_qty < 0 |

## `receipt_line` (derived)

Every supply receipt credited to the plan, with its source record.

**Primary key:** `receipt_line_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `receipt_line_id` | str | yes |  |  | yes |  |  |
| `po_id` | str | yes |  |  |  | purchase_order.po_id |  |
| `shipment_id` | str | no |  |  |  | inbound_shipment.shipment_id |  |
| `sku_id` | str | yes |  |  |  | sku.sku_id | credited SKU (substitute_for_sku_id when an approved substitute PO) |
| `location_id` | str | yes |  |  |  | location.location_id |  |
| `week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `qty_base` | int | yes |  | EA |  |  |  |
| `basis` | str | yes | SHIPMENT_ETA, PO_PROMISED, PO_DELAYED |  |  |  |  |
| `adjustment` | str | no |  |  |  |  | quarantine correction applied by the cleaned plan |

## `shortage` (derived)

Shortage = contiguous run of weeks with negative projected balance.

**Primary key:** `shortage_id`  
**Lifecycle:** DETECTED -> MITIGATION_PROPOSED -> MITIGATED | PARTIALLY_MITIGATED | UNMITIGATED | COVERED_BY_PRIOR_MITIGATION

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `shortage_id` | str | yes | `SHORT-2026-\d{6}` |  | yes |  |  |
| `sku_id` | str | yes |  |  |  | sku.sku_id |  |
| `location_id` | str | yes |  |  |  | location.location_id |  |
| `start_week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `end_week` | week | yes | `\d{4}W\d{2}` |  |  |  | >= start_week |
| `peak_week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `shortage_qty` | int | yes |  | EA |  |  | = -min(closing_qty) over the run |
| `recoverable` | bool | yes |  |  |  |  | start_week - snapshot >= min replenishment lead time |
| `min_lead_time_weeks` | int | yes |  | weeks |  |  |  |
| `priority_score` | float | yes |  | 0-100 |  |  |  |
| `priority_rank` | int | yes |  |  | yes |  |  |
| `visible_in_raw_plan` | bool | yes |  |  |  |  | false = hidden by a data anomaly in the uncleaned plan |
| `mitigated_qty` | int | yes |  | EA |  |  |  |
| `residual_qty` | int | yes |  | EA |  |  |  |
| `fill_pct` | float | yes |  | % |  |  |  |
| `status` | str | yes | MITIGATED, PARTIALLY_MITIGATED, UNMITIGATED, COVERED_BY_PRIOR_MITIGATION |  |  |  |  |

## `shortage_cause` (derived)

Counterfactual cause attribution; contributions sum to shortage_qty.

**Primary key:** `cause_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `cause_id` | str | yes |  |  | yes |  |  |
| `shortage_id` | str | yes |  |  |  | shortage.shortage_id |  |
| `cause_type` | str | yes | DEMAND_SPIKE, DEPENDENT_DEMAND, SUPPLIER_CAPACITY_CUT, CANCELLED_PO, SUPPLIER_DELAY, TRANSPORT_DELAY, BASE_SUPPLY_GAP |  |  |  |  |
| `contributed_qty` | int | yes |  | EA |  |  | > 0 |
| `share_pct` | float | yes |  | % |  |  |  |
| `source_record_ids` | str | no |  |  |  |  | pipe-separated evidence ids |

## `mitigation_option` (derived)

Candidate mitigations with cost/service trade-offs.

**Primary key:** `mitigation_id`  
**Lifecycle:** PROPOSED -> SELECTED | REJECTED

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `mitigation_id` | str | yes | `MIT-SHORT-2026-\d{6}-\d{2}` |  | yes |  |  |
| `shortage_id` | str | yes |  |  |  | shortage.shortage_id |  |
| `option_type` | str | yes | TRANSFER, SUBSTITUTE, PRODUCE, PLACE_PO, EXPEDITE, ACCEPT_SHORTFALL |  |  |  |  |
| `source_id` | str | no |  |  |  |  | supplier / donor location / substitute SKU / plant |
| `order_week` | week | no | `\d{4}W\d{2}` |  |  |  |  |
| `arrival_week` | week | no | `\d{4}W\d{2}` |  |  |  |  |
| `offered_qty` | int | yes |  | EA |  |  |  |
| `cost` | float | yes |  | currency |  |  |  |
| `cost_per_unit` | float | no |  | currency/EA |  |  |  |
| `fill_pct` | float | yes |  | % |  |  |  |
| `feasible` | bool | yes |  |  |  |  |  |
| `rejection_reason` | str | no |  |  |  |  |  |
| `dominated` | bool | yes |  |  |  |  | another feasible option has >= fill and <= cost |
| `selected` | bool | yes |  |  |  |  |  |
| `selected_qty` | int | yes |  | EA |  |  |  |
| `selected_cost` | float | yes |  | currency |  |  |  |

## `capacity_ledger` (derived)

Every unit of shared capacity/stock consumed by selected mitigations.

**Primary key:** `ledger_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `ledger_id` | str | yes |  |  | yes |  |  |
| `mitigation_id` | str | yes |  |  |  | mitigation_option.mitigation_id |  |
| `resource_type` | str | yes | SUPPLIER_CAPACITY, PLANT_CAPACITY, DONOR_STOCK, SUBSTITUTE_STOCK, COMPONENT_STOCK |  |  |  |  |
| `resource_id` | str | yes |  |  |  |  |  |
| `week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `qty_base` | int | yes |  | EA |  |  |  |

## `shortage_event` (event)

Shortage lifecycle history.

**Primary key:** `event_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `event_id` | str | yes |  |  | yes |  |  |
| `shortage_id` | str | yes |  |  |  | shortage.shortage_id |  |
| `event_seq` | int | yes |  |  |  |  |  |
| `event_type` | str | yes | DETECTED, MITIGATION_PROPOSED, MITIGATED, PARTIALLY_MITIGATED, UNMITIGATED, COVERED_BY_PRIOR_MITIGATION |  |  |  |  |
| `event_week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `actor` | str | yes | SUPPLIER, PLANNER, CARRIER, LOGISTICS_ANALYST, OPERATIONS_MANAGER |  |  |  | PLANNER detects/proposes; OPERATIONS_MANAGER closes when any selected option needed approval |
| `detail` | str | no |  |  |  |  |  |

## `mitigation_event` (event)

Mitigation option lifecycle history.

**Primary key:** `event_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `event_id` | str | yes |  |  | yes |  |  |
| `mitigation_id` | str | yes |  |  |  | mitigation_option.mitigation_id |  |
| `event_seq` | int | yes |  |  |  |  |  |
| `event_type` | str | yes | PROPOSED, SELECTED, REJECTED |  |  |  |  |
| `event_week` | week | yes | `\d{4}W\d{2}` |  |  |  |  |
| `actor` | str | yes | SUPPLIER, PLANNER, CARRIER, LOGISTICS_ANALYST, OPERATIONS_MANAGER |  |  |  | proposer: LOGISTICS_ANALYST for TRANSFER/EXPEDITE else PLANNER; SELECTED approver: OPERATIONS_MANAGER for ACCEPT_SHORTFALL or selected_cost >= threshold |
| `reason` | str | no |  |  |  |  |  |

## `exception` (derived)

Anomalies found by the blind detector (never reads ground truth).

**Primary key:** `exception_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `exception_id` | str | yes |  |  | yes |  |  |
| `issue_type` | str | yes | INBOUND_DOUBLE_COUNT, SUBSTITUTE_NOT_APPROVED, SUPPLIER_CAPACITY_EXCEEDED, SHORTAGE_WITHOUT_LEAD_TIME, UOM_MISMATCH |  |  |  |  |
| `entity` | str | yes |  |  |  |  |  |
| `record_id` | str | yes |  |  |  |  |  |
| `related_record_ids` | str | no |  |  |  |  |  |
| `rule` | str | yes |  |  |  |  |  |
| `owner` | str | yes | SUPPLIER, PLANNER, CARRIER, LOGISTICS_ANALYST, OPERATIONS_MANAGER |  |  |  | role that resolves it: LOGISTICS_ANALYST for shipment issues, PLANNER otherwise |
| `observed_value` | str | no |  |  |  |  |  |
| `suggested_value` | str | no |  |  |  |  | correction applied by the cleaned plan |

## `ground_truth` (label)

Labels for injected anomalies and boundary cases. NEVER an input to detect/plan.

**Primary key:** `issue_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| `issue_id` | str | yes |  |  | yes |  |  |
| `issue_type` | str | yes | INBOUND_DOUBLE_COUNT, SUBSTITUTE_NOT_APPROVED, SUPPLIER_CAPACITY_EXCEEDED, SHORTAGE_WITHOUT_LEAD_TIME, UOM_MISMATCH, BOUNDARY_PO_AT_MOQ, BOUNDARY_CAPACITY_AT_100PCT, BOUNDARY_ZERO_BALANCE, BOUNDARY_RECEIPT_AT_HORIZON_END |  |  |  |  |
| `expected_flag` | bool | yes |  |  |  |  | true = detector must flag; false = valid boundary, must not be flagged |
| `entity` | str | yes |  |  |  |  |  |
| `record_id` | str | yes |  |  |  |  |  |
| `related_record_ids` | str | no |  |  |  |  |  |
| `field` | str | no |  |  |  |  |  |
| `correct_value` | str | no |  |  |  |  |  |
| `corrupted_value` | str | no |  |  |  |  |  |
| `impact_base_qty` | int | no |  | EA |  |  |  |
| `rule` | str | yes |  |  |  |  |  |
