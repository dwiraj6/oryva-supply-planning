# Evaluation report (starter)

## 1. Anomaly detection vs ground truth

The detector reads only input tables. Scores compare its exceptions with `ground_truth.csv`.

| Issue type | Labelled | Flagged | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|---|
| INBOUND_DOUBLE_COUNT | 5 | 5 | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| SUBSTITUTE_NOT_APPROVED | 5 | 5 | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| SUPPLIER_CAPACITY_EXCEEDED | 5 | 5 | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| SHORTAGE_WITHOUT_LEAD_TIME | 5 | 5 | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UOM_MISMATCH | 5 | 5 | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| **micro average** |  |  | 25 | 0 | 0 | 1.000 | 1.000 | 1.000 |

Boundary (valid edge) records: 12; wrongly flagged: **0**.

## 2. Impact of anomalies on the plan

Shortages that the raw (uncleaned) plan would have hidden: **4**

Raw plan = anomalies left in; cleaned plan = detector corrections applied. Hidden weeks: shortage weeks the raw plan would miss. False weeks: shortage weeks the raw plan would wrongly report.

| Issue type | Records | Raw balance error | Hidden shortage weeks | False shortage weeks | Max abs balance error (EA) |
|---|---|---|---|---|---|
| INBOUND_DOUBLE_COUNT | 5 | overstated | 12 | 0 | 3,888 |
| SHORTAGE_WITHOUT_LEAD_TIME | 5 | overstated | 1 | 0 | 2,304 |
| SUBSTITUTE_NOT_APPROVED | 5 | overstated/understated | 3 | 5 | 72 |
| SUPPLIER_CAPACITY_EXCEEDED | 5 | overstated | 0 | 0 | 9,698 |
| UOM_MISMATCH | 5 | understated | 0 | 111 | 6,776 |

## 3. Planning KPIs

| KPI | Value |
|---|---|
| sku_locations | 290 |
| shortages | 310 |
| sku_locations_with_shortage | 203 |
| shortage_units | 61,400 |
| shortage_units_pct_of_demand | 6.37 |
| recoverable_pct | 91.29 |
| fill_rate_pct | 90.1 |
| mitigation_cost | 50,286.02 |
| accepted_lost_margin | 50,220.07 |
| options_generated | 1,183 |
| options_feasible | 777 |
| options_dominated | 391 |
| below_safety_stock_weeks_pct | 14.75 |
| status_counts | COVERED_BY_PRIOR_MITIGATION: 19, MITIGATED: 208, PARTIALLY_MITIGATED: 6, UNMITIGATED: 77 |
| selected_by_type | EXPEDITE: 12, PLACE_PO: 191, PRODUCE: 3, SUBSTITUTE: 1, TRANSFER: 12 |
| selected_units_by_type | EXPEDITE: 4,142, PLACE_PO: 46,292, PRODUCE: 45, SUBSTITUTE: 79, TRANSFER: 1,111 |
| cause_units | BASE_SUPPLY_GAP: 11,977, CANCELLED_PO: 4,458, DEMAND_SPIKE: 31,075, DEPENDENT_DEMAND: 9,817, SUPPLIER_CAPACITY_CUT: 2,967, SUPPLIER_DELAY: 1,061, TRANSPORT_DELAY: 45 |
| rejection_reasons | COMPONENT_SHORTAGE: 68, INSUFFICIENT_SUPPLIER_CAPACITY: 6, LEAD_TIME_EXCEEDS_NEED_DATE: 76, NO_SUBSTITUTE_SURPLUS: 14, NO_SURPLUS_AT_OTHER_LOCATIONS: 184, SUBSTITUTE_NOT_APPROVED: 19, SUPPLIER_ON_HOLD: 38, TRANSFER_LEAD_TIME_EXCEEDS_NEED_DATE: 1 |

## 4. Top 20 shortages by priority

