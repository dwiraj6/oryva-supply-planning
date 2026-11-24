# Edge cases, boundary cases and ground truth

The clean baseline is generated first. Edge cases are then injected into **specific records only**
(`oryva/generate.py::_inject`), and every injected or boundary record is written to
`ground_truth/<scale>/ground_truth.csv` (and `.json`).

The ground-truth file lives in its own folder. It is **never read** by `detect.py`, `engine.py`
or `plan.py`, and a test enforces this both statically and at runtime. Only the validator and the
evaluator read it: the validator to explain deliberate business-rule violations, the evaluator to
score the detector.

Counts per type are 5 at starter scale and 40 at full scale (`Scale.edge_cases_per_type`).

## Required negative scenarios

| issue_type | How it is injected | Field changed (correct → corrupted) | Effect on the raw plan | Caught by |
|---|---|---|---|---|
| `INBOUND_DOUBLE_COUNT` | A second ASN (`inbound_shipment`) for a PO already in transit, with the same qty, carrier and ship week | new `shipment_id` | Receipt counted twice; balance overstated; shortages hidden | D1 + validator BR1/BR6 |
| `SUBSTITUTE_NOT_APPROVED` | A new PO buying SKU X to cover SKU Y, where pair (Y, X) is PENDING or REJECTED | `substitute_for_sku_id` null → Y | Supply credited to the wrong SKU | D2 + BR2 |
| `SUPPLIER_CAPACITY_EXCEEDED` | A new confirmed PO that pushes a supplier-week above `capacity_base_qty` | `confirmed_base_qty` allowed → excess | Supply the supplier cannot deliver | D3 + BR3 |
| `SHORTAGE_WITHOUT_LEAD_TIME` | An existing unshipped PO's `promised_week` set to its `order_week` | `promised_week` order+LT → order | Supply credited weeks too early; near-term shortages hidden | D4 + BR4 |
| `UOM_MISMATCH` | An existing CASE PO re-keyed as EA without converting the qty | `order_uom` CASE → EA | Supply understated by pack size; false shortages | D5 + BR5/BR7 |

Each label records `record_id`, `related_record_ids` (lead-time lane, substitute pair, capacity row, original shipment), `field`, `correct_value`, `corrupted_value` and `impact_base_qty`.

Injection never touches records protected as boundary cases. It keeps supplier-week loads consistent, so one anomaly cannot accidentally trigger a different rule.

## Boundary (valid) cases: must NOT be flagged

| issue_type | Record | Expectation |
|---|---|---|
| `BOUNDARY_PO_AT_MOQ` | PO with `requested_base_qty == moq_base_qty` | Not flagged by any rule |
| `BOUNDARY_CAPACITY_AT_100PCT` | Supplier-week with load exactly equal to capacity | Not flagged; no spare left for mitigations |
| `BOUNDARY_ZERO_BALANCE` | Inventory set so the minimum projected closing is exactly 0 | No shortage (rule is `< 0`) |
| `BOUNDARY_RECEIPT_AT_HORIZON_END` | PO promised exactly in 2026W52 | Receipt counted in W52 |

## Normal, failure and exception coverage

- **Normal:** most SKU-locations stay healthy, with projected balance above safety stock.
- **Failure paths in the baseline:**
  - capacity cuts
  - cancellations
  - supplier and transport delays
  - on-hold suppliers
  - unapproved substitutes (listed as infeasible mitigations)
  - component shortages that block production
  - shortages inside the lead-time fence
- **Exception paths:** the five injected anomalies, which are quarantined and corrected in the cleaned plan. Shortages that no feasible mitigation can cover end as `ACCEPT_SHORTFALL`.

Detector scores and the measured plan impact of each anomaly are in `output/<scale>/evaluation_report.md`.
