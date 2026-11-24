# Business rules and formulas

Every rule below is implemented in code (file and function given) and checked by the validator
(`output/<scale>/validation_summary.md`). Quantities are in base unit **EA**. Weeks are ISO weeks;
the plan runs **as of the start of 2026W01** over a **52-week horizon (2026W01–2026W52)**.

## 1. Generation order (dependency order)

| Step | Tables | Code |
|---|---|---|
| 1 Masters | `sku`, `location`, `supplier` | `generate._skus/_locations/_suppliers` |
| 2 Bridges & reference | `sku_location`, `bom`, `supplier_sku`, `sku_substitute`, `lead_time`, `uom_conversion` | `generate._assortment/_bom/...` |
| 3 Demand | `forecast_demand` (weekly, per SKU-location) | `generate._demand` |
| 4 Production | `production_plan`, `production_capacity` | `generate._production` |
| 5 Inventory | `inventory` (on-hand snapshot at 2026W01) | `generate._inventory` |
| 6 Supply | `purchase_order` → capacity confirmation → `inbound_shipment` → `po_event` | `generate._purchase_orders/_capacity/_shipments/_events` |
| 7 Boundary cases | valid records at limits, labelled | `generate._boundaries` |
| 8 Anomalies | the five required edge cases, labelled | `generate._inject` |

Children always reference existing parents. Every random draw comes from a seeded stream
(`oryva/rng.py`); master records use a per-entity stream, so `SKU-000042` is identical in the
starter and full datasets.

## 2. Data generation rules (realism)

| Rule | Description |
|---|---|
| G1 ABC mix | 20% A, 30% B, 50% C SKUs. Weekly demand level is lognormal around 120 / 40 / 8 EA per location (A/B/C). |
| G2 Demand shape | A/B demand is negative binomial (dispersion 4). C demand is intermittent: Bernoulli occurrence (35–80%) × Poisson size. Category seasonality: sine wave, amplitude 0–40%. |
| G3 Demand spikes | About 3% of SKU-location-weeks get an `uplift_qty` of 1–4× the mean (promotions or events). `forecast_qty = baseline_qty + uplift_qty`. |
| G4 Assortment | A SKUs are stocked at 4–10 locations, B at 2–6, C at 1–3. MAKE SKUs are stocked only at plants (every 10th location). BOM components are stocked at the parent's plant (`stocking_role = COMPONENT`). |
| G5 Inventory | On-hand = mean weekly requirement × cover weeks (A 3–8, B 4–12, C 20–60, MAKE 1–3, components 2–6). Allocated stock is 0–8% of on-hand. |
| G6 Baseline POs | POs are sized as a planner would have placed them *before* the latest uplifts. Each row's annual gap is (baseline + dependent requirement + safety stock − available), multiplied by a sizing accuracy of 0.85–1.15. Each PO is timed for the week the balance would drop below safety stock. Exactly `n_pos` POs are apportioned: largest gaps first, then by need. |
| G7 Lead times | `lead_time_weeks` = supplier base lead time (lognormal around 4) + region distance. `transit_weeks` is 1–3 and always below the lead time. `promised_week = order_week + lead_time_weeks`. |
| G8 PO lifecycle | 2% of POs are cancelled. 5% of future POs are still unconfirmed (`CREATED`). A PO is shipped when `promised − transit ≤ 2026W01`. Unshipped POs get a supplier delay (1–4 weeks) with probability `(1 − reliability) × 1.5`. Shipments get a carrier delay (1–3 weeks) with probability `1 − carrier reliability`. |
| G9 Supplier capacity | Weekly capacity is set against promised-week load. Normal suppliers get 1.05–1.35× peak load, never below load. 12% of suppliers are latently tight at 0.55–0.85× peak load. Where load exceeds capacity, confirmed qty is cut pro rata and rounded down to the order multiple. `supplier.capacity_constrained` is **derived**: true when a cut happened. |
| G10 Substitutes | 20% of BUY SKUs have a same-category substitute stocked at a shared location. 70% of pairs are APPROVED, the rest PENDING or REJECTED. About 1.5% of POs legitimately buy an approved substitute. |
| G11 Production | Weekly planned qty = 4-week rolling forecast × 0.92–1.05. Plant capacity is never below the plan. FIRM for weeks 1–4, PLANNED afterwards. |

