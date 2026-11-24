-- Generated from oryva/schema.py. Load order respects foreign keys.
PRAGMA foreign_keys = ON;

CREATE TABLE sku (
  sku_id TEXT PRIMARY KEY,
  sku_name TEXT NOT NULL,
  category TEXT NOT NULL CHECK (category IN ('BEVERAGES', 'SNACKS', 'DAIRY', 'HOUSEHOLD', 'PERSONAL_CARE', 'ELECTRONICS', 'HARDWARE', 'PHARMA')),
  abc_class TEXT NOT NULL CHECK (abc_class IN ('A', 'B', 'C')),
  make_or_buy TEXT NOT NULL CHECK (make_or_buy IN ('MAKE', 'BUY')),
  base_uom TEXT NOT NULL CHECK (base_uom IN ('EA')),
  pack_size INTEGER NOT NULL,
  unit_cost REAL NOT NULL,
  unit_price REAL NOT NULL,
  safety_stock_weeks REAL NOT NULL,
  lifecycle_status TEXT NOT NULL CHECK (lifecycle_status IN ('ACTIVE', 'NEW', 'PHASE_OUT')),
  effective_from TEXT NOT NULL,
  effective_to TEXT
);

CREATE TABLE location (
  location_id TEXT PRIMARY KEY,
  location_name TEXT NOT NULL,
  location_type TEXT NOT NULL CHECK (location_type IN ('PLANT', 'DC', 'WAREHOUSE')),
  region TEXT NOT NULL CHECK (region IN ('NORTH', 'SOUTH', 'EAST', 'WEST', 'CENTRAL')),
  storage_capacity_units INTEGER NOT NULL
);

CREATE TABLE supplier (
  supplier_id TEXT PRIMARY KEY,
  supplier_name TEXT NOT NULL,
  region TEXT NOT NULL CHECK (region IN ('NORTH', 'SOUTH', 'EAST', 'WEST', 'CENTRAL')),
  reliability_score REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'ON_HOLD')),
  capacity_constrained INTEGER NOT NULL
);

CREATE TABLE uom_conversion (
  uom_conversion_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL,
  from_uom TEXT NOT NULL CHECK (from_uom IN ('CASE', 'EA')),
  to_uom TEXT NOT NULL CHECK (to_uom IN ('EA')),
  factor INTEGER NOT NULL,
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  UNIQUE (sku_id, from_uom)
);

CREATE TABLE sku_location (
  sku_location_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  stocking_role TEXT NOT NULL CHECK (stocking_role IN ('SELL', 'COMPONENT')),
  effective_from TEXT NOT NULL,
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  FOREIGN KEY (location_id) REFERENCES location(location_id),
  UNIQUE (sku_id, location_id)
);

CREATE TABLE supplier_sku (
  supplier_sku_id TEXT PRIMARY KEY,
  supplier_id TEXT NOT NULL,
  sku_id TEXT NOT NULL,
  is_primary INTEGER NOT NULL,
  unit_cost REAL NOT NULL,
  moq_base_qty INTEGER NOT NULL,
  order_multiple_base_qty INTEGER NOT NULL,
  order_uom TEXT NOT NULL CHECK (order_uom IN ('CASE', 'EA')),
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  UNIQUE (supplier_id, sku_id)
);

CREATE TABLE sku_substitute (
  substitute_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL,
  substitute_sku_id TEXT NOT NULL,
  conversion_ratio REAL NOT NULL,
  review_status TEXT NOT NULL CHECK (review_status IN ('APPROVED', 'PENDING', 'REJECTED')),
  approved INTEGER NOT NULL,
  approved_on TEXT,
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  FOREIGN KEY (substitute_sku_id) REFERENCES sku(sku_id),
  UNIQUE (sku_id, substitute_sku_id)
);

CREATE TABLE bom (
  bom_id TEXT PRIMARY KEY,
  parent_sku_id TEXT NOT NULL,
  component_sku_id TEXT NOT NULL,
  qty_per INTEGER NOT NULL,
  effective_from TEXT NOT NULL,
  FOREIGN KEY (parent_sku_id) REFERENCES sku(sku_id),
  FOREIGN KEY (component_sku_id) REFERENCES sku(sku_id),
  UNIQUE (parent_sku_id, component_sku_id)
);

CREATE TABLE lead_time (
  lead_time_id TEXT PRIMARY KEY,
  supplier_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  lead_time_weeks INTEGER NOT NULL,
  transit_weeks INTEGER NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
  FOREIGN KEY (location_id) REFERENCES location(location_id),
  UNIQUE (supplier_id, location_id)
);

CREATE TABLE supplier_capacity (
  supplier_capacity_id TEXT PRIMARY KEY,
  supplier_id TEXT NOT NULL,
  week TEXT NOT NULL,
  capacity_base_qty INTEGER NOT NULL,
  FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
  UNIQUE (supplier_id, week)
);

CREATE TABLE production_capacity (
  production_capacity_id TEXT PRIMARY KEY,
  location_id TEXT NOT NULL,
  week TEXT NOT NULL,
  capacity_base_qty INTEGER NOT NULL,
  FOREIGN KEY (location_id) REFERENCES location(location_id),
  UNIQUE (location_id, week)
);

