# Source manifest and data provenance

| Item | Value |
|---|---|
| Data origin | **100% synthetic**, produced by `oryva/generate.py` |
| External datasets used | **None** |
| Personal / confidential data | None. Names are generated labels such as "Supplier 0007 North" and "Snacks item 000042". |
| Access controls bypassed | None |
| Licence of generated data | Same as this repository; freely redistributable |
| Generator command | `python -m oryva generate --scale <starter\|full> --seed 20261022` |
| Fixed seed | `20261022` (`oryva/config.py::DEFAULT_SEED`) |
| Run metadata | `data/<scale>/generator_run.json`: command, seed, scale parameters, Python/numpy/pandas versions |
| File checksums | `data/<scale>/manifest.json`: rows, bytes and SHA-256 per file, plus the ground-truth checksum |
| Reproducibility evidence | `output/<scale>/reproducibility_report.md` |

## Public reference used for schema inspiration only

No external data was downloaded, copied or transformed. The entity design follows common, publicly documented supply-planning concepts:
- projected available balance (MRP)
- ABC classification
- MOQ and order multiples
- advance shipping notices
- bills of materials

Distribution choices (negative binomial demand, intermittent demand for slow movers, lognormal lead times) are standard textbook modelling assumptions.

Since no external data is used, there is no source URL, version, retrieval date, licence, attribution, transformation list or discarded-field list to record.