| Rank | Shortage | SKU (ABC) | Location | Weeks | Qty | Recoverable | Main causes | Selected mitigation | Fill % |
|---|---|---|---|---|---|---|---|---|---|
| 1 | SHORT-2026-000010 | SKU-000099 (C) | LOC-001 | 2026W03-2026W04 | 1,148 | no | DEPENDENT_DEMAND 1,148 (100%) | ACCEPT_SHORTFALL x1,148 | 0.0 |
| 2 | SHORT-2026-000044 | SKU-000023 (B) | LOC-005 | 2026W09-2026W52 | 1,305 | yes | CANCELLED_PO 1,032 (79%); DEMAND_SPIKE 256 (20%); BASE_SUPPLY_GAP 17 (1%) | PLACE_PO SUP-0009 x1,305 | 100.0 |
| 3 | SHORT-2026-000028 | SKU-000091 (A) | LOC-004 | 2026W06-2026W52 | 2,595 | no | CANCELLED_PO 2,250 (87%); DEMAND_SPIKE 345 (13%) | EXPEDITE SUP-0009 x1,656; ACCEPT_SHORTFALL x939 | 63.8 |
| 4 | SHORT-2026-000002 | SKU-000023 (B) | LOC-003 | 2026W02-2026W02 | 57 | no | DEMAND_SPIKE 57 (100%) | TRANSFER LOC-004 x57 | 100.0 |
| 5 | SHORT-2026-000043 | SKU-000082 (B) | LOC-003 | 2026W08-2026W10 | 136 | yes | SUPPLIER_DELAY 136 (100%) | PLACE_PO SUP-0018 x136 | 100.0 |
| 6 | SHORT-2026-000023 | SKU-000057 (B) | LOC-005 | 2026W06-2026W06 | 53 | yes | SUPPLIER_DELAY 53 (100%) | TRANSFER LOC-003 x17; PLACE_PO SUP-0001 x36 | 100.0 |
| 7 | SHORT-2026-000029 | SKU-000098 (B) | LOC-004 | 2026W06-2026W07 | 412 | no | SUPPLIER_DELAY 412 (100%) | EXPEDITE SUP-0018 x412 | 100.0 |
| 8 | SHORT-2026-000008 | SKU-000086 (B) | LOC-003 | 2026W03-2026W04 | 76 | no | DEMAND_SPIKE 76 (100%) | ACCEPT_SHORTFALL x76 | 0.0 |
| 9 | SHORT-2026-000018 | SKU-000050 (B) | LOC-002 | 2026W05-2026W52 | 1,009 | yes | BASE_SUPPLY_GAP 1,009 (100%) | PLACE_PO SUP-0016 x1,009 | 100.0 |
| 10 | SHORT-2026-000006 | SKU-000029 (B) | LOC-001 | 2026W03-2026W03 | 210 | no | DEPENDENT_DEMAND 210 (100%) | ACCEPT_SHORTFALL x210 | 0.0 |
| 11 | SHORT-2026-000040 | SKU-000050 (B) | LOC-003 | 2026W08-2026W52 | 1,547 | yes | BASE_SUPPLY_GAP 1,464 (95%); DEMAND_SPIKE 83 (5%) | PLACE_PO SUP-0016 x1,547 | 100.0 |
| 12 | SHORT-2026-000012 | SKU-000027 (A) | LOC-003 | 2026W04-2026W05 | 174 | no | DEMAND_SPIKE 174 (100%) | TRANSFER LOC-004 x174 | 100.0 |
| 13 | SHORT-2026-000016 | SKU-000084 (C) | LOC-001 | 2026W04-2026W07 | 1,636 | no | DEPENDENT_DEMAND 1,636 (100%) | EXPEDITE SUP-0010 x1,636 | 100.0 |
| 14 | SHORT-2026-000027 | SKU-000091 (A) | LOC-002 | 2026W06-2026W28 | 607 | no | BASE_SUPPLY_GAP 607 (100%) | ACCEPT_SHORTFALL x607 | 0.0 |
| 15 | SHORT-2026-000017 | SKU-000032 (A) | LOC-003 | 2026W05-2026W07 | 278 | no | DEMAND_SPIKE 278 (100%) | TRANSFER LOC-005 x278 | 100.0 |
| 16 | SHORT-2026-000030 | SKU-000005 (B) | LOC-004 | 2026W07-2026W08 | 132 | yes | DEMAND_SPIKE 132 (100%) | PLACE_PO SUP-0001 x132 | 100.0 |
| 17 | SHORT-2026-000015 | SKU-000080 (B) | LOC-004 | 2026W04-2026W07 | 95 | no | DEMAND_SPIKE 95 (100%) | SUBSTITUTE SKU-000060 x79; EXPEDITE SUP-0007 x16 | 100.0 |
| 18 | SHORT-2026-000019 | SKU-000057 (B) | LOC-004 | 2026W05-2026W05 | 12 | yes | SUPPLIER_DELAY 12 (100%) | PLACE_PO SUP-0001 x12 | 100.0 |
| 19 | SHORT-2026-000034 | SKU-000067 (B) | LOC-002 | 2026W07-2026W08 | 31 | yes | SUPPLIER_DELAY 31 (100%) | PLACE_PO SUP-0009 x31 | 100.0 |
| 20 | SHORT-2026-000009 | SKU-000092 (B) | LOC-002 | 2026W03-2026W05 | 41 | no | DEMAND_SPIKE 41 (100%) | TRANSFER LOC-004 x34; ACCEPT_SHORTFALL x7 | 82.9 |

## 5. Generated data profile (realism)

| ABC | SKU-locations | Mean weekly demand | Median CV | Zero-demand week share |
|---|---|---|---|---|
| A | 63 | 129.643 | 0.651 | 0.0 |
| B | 99 | 47.394 | 0.651 | 0.0 |
| C | 94 | 8.882 | 1.085 | 0.43 |

| Measure | Value |
|---|---|
| spike_week_share | 0.0337 |
| lead_time_weeks | {'min': 2, 'median': 6.0, 'p90': 10.0, 'max': 14} |
| po_status | {'CONFIRMED': 244, 'SHIPPED': 56, 'CREATED': 6, 'CANCELLED': 4} |
| po_uom | {'CASE': 215, 'EA': 95} |
| capacity_cut_pos | 3 |
| constrained_suppliers | 1 |
| suppliers_on_hold | 1 |
| transport_delayed_shipments_pct | 14.75 |
| supplier_delayed_pos | 59 |
| substitute_pairs | {'APPROVED': 9, 'REJECTED': 4, 'PENDING': 4} |
| substitute_pos | 9 |
| assortment_locations_per_sku | 2.9 |