## 3. Planning rules (engine)

| Rule | Formula / behaviour | Code |
|---|---|---|
| R1 Units | All quantities are converted to EA: `base_qty = order_qty × uom_conversion.factor` | `engine`, `generate` |
| R2 Opening | `opening(2026W01) = on_hand_qty − allocated_qty`. `inventory.in_transit_qty` (inbound stock already shipped) is derived from shipments and reported only. The plan credits inbound once, through the shipment receipt lines, so it is never double counted. | `engine.opening` |
| R3 Balance | `closing[w] = opening[w] + receipts[w] + production[w] − forecast[w] − dependent[w]` | `engine.balance` |
| R4 Roll | `opening[w+1] = closing[w]` | `engine.balance` |
| R5 Receipts | Shipped PO → `eta_week` of each shipment. Unshipped PO → latest `DELAYED.new_promised_week`, otherwise `promised_week`. Qty = confirmed (or requested when unconfirmed). Cancelled → 0. | `engine.receipt_lines` |
| R6 Horizon | Receipts dated before W01 are overdue and land in W01. Receipts after W52 are outside the horizon. | `engine.receipt_lines` |
| R7 Substitute PO | An approved substitute PO credits the SKU it substitutes for (× `conversion_ratio`). | `engine.receipt_lines` |
| R8 Dependent demand | `dependent[component, plant, w] = Σ parent planned_qty × bom.qty_per` | `engine.dependent_matrix` |
| R9 Safety stock | `ceil(sku.safety_stock_weeks × mean weekly (forecast + dependent))` | `engine.safety_stock` |
| R10 Shortage | A maximal run of consecutive weeks with `closing < 0`. `shortage_qty = −min(closing)` over the run. `peak_week` is the argmin. | `plan.run` |
| R11 Recoverable | `start_week − 2026W01 ≥` the shortest active-supplier lead time (production lead time for MAKE). Otherwise the shortage sits inside the lead-time fence. | `plan.run` |
| R12 Priority | `score = shortage_qty × unit_margin × ABC weight (A=3, B=2, C=1) × 0.5^((start_week − 1)/4)`, normalised to 0–100 and ranked. | `plan.run` |

### Cause attribution (every shortage is explained)

Causes are removed **cumulatively in a fixed order**, and the projected balance is recomputed after each removal:

1. `DEMAND_SPIKE`: forecast uplift removed
2. `DEPENDENT_DEMAND`: BOM-driven demand removed
3. `SUPPLIER_CAPACITY_CUT`: confirmed qty restored to requested qty
4. `CANCELLED_PO`: cancelled POs restored
5. `SUPPLIER_DELAY`: supplier-advised delays removed
6. `TRANSPORT_DELAY`: carrier delays removed

Each cause's contribution is the drop in the shortage's peak deficit within its window. Whatever deficit remains is `BASE_SUPPLY_GAP`: committed supply is too small even with no disruptions.

Every removal can only raise the balance, so contributions are non-negative. Because the steps telescope, the contributions **sum exactly to `shortage_qty`**. Each cause row lists the evidence records behind it: demand ids, PO ids, shipment ids, BOM ids or the inventory id.

## 4. Data-quality quarantine (detector → cleaned plan)

The detector (`oryva/detect.py`) reads input tables only. The **official plan is the cleaned plan**: each flagged record's suggested correction is applied. A raw plan with the anomalies left in is computed alongside, which shows how much each anomaly would distort the plan.

