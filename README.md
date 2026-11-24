# ORYVA: Demand, Inventory & Supply Planning

An end-to-end planning pipeline. It compares a weekly **forecast demand** against **inventory, supplier
capacity, lead times and production constraints**, then **finds, explains, prioritises and mitigates
shortages** on a fully synthetic, reproducible dataset that includes labelled anomalies.

```
generate ──► detect ──► plan ──────────────► validate ──► evaluate ──► report.html
(17 input    (blind      (projected balance,   (428 checks   (detector vs
 tables +     anomaly     shortages, causes,    + SQLite FK)  ground truth,
 ground       detector)   priority,                           plan KPIs)
 truth)                   mitigations)
```

## Quick start (one step)

Requires Python 3.10+. No database or server is needed.

```bash
./run.sh            # creates .venv on first run, runs starter + full pipelines and the tests (~45 s)
./run.sh starter    # starter scale only (~2 s)
```

Or run it by hand:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m oryva all --scale starter          # or --scale full
.venv/bin/python -m pytest -q
```

Then open `output/<scale>/report.html` in a browser.

### Commands

| Command | What it does |
|---|---|
| `python -m oryva all --scale S [--seed N] [--no-reproduce]` | Every stage below, in order. Exit code 0 only if validation passes. |
| `python -m oryva generate --scale S --seed N` | Writes `data/S/*.csv[.gz]`, `ground_truth/S/`, `manifest.json`, `generator_run.json` |
| `python -m oryva detect --scale S` | Blind anomaly detection → `output/S/exception.csv` |
| `python -m oryva plan --scale S` | Projected balance, shortages, causes, priorities, mitigations |
| `python -m oryva validate --scale S` | `output/S/validation_summary.{json,md}` (also loads everything into SQLite with FK checks) |
| `python -m oryva evaluate --scale S` | `output/S/evaluation.json`, `evaluation_report.md`, `report.html` |
| `python -m oryva reproduce --scale S` | Generates twice with the same seed and compares row counts + SHA-256; also checks against the committed data |
| `python -m oryva docs` | Rebuilds `docs/data_dictionary.md` and `schema/schema.sql` from `oryva/schema.py` |

`make all SCALE=full`, `make test` and similar targets do the same things if `make` is installed.

### Configuration

All parameters live in [`oryva/config.py`](oryva/config.py): scale presets, the seed and every business rate (spike rate, cancellation rate, cost model, priority weights, and so on).

| Preset | SKUs | Locations | Weeks | Suppliers | Baseline inbound POs | Anomalies per type |
|---|---|---|---|---|---|---|
| `starter` | 100 | 5 | 52 | 20 | 300 | 5 |
| `full` | **3,000** | **50** | **52** | **500** | **10,000** | 40 |

Both presets run the same generator with the same seed (`20261022`). Master records come from per-entity random streams, so starter SKUs are an exact subset of the full SKUs, and a test checks this.

## Repository layout

```
oryva/            pipeline code (generate, engine, detect, plan, validate, evaluate, report, schema)
tests/            pytest suite (28 tests, including hand-calculated balances)
docs/             data_dictionary.md · erd.md · business_rules.md · edge_cases.md · source_manifest.md
schema/           schema.sql (DDL with PK/FK/CHECK/UNIQUE, generated from oryva/schema.py)
data/starter/     input CSVs + seed.sql (SQL seed) + json/ (master data) + manifest.json + generator_run.json
data/full/        input CSVs (large ones gzipped) + manifest.json + generator_run.json
ground_truth/<s>/ ground_truth.csv / .json: anomaly + boundary labels, physically separate from inputs
output/<s>/       plan outputs, exception.csv, validation_summary, evaluation_report, reproducibility_report, report.html
output/test_results.txt   latest pytest output
```

## How the solution meets the brief

| Brief requirement | Where |
|---|---|
| Entities with PK/FK, cardinality, bridge tables, effective dates, lifecycles | [docs/erd.md](docs/erd.md), [docs/data_dictionary.md](docs/data_dictionary.md), [schema/schema.sql](schema/schema.sql) |
| Data dictionary (type, required, allowed values, units, uniqueness, rule) | [docs/data_dictionary.md](docs/data_dictionary.md), generated from the same code the validator uses |
| Required ID patterns | `SKU-000001`, `DEM-<sku>-<loc>-2026W01`, `PO-2026-000001`, `SHORT-2026-000001`, `MIT-<shortage-id>-01` (pattern-checked) |
| Dependency-ordered generation, derived values from sources | [docs/business_rules.md §1–2](docs/business_rules.md) |
| Projected available balance by week | `projected_balance` table; reconciliation checks in the validation summary |
| Shortages identified, **explained**, prioritised | `shortage`, `shortage_cause` (counterfactual attribution that sums exactly, with evidence record ids), `priority_rank` |
| Mitigations respecting policy and capacity; cost/service trade-offs | `mitigation_option` (cost, fill %, dominated flag, rejection reason), `capacity_ledger`, `mitigation_event` |
| Five actors (supplier, planner, carrier/warehouse operator, logistics analyst, operations manager) | `actor` on `po_event`, `shortage_event` and `mitigation_event`, plus `exception.owner`; approval matrix in [business_rules.md §5](docs/business_rules.md) |
| On-hand **and inbound** inventory | `inventory.on_hand_qty`, `allocated_qty`, `in_transit_qty` (derived from shipments) plus open POs |
| History preserved, not overwritten | `po_event`, `shortage_event`, `mitigation_event` (append-only); PO status is derived from events |
| Five required edge cases, labelled and traceable | [docs/edge_cases.md](docs/edge_cases.md), `ground_truth/` |
| Separate ground truth, never an input feature | Own folder; tests check that detect/plan never open it |
| Validation: PK, FK, enums, dates, arithmetic, lifecycle, duplicates | `output/<s>/validation_summary.md` (428 integrity checks + business rules + SQLite `foreign_key_check`) |
| Reproducibility | `output/<s>/reproducibility_report.md`: two runs byte-identical (gzip `mtime=0`), match the committed files, and seed+1 differs |
| Exports: CSV / JSON / SQL | CSV for every table; JSON for ground truth, masters (starter) and all summaries; `schema/schema.sql` + `data/starter/seed.sql` |
| Lawful provenance | [docs/source_manifest.md](docs/source_manifest.md): fully synthetic, no external data |

## Key design decisions

1. **The plan uses cleaned data, and the raw plan is kept alongside.** A blind detector flags suspect records. The official plan applies each flag's correction, and a raw plan with the anomalies left in shows the damage each one would do. For example, double-counted inbound hides shortages, and UoM errors create false ones (evaluation report §2).
2. **Causes add up.** Disruptions are removed one at a time in a fixed order. Each one's contribution is how much the shortage shrinks, and whatever is left is the base supply gap. Every shortage's causes add up exactly to its quantity, with the source record ids attached.
3. **Mitigations draw on shared ledgers.** Shortages are handled in priority order against shared ledgers for supplier capacity, plant capacity, donor stock, substitute stock and component stock. Two shortages can never be promised the same capacity, and the validator re-checks every ledger draw.
4. **Recoverable vs inside the lead-time fence.** Shortages that start before any supplier could deliver can only be fixed by transfers, substitutes, expediting or production. The plan labels them so a planner can act first where it matters.
5. **The baseline is realistic.** Inbound POs are sized as a planner would have placed them before the latest promotions were known. Shortages therefore come from real deviations (spikes, cancellations, cuts, delays, under-ordering), not random noise. Full scale: about 9% of demand is at risk, and 90% of it gets mitigated.

## Results (seed 20261022)

| | Starter | Full |
|---|---|---|
| Validation | PASS (0 integrity failures; 35/35 business-rule violations are labelled anomalies) | PASS (0 integrity failures; 279/279 labelled) |
| Detector precision / recall | 1.000 / 1.000 | 1.000 / 1.000 |
| Boundary records wrongly flagged | 0 / 12 | 0 / 40 |
| Shortages / recoverable | 310 / 91% | 10,155 / 91% |
| Fill rate after mitigation | 90.1% | 90.1% |
| Reproducible (same seed, byte-identical) | yes | yes |

The detector is perfect on these labels because each anomaly breaks a precise, checkable rule. On real data, D5 (UoM) would be a heuristic.

## Limitations

- A single planning snapshot (as of 2026W01). Re-planning across several snapshots ("as of week N") is not implemented.
- Mitigations are chosen greedily by unit cost in priority order, not by a global optimiser (LP).
- Transfers assume a fixed one-week lane between any two locations. Substitutes use a 1:1 conversion ratio.
- The SQLite database (`output/<s>/oryva.sqlite`) is rebuilt by `validate` and is not committed, because it is about 220 MB at full scale.
