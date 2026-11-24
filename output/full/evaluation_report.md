# Evaluation report (full)

## 1. Anomaly detection vs ground truth

The detector reads only input tables. Scores compare its exceptions with `ground_truth.csv`.

| Issue type | Labelled | Flagged | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|---|
| INBOUND_DOUBLE_COUNT | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| SUBSTITUTE_NOT_APPROVED | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| SUPPLIER_CAPACITY_EXCEEDED | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| SHORTAGE_WITHOUT_LEAD_TIME | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UOM_MISMATCH | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| **micro average** |  |  | 200 | 0 | 0 | 1.000 | 1.000 | 1.000 |

Boundary (valid edge) records: 40; wrongly flagged: **0**.

## 2. Impact of anomalies on the plan

Shortages that the raw (uncleaned) plan would have hidden: **38**

Raw plan = anomalies left in; cleaned plan = detector corrections applied. Hidden weeks: shortage weeks the raw plan would miss. False weeks: shortage weeks the raw plan would wrongly report.

| Issue type | Records | Raw balance error | Hidden shortage weeks | False shortage weeks | Max abs balance error (EA) |
|---|---|---|---|---|---|
| INBOUND_DOUBLE_COUNT | 40 | overstated | 104 | 0 | 43,032 |
| SHORTAGE_WITHOUT_LEAD_TIME | 40 | overstated | 22 | 0 | 6,240 |
| SUBSTITUTE_NOT_APPROVED | 40 | overstated/understated | 76 | 27 | 384 |
| SUPPLIER_CAPACITY_EXCEEDED | 40 | overstated | 0 | 0 | 80,786 |
| UOM_MISMATCH | 40 | understated | 0 | 1164 | 11,625 |

## 3. Planning KPIs

| KPI | Value |
|---|---|
| sku_locations | 11,735 |
| shortages | 10,155 |
| sku_locations_with_shortage | 7,567 |
| shortage_units | 5,394,568 |
| shortage_units_pct_of_demand | 8.76 |
| recoverable_pct | 91.31 |
| fill_rate_pct | 90.11 |
| mitigation_cost | 3,975,848.46 |
| accepted_lost_margin | 4,016,364.69 |
| options_generated | 40,281 |
| options_feasible | 31,819 |
| options_dominated | 18,828 |
| below_safety_stock_weeks_pct | 14.54 |
| status_counts | COVERED_BY_PRIOR_MITIGATION: 613, MITIGATED: 7,985, PARTIALLY_MITIGATED: 178, UNMITIGATED: 1,379 |
| selected_by_type | EXPEDITE: 330, PLACE_PO: 7,182, PRODUCE: 90, SUBSTITUTE: 13, TRANSFER: 757 |
| selected_units_by_type | EXPEDITE: 553,605, PLACE_PO: 4,023,773, PRODUCE: 1,264, SUBSTITUTE: 351, TRANSFER: 123,292 |
| cause_units | BASE_SUPPLY_GAP: 1,308,603, CANCELLED_PO: 745,803, DEMAND_SPIKE: 1,971,078, DEPENDENT_DEMAND: 914,401, SUPPLIER_CAPACITY_CUT: 334,023, SUPPLIER_DELAY: 107,591, TRANSPORT_DELAY: 13,069 |
| rejection_reasons | COMPONENT_SHORTAGE: 1,297, INSUFFICIENT_SUPPLIER_CAPACITY: 57, LEAD_TIME_EXCEEDS_NEED_DATE: 2,274, NO_SUBSTITUTE_SURPLUS: 176, NO_SURPLUS_AT_OTHER_LOCATIONS: 3,900, PLANT_CAPACITY_FULL: 5, PRODUCTION_LEAD_TIME_EXCEEDS_NEED_DATE: 23, SUBSTITUTE_NOT_APPROVED: 149, SUPPLIER_ON_HOLD: 542, TRANSFER_LEAD_TIME_EXCEEDS_NEED_DATE: 39 |

## 4. Top 20 shortages by priority