| Rule | Detection | Correction in the cleaned plan |
|---|---|---|
| D1 | More than one shipment per PO, or shipped qty > confirmed qty | Exclude the duplicate shipment |
| D2 | `substitute_for_sku_id` set, but the pair is not APPROVED | Credit the PO to its own SKU, not the substituted one |
| D3 | Cumulative confirmed qty for the supplier-week (in `po_id` order) exceeds capacity | Cap the PO at the remaining capacity |
| D4 | `promised_week − order_week < lead_time_weeks` | Move the receipt to `order_week + lead_time_weeks` |
| D5 | `order_uom` differs from the contracted UoM, or an EA qty is not a pack multiple | Re-convert the qty using the contracted UoM |

## 5. Actors and responsibilities

The five actors from the brief appear in the event history. A validator check confirms that each one is used.

| Actor | Where it appears | Responsibility |
|---|---|---|
| SUPPLIER | `po_event.actor` (CONFIRMED, CANCELLED, supplier DELAYED) | Confirms POs, possibly below the requested qty when capacity is short; advises delays |
| PLANNER | `po_event` (CREATED), `shortage_event` (DETECTED, MITIGATION_PROPOSED), `mitigation_event` (PROPOSED for PLACE_PO / SUBSTITUTE / PRODUCE / ACCEPT), `exception.owner` | Creates orders, runs the plan, proposes sourcing mitigations, owns master-data and PO exceptions |
| CARRIER (carrier / warehouse operator) | `po_event` (SHIPPED, transport DELAYED), `inbound_shipment` (ASN, ETA) | Ships goods and reports in-transit status and delays |
| LOGISTICS_ANALYST | `mitigation_event` (PROPOSED, and SELECTED below the threshold, for TRANSFER and EXPEDITE), `exception.owner` for `INBOUND_DOUBLE_COUNT` | Owns stock movements, expedites and ASN data quality |
| OPERATIONS_MANAGER | `mitigation_event` SELECTED when the option is ACCEPT_SHORTFALL or `selected_cost >= 5,000` (`ops_approval_threshold`); `shortage_event` closing event for those shortages | Approves high spend and every accepted lost sale |

## 6. Mitigation policy

Shortages are processed in **priority order**. All shortages draw on **shared ledgers**, so two shortages can never consume the same capacity or stock.

| Option | Feasible when | Cost model |
|---|---|---|
| TRANSFER | Need week ≥ 2 (1-week transfer lead time). The donor keeps its own safety stock in every remaining week: `min(future closing) − safety stock − already reserved`. Up to two best donors are listed. | 200 + 4% of unit cost × qty |
| SUBSTITUTE | The pair is **APPROVED**. The substitute has surplus above its safety stock at the same location. Unapproved pairs are listed as infeasible, with the reason. | 100 + qty × max(0, substitute cost − SKU cost) |
| PRODUCE | MAKE SKU. Spare plant capacity in week `need − 1`. Every BOM component has surplus. | 300 + 8% of unit cost × qty |
| PLACE_PO | Supplier ACTIVE and `need_week − lead_time ≥ 2026W01`. Qty ≥ MOQ and a multiple of the order multiple, within spare supplier capacity in the need week. | 150 + qty × (supplier cost − primary cost) |
| EXPEDITE | Only when a normal PO would arrive too late. Lead time is halved (rounded up). Same capacity and MOQ rules apply. | 500 + qty × (premium + 25% of unit cost) |
| ACCEPT_SHORTFALL | Always | Lost margin = qty × (price − cost) |

- **Trade-offs:** each option shows cost, fill %, arrival week and a `dominated` flag. An option is dominated when another feasible option has ≥ fill and ≤ cost, and is strictly better on one of them.
- **Selection:** feasible options are taken greedily by **cost per unit**, rechecking the live ledgers each time, until the need is covered. Any remainder is explicitly accepted as `ACCEPT_SHORTFALL`.
- **Earlier mitigations count:** supply added for an earlier-processed shortage at the same SKU-location reduces the need of later runs. A shortage fully covered this way is `COVERED_BY_PRIOR_MITIGATION`.
- **Ledgers and events:** every unit drawn is written to `capacity_ledger`. Each decision is written to `mitigation_event` (PROPOSED → SELECTED / REJECTED with a reason) and to `shortage_event`.