CREATE TABLE forecast_demand (
  demand_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  week TEXT NOT NULL,
  baseline_qty INTEGER NOT NULL,
  uplift_qty INTEGER NOT NULL,
  forecast_qty INTEGER NOT NULL,
  uom TEXT NOT NULL CHECK (uom IN ('EA')),
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  FOREIGN KEY (location_id) REFERENCES location(location_id),
  UNIQUE (sku_id, location_id, week)
);

CREATE TABLE inventory (
  inventory_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  snapshot_week TEXT NOT NULL,
  on_hand_qty INTEGER NOT NULL,
  allocated_qty INTEGER NOT NULL,
  available_qty INTEGER NOT NULL,
  in_transit_qty INTEGER NOT NULL,
  uom TEXT NOT NULL CHECK (uom IN ('EA')),
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  FOREIGN KEY (location_id) REFERENCES location(location_id),
  UNIQUE (sku_id, location_id)
);

CREATE TABLE purchase_order (
  po_id TEXT PRIMARY KEY,
  supplier_id TEXT NOT NULL,
  sku_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  substitute_for_sku_id TEXT,
  created_week TEXT NOT NULL,
  order_week TEXT NOT NULL,
  promised_week TEXT NOT NULL,
  order_qty INTEGER NOT NULL,
  order_uom TEXT NOT NULL CHECK (order_uom IN ('CASE', 'EA')),
  requested_base_qty INTEGER NOT NULL,
  confirmed_base_qty INTEGER,
  unit_cost REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('CREATED', 'CONFIRMED', 'SHIPPED', 'CANCELLED')),
  FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  FOREIGN KEY (location_id) REFERENCES location(location_id),
  FOREIGN KEY (substitute_for_sku_id) REFERENCES sku(sku_id)
);

CREATE TABLE po_event (
  event_id TEXT PRIMARY KEY,
  po_id TEXT NOT NULL,
  event_seq INTEGER NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('CREATED', 'CONFIRMED', 'SHIPPED', 'DELAYED', 'CANCELLED')),
  event_week TEXT NOT NULL,
  actor TEXT NOT NULL CHECK (actor IN ('PLANNER', 'SUPPLIER', 'CARRIER')),
  qty_base INTEGER,
  new_promised_week TEXT,
  reason TEXT,
  FOREIGN KEY (po_id) REFERENCES purchase_order(po_id),
  UNIQUE (po_id, event_seq)
);

CREATE TABLE inbound_shipment (
  shipment_id TEXT PRIMARY KEY,
  po_id TEXT NOT NULL,
  carrier TEXT NOT NULL CHECK (carrier IN ('BLUEDART_FREIGHT', 'RAILCO', 'SEALINK', 'ROADSTAR', 'AIRFAST', 'CONTAINERX')),
  ship_week TEXT NOT NULL,
  eta_week TEXT NOT NULL,
  delay_weeks INTEGER NOT NULL,
  qty_base INTEGER NOT NULL,
  shipment_status TEXT NOT NULL CHECK (shipment_status IN ('IN_TRANSIT')),
  FOREIGN KEY (po_id) REFERENCES purchase_order(po_id)
);

CREATE TABLE production_plan (
  production_plan_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  week TEXT NOT NULL,
  planned_qty INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('FIRM', 'PLANNED')),
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  FOREIGN KEY (location_id) REFERENCES location(location_id),
  UNIQUE (sku_id, location_id, week)
);

CREATE TABLE exception (
  exception_id TEXT PRIMARY KEY,
  issue_type TEXT NOT NULL CHECK (issue_type IN ('INBOUND_DOUBLE_COUNT', 'SUBSTITUTE_NOT_APPROVED', 'SUPPLIER_CAPACITY_EXCEEDED', 'SHORTAGE_WITHOUT_LEAD_TIME', 'UOM_MISMATCH')),
  entity TEXT NOT NULL,
  record_id TEXT NOT NULL,
  related_record_ids TEXT,
  rule TEXT NOT NULL,
  owner TEXT NOT NULL CHECK (owner IN ('SUPPLIER', 'PLANNER', 'CARRIER', 'LOGISTICS_ANALYST', 'OPERATIONS_MANAGER')),
  observed_value TEXT,
  suggested_value TEXT
);

CREATE TABLE receipt_line (
  receipt_line_id TEXT PRIMARY KEY,
  po_id TEXT NOT NULL,
  shipment_id TEXT,
  sku_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  week TEXT NOT NULL,
  qty_base INTEGER NOT NULL,
  basis TEXT NOT NULL CHECK (basis IN ('SHIPMENT_ETA', 'PO_PROMISED', 'PO_DELAYED')),
  adjustment TEXT,
  FOREIGN KEY (po_id) REFERENCES purchase_order(po_id),
  FOREIGN KEY (shipment_id) REFERENCES inbound_shipment(shipment_id),
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  FOREIGN KEY (location_id) REFERENCES location(location_id)
);