| Rank | Shortage | SKU (ABC) | Location | Weeks | Qty | Recoverable | Main causes | Selected mitigation | Fill % |
|---|---|---|---|---|---|---|---|---|---|
| 1 | SHORT-2026-000658 | SKU-001042 (A) | LOC-047 | 2026W05-2026W52 | 14,050 | no | CANCELLED_PO 13,098 (93%); DEMAND_SPIKE 952 (7%) | TRANSFER LOC-020 x723; TRANSFER LOC-001 x194; EXPEDITE SUP-0201 x13,133 | 100.0 |
| 2 | SHORT-2026-001319 | SKU-001910 (A) | LOC-037 | 2026W07-2026W52 | 10,012 | yes | CANCELLED_PO 9,984 (100%); BASE_SUPPLY_GAP 28 (0%) | TRANSFER LOC-001 x198; PLACE_PO SUP-0105 x9,814 | 100.0 |
| 3 | SHORT-2026-000619 | SKU-000761 (A) | LOC-047 | 2026W05-2026W52 | 10,241 | no | BASE_SUPPLY_GAP 9,522 (93%); DEMAND_SPIKE 719 (7%) | TRANSFER LOC-046 x1,000; EXPEDITE SUP-0233 x9,241 | 100.0 |
| 4 | SHORT-2026-000509 | SKU-002557 (A) | LOC-037 | 2026W04-2026W52 | 9,443 | no | CANCELLED_PO 8,923 (94%); DEMAND_SPIKE 520 (6%) | ACCEPT_SHORTFALL x9,443 | 0.0 |
| 5 | SHORT-2026-000473 | SKU-002022 (A) | LOC-033 | 2026W04-2026W52 | 6,623 | no | CANCELLED_PO 6,623 (100%) | TRANSFER LOC-042 x73; TRANSFER LOC-012 x29; ACCEPT_SHORTFALL x6,521 | 1.5 |
| 6 | SHORT-2026-000339 | SKU-000270 (A) | LOC-038 | 2026W04-2026W52 | 7,649 | no | CANCELLED_PO 6,999 (92%); DEMAND_SPIKE 650 (8%) | TRANSFER LOC-046 x1,057; TRANSFER LOC-004 x35; ACCEPT_SHORTFALL x6,557 | 14.3 |
| 7 | SHORT-2026-000130 | SKU-002366 (B) | LOC-011 | 2026W02-2026W52 | 4,356 | no | DEPENDENT_DEMAND 4,356 (100%) | ACCEPT_SHORTFALL x4,356 | 0.0 |
| 8 | SHORT-2026-000709 | SKU-001549 (A) | LOC-023 | 2026W05-2026W52 | 10,423 | no | BASE_SUPPLY_GAP 9,958 (96%); DEMAND_SPIKE 465 (4%) | TRANSFER LOC-018 x322; TRANSFER LOC-041 x15; ACCEPT_SHORTFALL x10,086 | 3.2 |
| 9 | SHORT-2026-000106 | SKU-001552 (A) | LOC-041 | 2026W02-2026W52 | 3,623 | no | DEPENDENT_DEMAND 3,623 (100%) | TRANSFER LOC-047 x1,001; TRANSFER LOC-010 x268; ACCEPT_SHORTFALL x2,354 | 35.0 |
| 10 | SHORT-2026-001511 | SKU-001552 (A) | LOC-027 | 2026W08-2026W52 | 9,971 | yes | BASE_SUPPLY_GAP 8,289 (83%); DEMAND_SPIKE 1,682 (17%) | PLACE_PO SUP-0205 x9,971 | 100.0 |
| 11 | SHORT-2026-000868 | SKU-000270 (A) | LOC-007 | 2026W06-2026W52 | 8,296 | yes | BASE_SUPPLY_GAP 8,051 (97%); DEMAND_SPIKE 245 (3%) | PLACE_PO SUP-0441 x8,296 | 100.0 |
| 12 | SHORT-2026-001259 | SKU-001204 (A) | LOC-042 | 2026W07-2026W52 | 10,469 | yes | CANCELLED_PO 9,888 (94%); BASE_SUPPLY_GAP 581 (6%) | PLACE_PO SUP-0449 x10,469 | 100.0 |
| 13 | SHORT-2026-000261 | SKU-001892 (B) | LOC-001 | 2026W03-2026W52 | 19,746 | no | DEPENDENT_DEMAND 19,746 (100%) | TRANSFER LOC-017 x22; ACCEPT_SHORTFALL x19,724 | 0.1 |
| 14 | SHORT-2026-000468 | SKU-001994 (A) | LOC-030 | 2026W04-2026W52 | 13,516 | no | CANCELLED_PO 11,277 (83%); DEMAND_SPIKE 2,239 (17%) | EXPEDITE SUP-0267 x13,516 | 100.0 |
| 15 | SHORT-2026-001332 | SKU-001982 (A) | LOC-034 | 2026W07-2026W52 | 6,697 | yes | BASE_SUPPLY_GAP 5,893 (88%); DEMAND_SPIKE 804 (12%) | PLACE_PO SUP-0269 x6,697 | 100.0 |
| 16 | SHORT-2026-000419 | SKU-001421 (C) | LOC-001 | 2026W04-2026W52 | 35,396 | no | DEPENDENT_DEMAND 35,396 (100%) | ACCEPT_SHORTFALL x35,396 | 0.0 |
| 17 | SHORT-2026-000836 | SKU-002941 (B) | LOC-031 | 2026W05-2026W52 | 13,100 | no | DEPENDENT_DEMAND 13,100 (100%) | TRANSFER LOC-011 x1,000; TRANSFER LOC-039 x345; EXPEDITE SUP-0011 x11,755 | 100.0 |
| 18 | SHORT-2026-000042 | SKU-000035 (A) | LOC-039 | 2026W02-2026W52 | 3,995 | no | CANCELLED_PO 3,893 (97%); DEMAND_SPIKE 102 (3%) | TRANSFER LOC-011 x20; TRANSFER LOC-033 x7; ACCEPT_SHORTFALL x3,968 | 0.7 |
| 19 | SHORT-2026-000963 | SKU-001395 (A) | LOC-042 | 2026W06-2026W10 | 4,433 | yes | DEMAND_SPIKE 3,857 (87%); SUPPLIER_DELAY 576 (13%) | PLACE_PO SUP-0084 x4,433 | 100.0 |
| 20 | SHORT-2026-000781 | SKU-002366 (B) | LOC-029 | 2026W05-2026W52 | 2,681 | yes | CANCELLED_PO 2,370 (88%); BASE_SUPPLY_GAP 193 (7%); DEMAND_SPIKE 118 (4%) | PLACE_PO SUP-0175 x2,681 | 100.0 |

## 5. Generated data profile (realism)

| ABC | SKU-locations | Mean weekly demand | Median CV | Zero-demand week share |
|---|---|---|---|---|
| A | 3528 | 192.283 | 0.631 | 0.0 |
| B | 3263 | 62.561 | 0.646 | 0.001 |
| C | 2847 | 12.256 | 1.006 | 0.417 |

| Measure | Value |
|---|---|
| spike_week_share | 0.0297 |
| lead_time_weeks | {'min': 2, 'median': 6.0, 'p90': 9.0, 'max': 16} |
| po_status | {'CONFIRMED': 6554, 'SHIPPED': 3157, 'CANCELLED': 200, 'CREATED': 169} |
| po_uom | {'CASE': 6990, 'EA': 3090} |
| capacity_cut_pos | 338 |
| constrained_suppliers | 56 |
| suppliers_on_hold | 20 |
| transport_delayed_shipments_pct | 14.08 |
| supplier_delayed_pos | 1833 |
| substitute_pairs | {'APPROVED': 325, 'REJECTED': 78, 'PENDING': 68} |
| substitute_pos | 190 |
| assortment_locations_per_sku | 3.91 |
