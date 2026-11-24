"""Stage orchestration. Every stage reads its inputs from disk so the files
are the contract between stages (and between runs)."""
from __future__ import annotations

import json
import platform
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from . import detect as det
from . import evaluate as evl
from . import io
from . import plan as pln
from . import report
from . import validate as val
from .config import SCALES, Scale
from .generate import generate as gen
from .schema import INPUT_TABLES, OUTPUT_TABLES, TABLES, to_markdown, to_sql_ddl


class Paths:
    def __init__(self, root: Path, scale: str):
        self.root = Path(root)
        self.data = self.root / "data" / scale
        self.gt = self.root / "ground_truth" / scale
        self.out = self.root / "output" / scale


def log(msg: str) -> None:
    print(f"[oryva] {msg}", flush=True)


# ---------------------------------------------------------------- stages
def stage_generate(scale: Scale, seed: int, root: Path, data_dir: Path | None = None, gt_dir: Path | None = None) -> dict:
    p = Paths(root, scale.name)
    data_dir = Path(data_dir or p.data)
    gt_dir = Path(gt_dir or p.gt)
    t0 = time.time()
    t, gt = gen(scale, seed)
    if data_dir.exists():
        for f in data_dir.glob("*.csv*"):
            f.unlink()
    for name in INPUT_TABLES:
        io.write_table(t[name], data_dir, name, scale.compress)
    gt_dir.mkdir(parents=True, exist_ok=True)
    gtn = io._normalise(gt, "ground_truth")
    gtn.to_csv(gt_dir / "ground_truth.csv", index=False, lineterminator="\n")
    (gt_dir / "ground_truth.json").write_text(gtn.to_json(orient="records", indent=1) + "\n")
    man = io.manifest(data_dir)
    io.write_json({"scale": scale.to_dict(), "seed": seed, "files": man,
                   "ground_truth": {"rows": len(gtn), "sha256": io.sha256(gt_dir / "ground_truth.csv")}},
                  data_dir / "manifest.json")
    io.write_json({"generator": "python -m oryva generate", "command": f"python -m oryva generate --scale {scale.name} --seed {seed}",
                   "seed": seed, "scale": scale.to_dict(), "oryva_version": __version__,
                   "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                   "external_data": "none (fully synthetic; see docs/source_manifest.md)"}, data_dir / "generator_run.json")
    if scale.name == "starter":
        _seed_sql(t, data_dir / "seed.sql")
        _json_exports(t, data_dir / "json")
    log(f"generate {scale.name}: {sum(v['rows'] for v in man.values()):,} rows in {len(man)} files, "
        f"{len(gtn)} ground-truth labels ({time.time() - t0:.1f}s)")
    return t


def _seed_sql(t: dict, path: Path) -> None:
    con = sqlite3.connect(":memory:")
    con.executescript(to_sql_ddl().replace("PRAGMA foreign_keys = ON;", ""))
    for name in INPUT_TABLES:
        df = io._normalise(t[name], name)
        cols = list(df.columns)
        rows = [tuple(None if pd.isna(v) else (int(v) if isinstance(v, (bool, np.bool_, np.integer)) else v) for v in r)
                for r in df.itertuples(index=False, name=None)]
        con.executemany(f"INSERT INTO {name} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", rows)
    with open(path, "w") as f:
        f.write("PRAGMA foreign_keys = ON;\n")
        for line in con.iterdump():
            f.write(line + "\n")
    con.close()


def _json_exports(t: dict, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("sku", "location", "supplier", "supplier_sku", "sku_substitute", "bom", "lead_time"):
        df = io._normalise(t[name], name)
        (folder / f"{name}.json").write_text(df.to_json(orient="records", indent=1) + "\n")


def load_inputs(p: Paths) -> dict:
    return io.read_many(p.data, INPUT_TABLES)


def stage_detect(p: Paths, compress: bool, t: dict | None = None) -> pd.DataFrame:
    t = t or load_inputs(p)
    exc = det.detect(t)
    io.write_table(exc, p.out, "exception", compress)
    log(f"detect: {len(exc)} exceptions " + json.dumps(exc.issue_type.value_counts().to_dict()))
    return exc


def stage_plan(p: Paths, compress: bool, t: dict | None = None, exc: pd.DataFrame | None = None) -> dict:
    t = t or load_inputs(p)
    exc = exc if exc is not None else io.read_table(p.out, "exception")
    t0 = time.time()
    o = pln.run(t, exc)
    for name in OUTPUT_TABLES:
        if name != "exception":
            io.write_table(o[name], p.out, name, compress)
    sh = o["shortage"]
    log(f"plan: {len(sh):,} shortages, {len(o['mitigation_option']):,} mitigation options ({time.time() - t0:.1f}s)")
    return o


def _read_outputs(p: Paths) -> dict:
    return {n: io.read_table(p.out, n) for n in OUTPUT_TABLES}


def stage_validate(p: Paths, t: dict | None = None, o: dict | None = None) -> dict:
    t = t or load_inputs(p)
    o = o or _read_outputs(p)
    exc = o["exception"] if "exception" in o else io.read_table(p.out, "exception")
    gt = io.read_table(p.gt, "ground_truth")
    t0 = time.time()
    v = val.validate(t, o, exc, gt, p.out / "oryva.sqlite")
    io.write_json(v, p.out / "validation_summary.json")
    (p.out / "validation_summary.md").write_text(val.to_markdown(v, p.out.name))
    log(f"validate: {v['overall_status']} - {v['integrity_checks']} integrity checks ({v['integrity_failed']} failed), "
        f"{v['business_rule_violations_explained_by_ground_truth']} business-rule violations all labelled, "
        f"{v['business_rule_violations_unexplained']} unexplained ({time.time() - t0:.1f}s)")
    return v


def stage_evaluate(p: Paths, seed: int, t: dict | None = None, o: dict | None = None) -> dict:
    t = t or load_inputs(p)
    exc = io.read_table(p.out, "exception")
    if o is None or "_raw" not in o:
        o = pln.run(t, exc)
    gt = io.read_table(p.gt, "ground_truth")
    ev = evl.evaluate(t, o, exc, gt)
    io.write_json(ev, p.out / "evaluation.json")
    (p.out / "evaluation_report.md").write_text(evl.to_markdown(ev, p.out.name))
    v = json.loads((p.out / "validation_summary.json").read_text())
    (p.out / "report.html").write_text(report.build(ev, v, p.out.name, seed))
    m = ev["detector"]["_micro"]
    log(f"evaluate: detector precision={m['precision']:.3f} recall={m['recall']:.3f}; "
        f"fill rate {ev['planning']['fill_rate_pct']}%; report -> {p.out / 'report.html'}")
    return ev


def stage_manifest(p: Paths) -> None:
    io.write_json({"files": io.manifest(p.out)}, p.out / "manifest.json")


def stage_reproduce(scale: Scale, seed: int, root: Path) -> dict:
    p = Paths(root, scale.name)
    tmp = Path(tempfile.mkdtemp(prefix="oryva-repro-"))
    try:
        runs = []
        for k in (1, 2):
            d = tmp / f"run{k}"
            stage_generate(scale, seed, root, data_dir=d / "data", gt_dir=d / "gt")
            runs.append({**io.manifest(d / "data"), "ground_truth.csv": {"rows": None, "sha256": io.sha256(d / "gt" / "ground_truth.csv")}})
        other = tmp / "other_seed"
        stage_generate(scale, seed + 1, root, data_dir=other / "data", gt_dir=other / "gt")
        diff_seed = io.manifest(other / "data")
    finally:
        pass
    committed = {}
    if (p.data / "manifest.json").exists():
        committed = json.loads((p.data / "manifest.json").read_text())["files"]
    rows = []
    for f in sorted(runs[0]):
        a, b = runs[0][f], runs[1][f]
        c = committed.get(f)
        rows.append({"file": f, "rows": a["rows"], "sha256_run1": a["sha256"], "sha256_run2": b["sha256"],
                     "identical": a["sha256"] == b["sha256"] and a["rows"] == b["rows"],
                     "matches_committed": (c is not None and c["sha256"] == a["sha256"]) if f != "ground_truth.csv" else None,
                     "differs_with_seed_plus_1": (f in diff_seed and diff_seed[f]["sha256"] != a["sha256"]) if f != "ground_truth.csv" else None})
    ok = all(r["identical"] for r in rows)
    res = {"scale": scale.name, "seed": seed, "all_identical": ok,
           "all_match_committed": all(r["matches_committed"] for r in rows if r["matches_committed"] is not None) if committed else None,
           "files": rows}
    shutil.rmtree(tmp, ignore_errors=True)
    io.write_json(res, p.out / "reproducibility.json")
    md = [f"# Reproducibility ({scale.name}, seed {seed})", "",
          f"Generated twice with the same seed into separate temporary folders: **{'IDENTICAL' if ok else 'DIFFERENT'}**.  ",
          f"Matches the committed dataset: **{res['all_match_committed']}**.  ",
          f"Same generator with seed {seed + 1} produces different files (sanity check).", "",
          "| File | Rows | SHA-256 (run 1) | Run 2 identical | Matches committed | Differs with seed+1 |", "|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['file']} | {r['rows'] if r['rows'] is not None else ''} | `{r['sha256_run1'][:16]}...` | {r['identical']} | "
                  f"{'' if r['matches_committed'] is None else r['matches_committed']} | {'' if r['differs_with_seed_plus_1'] is None else r['differs_with_seed_plus_1']} |")
    (p.out / "reproducibility_report.md").write_text("\n".join(md) + "\n")
    log(f"reproduce {scale.name}: identical={ok}, matches committed={res['all_match_committed']}")
    return res


def stage_docs(root: Path) -> None:
    (Path(root) / "docs").mkdir(exist_ok=True)
    (Path(root) / "schema").mkdir(exist_ok=True)
    (Path(root) / "docs" / "data_dictionary.md").write_text(to_markdown())
    (Path(root) / "schema" / "schema.sql").write_text(to_sql_ddl())
    log("docs: docs/data_dictionary.md and schema/schema.sql written")


def run_all(scale_name: str, seed: int, root: Path, reproduce: bool = True) -> dict:
    scale = SCALES[scale_name]
    p = Paths(root, scale_name)
    t0 = time.time()
    stage_docs(root)
    stage_generate(scale, seed, root)
    t = load_inputs(p)
    exc = stage_detect(p, scale.compress, t)
    o = stage_plan(p, scale.compress, t, exc)
    o["exception"] = exc
    v = stage_validate(p, t, o)
    ev = stage_evaluate(p, seed, t, o)
    if reproduce:
        stage_reproduce(scale, seed, root)
    stage_manifest(p)
    log(f"all {scale_name}: done in {time.time() - t0:.1f}s -> validation {v['overall_status']}")
    return {"validation": v, "evaluation": ev}
