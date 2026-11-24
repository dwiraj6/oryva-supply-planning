# Validation summary (starter)

**Overall: PASS**  
Integrity checks: 428 (0 failed)  
Business-rule checks: 7; violations explained by labelled anomalies: 35; unexplained: 0  
Labelled anomalies caught by at least one rule: 25 / 25

Business-rule violations are expected ONLY on records deliberately injected and labelled in `ground_truth.csv`; any unexplained violation fails validation.

| Check | Category | Violations | Status | Notes |
|---|---|---|---|---|
| sku: primary key unique & non-null | integrity | 0 | PASS |  |
| sku.sku_id: required | integrity | 0 | PASS |  |
| sku.sku_id: pattern SKU-\d{6} | integrity | 0 | PASS |  |
| sku.sku_name: required | integrity | 0 | PASS |  |
| sku.category: required | integrity | 0 | PASS |  |
| sku.category: allowed values | integrity | 0 | PASS |  |
| sku.abc_class: required | integrity | 0 | PASS |  |
| sku.abc_class: allowed values | integrity | 0 | PASS |  |
| sku.make_or_buy: required | integrity | 0 | PASS |  |
| sku.make_or_buy: allowed values | integrity | 0 | PASS |  |
| sku.base_uom: required | integrity | 0 | PASS |  |
| sku.base_uom: allowed values | integrity | 0 | PASS |  |
| sku.pack_size: required | integrity | 0 | PASS |  |
| sku.pack_size: allowed values | integrity | 0 | PASS |  |
| sku.unit_cost: required | integrity | 0 | PASS |  |
| sku.unit_price: required | integrity | 0 | PASS |  |
| sku.safety_stock_weeks: required | integrity | 0 | PASS |  |
| sku.lifecycle_status: required | integrity | 0 | PASS |  |
| sku.lifecycle_status: allowed values | integrity | 0 | PASS |  |
| sku.effective_from: required | integrity | 0 | PASS |  |
| sku.effective_from: valid date | integrity | 0 | PASS |  |
| sku.effective_to: valid date | integrity | 0 | PASS |  |
| location: primary key unique & non-null | integrity | 0 | PASS |  |
| location.location_id: required | integrity | 0 | PASS |  |
| location.location_id: pattern LOC-\d{3} | integrity | 0 | PASS |  |
| location.location_name: required | integrity | 0 | PASS |  |
| location.location_type: required | integrity | 0 | PASS |  |
| location.location_type: allowed values | integrity | 0 | PASS |  |
| location.region: required | integrity | 0 | PASS |  |
| location.region: allowed values | integrity | 0 | PASS |  |
| location.storage_capacity_units: required | integrity | 0 | PASS |  |
| supplier: primary key unique & non-null | integrity | 0 | PASS |  |
| supplier.supplier_id: required | integrity | 0 | PASS |  |
| supplier.supplier_id: pattern SUP-\d{4} | integrity | 0 | PASS |  |
| supplier.supplier_name: required | integrity | 0 | PASS |  |
| supplier.region: required | integrity | 0 | PASS |  |
| supplier.region: allowed values | integrity | 0 | PASS |  |
| supplier.reliability_score: required | integrity | 0 | PASS |  |
| supplier.status: required | integrity | 0 | PASS |  |
| supplier.status: allowed values | integrity | 0 | PASS |  |
| supplier.capacity_constrained: required | integrity | 0 | PASS |  |
| uom_conversion: primary key unique & non-null | integrity | 0 | PASS |  |
| uom_conversion: natural key ('sku_id', 'from_uom') unique | integrity | 0 | PASS |  |
| uom_conversion.uom_conversion_id: required | integrity | 0 | PASS |  |
| uom_conversion.sku_id: required | integrity | 0 | PASS |  |
| uom_conversion.from_uom: required | integrity | 0 | PASS |  |
| uom_conversion.from_uom: allowed values | integrity | 0 | PASS |  |
| uom_conversion.to_uom: required | integrity | 0 | PASS |  |
| uom_conversion.to_uom: allowed values | integrity | 0 | PASS |  |
| uom_conversion.factor: required | integrity | 0 | PASS |  |
| sku_location: primary key unique & non-null | integrity | 0 | PASS |  |
| sku_location: natural key ('sku_id', 'location_id') unique | integrity | 0 | PASS |  |
| sku_location.sku_location_id: required | integrity | 0 | PASS |  |
| sku_location.sku_id: required | integrity | 0 | PASS |  |
| sku_location.location_id: required | integrity | 0 | PASS |  |
| sku_location.stocking_role: required | integrity | 0 | PASS |  |
| sku_location.stocking_role: allowed values | integrity | 0 | PASS |  |
| sku_location.effective_from: required | integrity | 0 | PASS |  |
| sku_location.effective_from: valid date | integrity | 0 | PASS |  |
| supplier_sku: primary key unique & non-null | integrity | 0 | PASS |  |
| supplier_sku: natural key ('supplier_id', 'sku_id') unique | integrity | 0 | PASS |  |
| supplier_sku.supplier_sku_id: required | integrity | 0 | PASS |  |
| supplier_sku.supplier_id: required | integrity | 0 | PASS |  |
| supplier_sku.sku_id: required | integrity | 0 | PASS |  |
| supplier_sku.is_primary: required | integrity | 0 | PASS |  |
| supplier_sku.unit_cost: required | integrity | 0 | PASS |  |
| supplier_sku.moq_base_qty: required | integrity | 0 | PASS |  |
| supplier_sku.order_multiple_base_qty: required | integrity | 0 | PASS |  |
| supplier_sku.order_uom: required | integrity | 0 | PASS |  |
| supplier_sku.order_uom: allowed values | integrity | 0 | PASS |  |
| supplier_sku.effective_from: required | integrity | 0 | PASS |  |
| supplier_sku.effective_from: valid date | integrity | 0 | PASS |  |
| sku_substitute: primary key unique & non-null | integrity | 0 | PASS |  |
| sku_substitute: natural key ('sku_id', 'substitute_sku_id') unique | integrity | 0 | PASS |  |
| sku_substitute.substitute_id: required | integrity | 0 | PASS |  |
| sku_substitute.sku_id: required | integrity | 0 | PASS |  |
| sku_substitute.substitute_sku_id: required | integrity | 0 | PASS |  |
| sku_substitute.conversion_ratio: required | integrity | 0 | PASS |  |
| sku_substitute.review_status: required | integrity | 0 | PASS |  |
| sku_substitute.review_status: allowed values | integrity | 0 | PASS |  |
| sku_substitute.approved: required | integrity | 0 | PASS |  |
| sku_substitute.approved_on: valid date | integrity | 0 | PASS |  |
| bom: primary key unique & non-null | integrity | 0 | PASS |  |
| bom: natural key ('parent_sku_id', 'component_sku_id') unique | integrity | 0 | PASS |  |
| bom.bom_id: required | integrity | 0 | PASS |  |
| bom.parent_sku_id: required | integrity | 0 | PASS |  |
| bom.component_sku_id: required | integrity | 0 | PASS |  |
| bom.qty_per: required | integrity | 0 | PASS |  |
| bom.effective_from: required | integrity | 0 | PASS |  |
| bom.effective_from: valid date | integrity | 0 | PASS |  |
| lead_time: primary key unique & non-null | integrity | 0 | PASS |  |
| lead_time: natural key ('supplier_id', 'location_id') unique | integrity | 0 | PASS |  |
| lead_time.lead_time_id: required | integrity | 0 | PASS |  |
| lead_time.supplier_id: required | integrity | 0 | PASS |  |
| lead_time.location_id: required | integrity | 0 | PASS |  |
| lead_time.lead_time_weeks: required | integrity | 0 | PASS |  |
| lead_time.transit_weeks: required | integrity | 0 | PASS |  |
| lead_time.effective_from: required | integrity | 0 | PASS |  |
| lead_time.effective_from: valid date | integrity | 0 | PASS |  |
| supplier_capacity: primary key unique & non-null | integrity | 0 | PASS |  |
| supplier_capacity: natural key ('supplier_id', 'week') unique | integrity | 0 | PASS |  |
| supplier_capacity.supplier_capacity_id: required | integrity | 0 | PASS |  |
| supplier_capacity.supplier_id: required | integrity | 0 | PASS |  |
| supplier_capacity.week: required | integrity | 0 | PASS |  |
| supplier_capacity.week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| supplier_capacity.week: valid ISO week | integrity | 0 | PASS |  |
| supplier_capacity.capacity_base_qty: required | integrity | 0 | PASS |  |
| production_capacity: primary key unique & non-null | integrity | 0 | PASS |  |
| production_capacity: natural key ('location_id', 'week') unique | integrity | 0 | PASS |  |
| production_capacity.production_capacity_id: required | integrity | 0 | PASS |  |
| production_capacity.location_id: required | integrity | 0 | PASS |  |
| production_capacity.week: required | integrity | 0 | PASS |  |
| production_capacity.week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| production_capacity.week: valid ISO week | integrity | 0 | PASS |  |
| production_capacity.capacity_base_qty: required | integrity | 0 | PASS |  |
| forecast_demand: primary key unique & non-null | integrity | 0 | PASS |  |
| forecast_demand: natural key ('sku_id', 'location_id', 'week') unique | integrity | 0 | PASS |  |
| forecast_demand.demand_id: required | integrity | 0 | PASS |  |
| forecast_demand.demand_id: pattern DEM-SKU-\d{6}-LOC-\d{3}-\d{4}W\d{2} | integrity | 0 | PASS |  |
| forecast_demand.sku_id: required | integrity | 0 | PASS |  |
| forecast_demand.location_id: required | integrity | 0 | PASS |  |
| forecast_demand.week: required | integrity | 0 | PASS |  |
| forecast_demand.week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| forecast_demand.week: valid ISO week | integrity | 0 | PASS |  |
| forecast_demand.baseline_qty: required | integrity | 0 | PASS |  |
| forecast_demand.uplift_qty: required | integrity | 0 | PASS |  |
| forecast_demand.forecast_qty: required | integrity | 0 | PASS |  |
| forecast_demand.uom: required | integrity | 0 | PASS |  |
| forecast_demand.uom: allowed values | integrity | 0 | PASS |  |
| inventory: primary key unique & non-null | integrity | 0 | PASS |  |
| inventory: natural key ('sku_id', 'location_id') unique | integrity | 0 | PASS |  |
| inventory.inventory_id: required | integrity | 0 | PASS |  |
| inventory.sku_id: required | integrity | 0 | PASS |  |
| inventory.location_id: required | integrity | 0 | PASS |  |
| inventory.snapshot_week: required | integrity | 0 | PASS |  |
| inventory.snapshot_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| inventory.snapshot_week: valid ISO week | integrity | 0 | PASS |  |
| inventory.on_hand_qty: required | integrity | 0 | PASS |  |
| inventory.allocated_qty: required | integrity | 0 | PASS |  |
| inventory.available_qty: required | integrity | 0 | PASS |  |
| inventory.in_transit_qty: required | integrity | 0 | PASS |  |
| inventory.uom: required | integrity | 0 | PASS |  |
| inventory.uom: allowed values | integrity | 0 | PASS |  |
| purchase_order: primary key unique & non-null | integrity | 0 | PASS |  |
| purchase_order.po_id: required | integrity | 0 | PASS |  |
| purchase_order.po_id: pattern PO-2026-\d{6} | integrity | 0 | PASS |  |
| purchase_order.supplier_id: required | integrity | 0 | PASS |  |
| purchase_order.sku_id: required | integrity | 0 | PASS |  |
| purchase_order.location_id: required | integrity | 0 | PASS |  |
| purchase_order.created_week: required | integrity | 0 | PASS |  |
| purchase_order.created_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| purchase_order.created_week: valid ISO week | integrity | 0 | PASS |  |
| purchase_order.order_week: required | integrity | 0 | PASS |  |
| purchase_order.order_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| purchase_order.order_week: valid ISO week | integrity | 0 | PASS |  |
| purchase_order.promised_week: required | integrity | 0 | PASS |  |
| purchase_order.promised_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| purchase_order.promised_week: valid ISO week | integrity | 0 | PASS |  |
| purchase_order.order_qty: required | integrity | 0 | PASS |  |
| purchase_order.order_uom: required | integrity | 0 | PASS |  |
| purchase_order.order_uom: allowed values | integrity | 0 | PASS |  |
| purchase_order.requested_base_qty: required | integrity | 0 | PASS |  |
| purchase_order.unit_cost: required | integrity | 0 | PASS |  |
| purchase_order.status: required | integrity | 0 | PASS |  |
| purchase_order.status: allowed values | integrity | 0 | PASS |  |
| po_event: primary key unique & non-null | integrity | 0 | PASS |  |
| po_event: natural key ('po_id', 'event_seq') unique | integrity | 0 | PASS |  |
| po_event.event_id: required | integrity | 0 | PASS |  |
| po_event.po_id: required | integrity | 0 | PASS |  |
| po_event.event_seq: required | integrity | 0 | PASS |  |
| po_event.event_type: required | integrity | 0 | PASS |  |
| po_event.event_type: allowed values | integrity | 0 | PASS |  |
| po_event.event_week: required | integrity | 0 | PASS |  |
| po_event.event_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| po_event.event_week: valid ISO week | integrity | 0 | PASS |  |
| po_event.actor: required | integrity | 0 | PASS |  |
| po_event.actor: allowed values | integrity | 0 | PASS |  |
| po_event.new_promised_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| po_event.new_promised_week: valid ISO week | integrity | 0 | PASS |  |
| inbound_shipment: primary key unique & non-null | integrity | 0 | PASS |  |
| inbound_shipment.shipment_id: required | integrity | 0 | PASS |  |
| inbound_shipment.po_id: required | integrity | 0 | PASS |  |
| inbound_shipment.carrier: required | integrity | 0 | PASS |  |
| inbound_shipment.carrier: allowed values | integrity | 0 | PASS |  |
| inbound_shipment.ship_week: required | integrity | 0 | PASS |  |
| inbound_shipment.ship_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| inbound_shipment.ship_week: valid ISO week | integrity | 0 | PASS |  |
| inbound_shipment.eta_week: required | integrity | 0 | PASS |  |
| inbound_shipment.eta_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| inbound_shipment.eta_week: valid ISO week | integrity | 0 | PASS |  |
| inbound_shipment.delay_weeks: required | integrity | 0 | PASS |  |
| inbound_shipment.qty_base: required | integrity | 0 | PASS |  |
| inbound_shipment.shipment_status: required | integrity | 0 | PASS |  |
| inbound_shipment.shipment_status: allowed values | integrity | 0 | PASS |  |
| production_plan: primary key unique & non-null | integrity | 0 | PASS |  |
| production_plan: natural key ('sku_id', 'location_id', 'week') unique | integrity | 0 | PASS |  |
| production_plan.production_plan_id: required | integrity | 0 | PASS |  |
| production_plan.sku_id: required | integrity | 0 | PASS |  |
| production_plan.location_id: required | integrity | 0 | PASS |  |
| production_plan.week: required | integrity | 0 | PASS |  |
| production_plan.week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| production_plan.week: valid ISO week | integrity | 0 | PASS |  |
| production_plan.planned_qty: required | integrity | 0 | PASS |  |
| production_plan.status: required | integrity | 0 | PASS |  |
| production_plan.status: allowed values | integrity | 0 | PASS |  |
| receipt_line: primary key unique & non-null | integrity | 0 | PASS |  |
| receipt_line.receipt_line_id: required | integrity | 0 | PASS |  |
| receipt_line.po_id: required | integrity | 0 | PASS |  |
| receipt_line.sku_id: required | integrity | 0 | PASS |  |
| receipt_line.location_id: required | integrity | 0 | PASS |  |
| receipt_line.week: required | integrity | 0 | PASS |  |
| receipt_line.week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| receipt_line.week: valid ISO week | integrity | 0 | PASS |  |
| receipt_line.qty_base: required | integrity | 0 | PASS |  |
| receipt_line.basis: required | integrity | 0 | PASS |  |
| receipt_line.basis: allowed values | integrity | 0 | PASS |  |
| projected_balance: primary key unique & non-null | integrity | 0 | PASS |  |
| projected_balance: natural key ('sku_id', 'location_id', 'week') unique | integrity | 0 | PASS |  |
| projected_balance.balance_id: required | integrity | 0 | PASS |  |
| projected_balance.sku_id: required | integrity | 0 | PASS |  |
| projected_balance.location_id: required | integrity | 0 | PASS |  |
| projected_balance.week: required | integrity | 0 | PASS |  |
| projected_balance.week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| projected_balance.week: valid ISO week | integrity | 0 | PASS |  |
| projected_balance.opening_qty: required | integrity | 0 | PASS |  |
| projected_balance.receipt_qty: required | integrity | 0 | PASS |  |
| projected_balance.production_qty: required | integrity | 0 | PASS |  |
| projected_balance.forecast_qty: required | integrity | 0 | PASS |  |
| projected_balance.dependent_demand_qty: required | integrity | 0 | PASS |  |
| projected_balance.closing_qty: required | integrity | 0 | PASS |  |
| projected_balance.safety_stock_qty: required | integrity | 0 | PASS |  |
| projected_balance.below_safety_stock: required | integrity | 0 | PASS |  |
| projected_balance.in_shortage: required | integrity | 0 | PASS |  |
| shortage: primary key unique & non-null | integrity | 0 | PASS |  |
| shortage.shortage_id: required | integrity | 0 | PASS |  |
| shortage.shortage_id: pattern SHORT-2026-\d{6} | integrity | 0 | PASS |  |
| shortage.sku_id: required | integrity | 0 | PASS |  |
| shortage.location_id: required | integrity | 0 | PASS |  |
| shortage.start_week: required | integrity | 0 | PASS |  |
| shortage.start_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| shortage.start_week: valid ISO week | integrity | 0 | PASS |  |
| shortage.end_week: required | integrity | 0 | PASS |  |
| shortage.end_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| shortage.end_week: valid ISO week | integrity | 0 | PASS |  |
| shortage.peak_week: required | integrity | 0 | PASS |  |
| shortage.peak_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| shortage.peak_week: valid ISO week | integrity | 0 | PASS |  |
| shortage.shortage_qty: required | integrity | 0 | PASS |  |
| shortage.recoverable: required | integrity | 0 | PASS |  |
| shortage.min_lead_time_weeks: required | integrity | 0 | PASS |  |
| shortage.priority_score: required | integrity | 0 | PASS |  |
| shortage.priority_rank: required | integrity | 0 | PASS |  |
| shortage.visible_in_raw_plan: required | integrity | 0 | PASS |  |
| shortage.mitigated_qty: required | integrity | 0 | PASS |  |
| shortage.residual_qty: required | integrity | 0 | PASS |  |
| shortage.fill_pct: required | integrity | 0 | PASS |  |
| shortage.status: required | integrity | 0 | PASS |  |
| shortage.status: allowed values | integrity | 0 | PASS |  |
| shortage_cause: primary key unique & non-null | integrity | 0 | PASS |  |
| shortage_cause.cause_id: required | integrity | 0 | PASS |  |
| shortage_cause.shortage_id: required | integrity | 0 | PASS |  |
| shortage_cause.cause_type: required | integrity | 0 | PASS |  |
| shortage_cause.cause_type: allowed values | integrity | 0 | PASS |  |
| shortage_cause.contributed_qty: required | integrity | 0 | PASS |  |
| shortage_cause.share_pct: required | integrity | 0 | PASS |  |
| mitigation_option: primary key unique & non-null | integrity | 0 | PASS |  |
| mitigation_option.mitigation_id: required | integrity | 0 | PASS |  |
| mitigation_option.mitigation_id: pattern MIT-SHORT-2026-\d{6}-\d{2} | integrity | 0 | PASS |  |
| mitigation_option.shortage_id: required | integrity | 0 | PASS |  |
| mitigation_option.option_type: required | integrity | 0 | PASS |  |
| mitigation_option.option_type: allowed values | integrity | 0 | PASS |  |
| mitigation_option.order_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| mitigation_option.order_week: valid ISO week | integrity | 0 | PASS |  |
| mitigation_option.arrival_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| mitigation_option.arrival_week: valid ISO week | integrity | 0 | PASS |  |
| mitigation_option.offered_qty: required | integrity | 0 | PASS |  |
| mitigation_option.cost: required | integrity | 0 | PASS |  |
| mitigation_option.fill_pct: required | integrity | 0 | PASS |  |
| mitigation_option.feasible: required | integrity | 0 | PASS |  |
| mitigation_option.dominated: required | integrity | 0 | PASS |  |
| mitigation_option.selected: required | integrity | 0 | PASS |  |
| mitigation_option.selected_qty: required | integrity | 0 | PASS |  |
| mitigation_option.selected_cost: required | integrity | 0 | PASS |  |
| capacity_ledger: primary key unique & non-null | integrity | 0 | PASS |  |
| capacity_ledger.ledger_id: required | integrity | 0 | PASS |  |
| capacity_ledger.mitigation_id: required | integrity | 0 | PASS |  |
| capacity_ledger.resource_type: required | integrity | 0 | PASS |  |
| capacity_ledger.resource_type: allowed values | integrity | 0 | PASS |  |
| capacity_ledger.resource_id: required | integrity | 0 | PASS |  |
| capacity_ledger.week: required | integrity | 0 | PASS |  |
| capacity_ledger.week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| capacity_ledger.week: valid ISO week | integrity | 0 | PASS |  |
| capacity_ledger.qty_base: required | integrity | 0 | PASS |  |
| shortage_event: primary key unique & non-null | integrity | 0 | PASS |  |
| shortage_event.event_id: required | integrity | 0 | PASS |  |
| shortage_event.shortage_id: required | integrity | 0 | PASS |  |
| shortage_event.event_seq: required | integrity | 0 | PASS |  |
| shortage_event.event_type: required | integrity | 0 | PASS |  |
| shortage_event.event_type: allowed values | integrity | 0 | PASS |  |
| shortage_event.event_week: required | integrity | 0 | PASS |  |
| shortage_event.event_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| shortage_event.event_week: valid ISO week | integrity | 0 | PASS |  |
| shortage_event.actor: required | integrity | 0 | PASS |  |
| shortage_event.actor: allowed values | integrity | 0 | PASS |  |
| mitigation_event: primary key unique & non-null | integrity | 0 | PASS |  |
| mitigation_event.event_id: required | integrity | 0 | PASS |  |
| mitigation_event.mitigation_id: required | integrity | 0 | PASS |  |
| mitigation_event.event_seq: required | integrity | 0 | PASS |  |
| mitigation_event.event_type: required | integrity | 0 | PASS |  |
| mitigation_event.event_type: allowed values | integrity | 0 | PASS |  |
| mitigation_event.event_week: required | integrity | 0 | PASS |  |
| mitigation_event.event_week: pattern \d{4}W\d{2} | integrity | 0 | PASS |  |
| mitigation_event.event_week: valid ISO week | integrity | 0 | PASS |  |
| mitigation_event.actor: required | integrity | 0 | PASS |  |
| mitigation_event.actor: allowed values | integrity | 0 | PASS |  |
| exception: primary key unique & non-null | integrity | 0 | PASS |  |
| exception.exception_id: required | integrity | 0 | PASS |  |
| exception.issue_type: required | integrity | 0 | PASS |  |
| exception.issue_type: allowed values | integrity | 0 | PASS |  |
| exception.entity: required | integrity | 0 | PASS |  |
| exception.record_id: required | integrity | 0 | PASS |  |
| exception.rule: required | integrity | 0 | PASS |  |
| exception.owner: required | integrity | 0 | PASS |  |
| exception.owner: allowed values | integrity | 0 | PASS |  |
| FK uom_conversion.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK sku_location.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK sku_location.location_id -> location.location_id | integrity | 0 | PASS |  |
| FK supplier_sku.supplier_id -> supplier.supplier_id | integrity | 0 | PASS |  |
| FK supplier_sku.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK sku_substitute.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK sku_substitute.substitute_sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK bom.parent_sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK bom.component_sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK lead_time.supplier_id -> supplier.supplier_id | integrity | 0 | PASS |  |
| FK lead_time.location_id -> location.location_id | integrity | 0 | PASS |  |
| FK supplier_capacity.supplier_id -> supplier.supplier_id | integrity | 0 | PASS |  |
| FK production_capacity.location_id -> location.location_id | integrity | 0 | PASS |  |
| FK forecast_demand.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK forecast_demand.location_id -> location.location_id | integrity | 0 | PASS |  |
| FK inventory.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK inventory.location_id -> location.location_id | integrity | 0 | PASS |  |
| FK purchase_order.supplier_id -> supplier.supplier_id | integrity | 0 | PASS |  |
| FK purchase_order.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK purchase_order.location_id -> location.location_id | integrity | 0 | PASS |  |
| FK purchase_order.substitute_for_sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK po_event.po_id -> purchase_order.po_id | integrity | 0 | PASS |  |
| FK inbound_shipment.po_id -> purchase_order.po_id | integrity | 0 | PASS |  |
| FK production_plan.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK production_plan.location_id -> location.location_id | integrity | 0 | PASS |  |
| FK receipt_line.po_id -> purchase_order.po_id | integrity | 0 | PASS |  |
| FK receipt_line.shipment_id -> inbound_shipment.shipment_id | integrity | 0 | PASS |  |
| FK receipt_line.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK receipt_line.location_id -> location.location_id | integrity | 0 | PASS |  |
| FK projected_balance.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK projected_balance.location_id -> location.location_id | integrity | 0 | PASS |  |
| FK shortage.sku_id -> sku.sku_id | integrity | 0 | PASS |  |
| FK shortage.location_id -> location.location_id | integrity | 0 | PASS |  |
| FK shortage_cause.shortage_id -> shortage.shortage_id | integrity | 0 | PASS |  |
| FK mitigation_option.shortage_id -> shortage.shortage_id | integrity | 0 | PASS |  |
| FK capacity_ledger.mitigation_id -> mitigation_option.mitigation_id | integrity | 0 | PASS |  |
| FK shortage_event.shortage_id -> shortage.shortage_id | integrity | 0 | PASS |  |
| FK mitigation_event.mitigation_id -> mitigation_option.mitigation_id | integrity | 0 | PASS |  |
| SQLite load with CHECK/UNIQUE constraints | integrity | 0 | PASS |  |
| SQLite PRAGMA foreign_key_check | integrity | 0 | PASS |  |
| forecast_qty = baseline_qty + uplift_qty | integrity | 0 | PASS |  |
| inventory: available = on_hand - allocated; 0 <= allocated <= on_hand | integrity | 0 | PASS |  |
| inventory: in_transit_qty = sum of inbound shipments to the SKU-location | integrity | 0 | PASS |  |
| forecast_demand SKU-location is in assortment | integrity | 0 | PASS |  |
| inventory SKU-location is in assortment | integrity | 0 | PASS |  |
| sku: unit_price > unit_cost > 0 | integrity | 0 | PASS |  |
| sku: effective_from <= effective_to | integrity | 0 | PASS |  |
| supplier_sku: effective_from <= effective_to | integrity | 0 | PASS |  |
| lead_time: effective_from <= effective_to | integrity | 0 | PASS |  |
| sku_substitute: approved == (review_status == APPROVED); approved_on iff approved | integrity | 0 | PASS |  |
| supplier_sku: exactly one primary supplier per SKU | integrity | 0 | PASS |  |
| supplier_sku: MOQ is a multiple of order multiple = pack_size | integrity | 0 | PASS |  |
| bom: parent is MAKE and component is BUY | integrity | 0 | PASS |  |
| lead_time: lead_time_weeks > transit_weeks >= 1 | integrity | 0 | PASS |  |
| production_plan: plant load <= production capacity | integrity | 0 | PASS |  |
| purchase_order: requested_base_qty = order_qty * uom factor | integrity | 0 | PASS |  |
| purchase_order: confirmed_base_qty <= requested_base_qty | integrity | 0 | PASS |  |
| purchase_order: confirmed qty null iff CREATED/CANCELLED | integrity | 0 | PASS |  |
| purchase_order: created_week <= order_week < promised_or_equal; created <= snapshot | integrity | 0 | PASS |  |
| po_event: event_seq is 1..n per PO | integrity | 0 | PASS |  |
| po_event: lifecycle transitions are legal | integrity | 0 | PASS |  |
| po_event: event weeks non-decreasing and <= snapshot | integrity | 0 | PASS |  |
| purchase_order.status == latest non-DELAYED event | integrity | 0 | PASS |  |
| every PO has an event history | integrity | 0 | PASS |  |
| po_event: DELAYED new_promised_week later than promised_week | integrity | 0 | PASS |  |
| inbound_shipment: eta_week = ship_week + transit_weeks + delay_weeks | integrity | 0 | PASS |  |
| inbound_shipment: only for SHIPPED POs | integrity | 0 | PASS |  |
| every SHIPPED PO has a shipment | integrity | 0 | PASS |  |
| supplier.capacity_constrained derived from capacity cuts | integrity | 0 | PASS |  |
| BR1 at most one ASN per PO (inbound not double counted) | business_rule | 5 | PASS | explained=5, unexplained=0 |
| BR6 no duplicate shipment records (po, carrier, ship week, qty) | business_rule | 5 | PASS | explained=5, unexplained=0 |
| BR2 substitute POs use an APPROVED substitute pair | business_rule | 5 | PASS | explained=5, unexplained=0 |
| BR3 confirmed supplier load <= weekly capacity | business_rule | 5 | PASS | explained=5, unexplained=0 |
| BR4 promised_week >= order_week + lead_time_weeks | business_rule | 5 | PASS | explained=5, unexplained=0 |
| BR5 PO unit of measure matches contract and pack multiple | business_rule | 5 | PASS | explained=5, unexplained=0 |
| BR7 requested qty >= MOQ and multiple of order multiple | business_rule | 5 | PASS | explained=5, unexplained=0 |
| PAB: closing = opening + receipts + production - forecast - dependent | integrity | 0 | PASS |  |
| PAB: opening[w+1] = closing[w] (week-by-week roll) | integrity | 0 | PASS |  |
| PAB: opening(W01) = inventory.available_qty | integrity | 0 | PASS |  |
| PAB: forecast_qty reconciles to forecast_demand | integrity | 0 | PASS |  |
| PAB: production_qty reconciles to production_plan | integrity | 0 | PASS |  |
| PAB: receipt_qty reconciles to receipt_line | integrity | 0 | PASS |  |
| PAB: dependent_demand_qty = sum(parent planned_qty * qty_per) | integrity | 0 | PASS |  |
| receipt_line: never credits a CANCELLED PO | integrity | 0 | PASS |  |
| shortage_qty = -min(closing) over the run | integrity | 0 | PASS |  |
| shortage run boundaries match negative-balance weeks | integrity | 0 | PASS |  |
| every negative-balance week belongs to a shortage | integrity | 0 | PASS |  |
| every shortage has explainable causes summing to shortage_qty | integrity | 0 | PASS |  |
| cause contributions are positive | integrity | 0 | PASS |  |
| mitigated_qty + residual_qty consistent with selected options | integrity | 0 | PASS |  |
| residual qty is explicitly accepted (ACCEPT_SHORTFALL selected) | integrity | 0 | PASS |  |
| only feasible options are selected | integrity | 0 | PASS |  |
| policy: selected substitutes are APPROVED | integrity | 0 | PASS |  |
| policy: no PO/expedite placed with an ON_HOLD supplier | integrity | 0 | PASS |  |
| policy: PO/expedite arrival honours (expedited) lead time | integrity | 0 | PASS |  |
| policy: mitigation POs respect MOQ and order multiple | integrity | 0 | PASS |  |
| mitigations never exceed spare supplier capacity | integrity | 0 | PASS |  |
| mitigations never exceed spare plant capacity | integrity | 0 | PASS |  |
| donor/substitute/component stock stays >= safety stock after mitigation | integrity | 0 | PASS |  |
| shortage_event: lifecycle starts with DETECTED | integrity | 0 | PASS |  |
| mitigation_event: lifecycle starts with PROPOSED | integrity | 0 | PASS |  |
| shortage.status == final shortage event | integrity | 0 | PASS |  |
| approval: accepted shortfalls and spend >= threshold approved by OPERATIONS_MANAGER | integrity | 0 | PASS |  |
| roles: TRANSFER/EXPEDITE proposed by LOGISTICS_ANALYST, others by PLANNER | integrity | 0 | PASS |  |
| roles: shortage closed by OPERATIONS_MANAGER iff a selected option needed approval | integrity | 0 | PASS |  |
| all five actors from the brief appear in the event history | integrity | 0 | PASS |  |
| ground truth: every label traces to an existing source record | integrity | 0 | PASS |  |
| boundary: zero-balance rows produce no shortage | integrity | 0 | PASS |  |
| boundary: receipt promised in W52 is counted in W52 | integrity | 0 | PASS |  |
| boundary: MOQ POs requested exactly MOQ | integrity | 0 | PASS |  |
| ground truth covers all 5 required edge-case types | integrity | 0 | PASS |  |

## Row counts

| Table | Rows |
|---|---|
| bom | 52 |
| capacity_ledger | 225 |
| exception | 25 |
| forecast_demand | 13,312 |
| inbound_shipment | 61 |
| inventory | 290 |
| lead_time | 100 |
| location | 5 |
| mitigation_event | 2,366 |
| mitigation_option | 1,183 |
| po_event | 737 |
| production_capacity | 52 |
| production_plan | 820 |
| projected_balance | 15,080 |
| purchase_order | 310 |
| receipt_line | 315 |
| shortage | 310 |
| shortage_cause | 377 |
| shortage_event | 911 |
| sku | 100 |
| sku_location | 290 |
| sku_substitute | 17 |
| supplier | 20 |
| supplier_capacity | 1,040 |
| supplier_sku | 157 |
| uom_conversion | 200 |