CREATE TABLE projected_balance (
  balance_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  week TEXT NOT NULL,
  opening_qty INTEGER NOT NULL,
  receipt_qty INTEGER NOT NULL,
  production_qty INTEGER NOT NULL,
  forecast_qty INTEGER NOT NULL,
  dependent_demand_qty INTEGER NOT NULL,
  closing_qty INTEGER NOT NULL,
  safety_stock_qty INTEGER NOT NULL,
  below_safety_stock INTEGER NOT NULL,
  in_shortage INTEGER NOT NULL,
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  FOREIGN KEY (location_id) REFERENCES location(location_id),
  UNIQUE (sku_id, location_id, week)
);

CREATE TABLE shortage (
  shortage_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  start_week TEXT NOT NULL,
  end_week TEXT NOT NULL,
  peak_week TEXT NOT NULL,
  shortage_qty INTEGER NOT NULL,
  recoverable INTEGER NOT NULL,
  min_lead_time_weeks INTEGER NOT NULL,
  priority_score REAL NOT NULL,
  priority_rank INTEGER NOT NULL,
  visible_in_raw_plan INTEGER NOT NULL,
  mitigated_qty INTEGER NOT NULL,
  residual_qty INTEGER NOT NULL,
  fill_pct REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('MITIGATED', 'PARTIALLY_MITIGATED', 'UNMITIGATED', 'COVERED_BY_PRIOR_MITIGATION')),
  FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
  FOREIGN KEY (location_id) REFERENCES location(location_id)
);

CREATE TABLE shortage_cause (
  cause_id TEXT PRIMARY KEY,
  shortage_id TEXT NOT NULL,
  cause_type TEXT NOT NULL CHECK (cause_type IN ('DEMAND_SPIKE', 'DEPENDENT_DEMAND', 'SUPPLIER_CAPACITY_CUT', 'CANCELLED_PO', 'SUPPLIER_DELAY', 'TRANSPORT_DELAY', 'BASE_SUPPLY_GAP')),
  contributed_qty INTEGER NOT NULL,
  share_pct REAL NOT NULL,
  source_record_ids TEXT,
  FOREIGN KEY (shortage_id) REFERENCES shortage(shortage_id)
);

CREATE TABLE mitigation_option (
  mitigation_id TEXT PRIMARY KEY,
  shortage_id TEXT NOT NULL,
  option_type TEXT NOT NULL CHECK (option_type IN ('TRANSFER', 'SUBSTITUTE', 'PRODUCE', 'PLACE_PO', 'EXPEDITE', 'ACCEPT_SHORTFALL')),
  source_id TEXT,
  order_week TEXT,
  arrival_week TEXT,
  offered_qty INTEGER NOT NULL,
  cost REAL NOT NULL,
  cost_per_unit REAL,
  fill_pct REAL NOT NULL,
  feasible INTEGER NOT NULL,
  rejection_reason TEXT,
  dominated INTEGER NOT NULL,
  selected INTEGER NOT NULL,
  selected_qty INTEGER NOT NULL,
  selected_cost REAL NOT NULL,
  FOREIGN KEY (shortage_id) REFERENCES shortage(shortage_id)
);

CREATE TABLE capacity_ledger (
  ledger_id TEXT PRIMARY KEY,
  mitigation_id TEXT NOT NULL,
  resource_type TEXT NOT NULL CHECK (resource_type IN ('SUPPLIER_CAPACITY', 'PLANT_CAPACITY', 'DONOR_STOCK', 'SUBSTITUTE_STOCK', 'COMPONENT_STOCK')),
  resource_id TEXT NOT NULL,
  week TEXT NOT NULL,
  qty_base INTEGER NOT NULL,
  FOREIGN KEY (mitigation_id) REFERENCES mitigation_option(mitigation_id)
);

CREATE TABLE shortage_event (
  event_id TEXT PRIMARY KEY,
  shortage_id TEXT NOT NULL,
  event_seq INTEGER NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('DETECTED', 'MITIGATION_PROPOSED', 'MITIGATED', 'PARTIALLY_MITIGATED', 'UNMITIGATED', 'COVERED_BY_PRIOR_MITIGATION')),
  event_week TEXT NOT NULL,
  actor TEXT NOT NULL CHECK (actor IN ('SUPPLIER', 'PLANNER', 'CARRIER', 'LOGISTICS_ANALYST', 'OPERATIONS_MANAGER')),
  detail TEXT,
  FOREIGN KEY (shortage_id) REFERENCES shortage(shortage_id)
);

CREATE TABLE mitigation_event (
  event_id TEXT PRIMARY KEY,
  mitigation_id TEXT NOT NULL,
  event_seq INTEGER NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('PROPOSED', 'SELECTED', 'REJECTED')),
  event_week TEXT NOT NULL,
  actor TEXT NOT NULL CHECK (actor IN ('SUPPLIER', 'PLANNER', 'CARRIER', 'LOGISTICS_ANALYST', 'OPERATIONS_MANAGER')),
  reason TEXT,
  FOREIGN KEY (mitigation_id) REFERENCES mitigation_option(mitigation_id)
);
