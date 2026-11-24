"""Deterministic CSV/JSON read & write driven by the schema."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .schema import TABLES

GZIP = {"method": "gzip", "mtime": 0}   # mtime=0 keeps gzip bytes reproducible
BIG_TABLES = {"forecast_demand", "projected_balance", "receipt_line", "po_event",
              "mitigation_option", "mitigation_event", "shortage_event", "shortage_cause",
              "capacity_ledger", "supplier_capacity", "production_plan", "production_capacity"}


def path_for(folder: Path, name: str, compress: bool) -> Path:
    gz = compress and name in BIG_TABLES
    return Path(folder) / (f"{name}.csv.gz" if gz else f"{name}.csv")


def _normalise(df: pd.DataFrame, name: str) -> pd.DataFrame:
    t = TABLES[name]
    df = df[[c.name for c in t.cols]].copy()
    for c in t.cols:
        s = df[c.name]
        if c.type == "int":
            df[c.name] = pd.array(pd.to_numeric(s).round(0), dtype="Int64")
        elif c.type == "float":
            df[c.name] = pd.to_numeric(s).astype("float64").round(4)
        elif c.type == "bool":
            df[c.name] = s.astype(bool)
        else:
            df[c.name] = s.astype(object).where(s.notna(), None)
    return df.sort_values(t.pk, kind="mergesort").reset_index(drop=True)


def write_table(df: pd.DataFrame, folder: Path, name: str, compress: bool) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    df = _normalise(df, name)
    p = path_for(folder, name, compress)
    other = path_for(folder, name, not compress)
    if other != p and other.exists():
        other.unlink()
    df.to_csv(p, index=False, lineterminator="\n", compression=GZIP if p.suffix == ".gz" else None)
    return p


def read_table(folder: Path, name: str) -> pd.DataFrame:
    folder = Path(folder)
    p = folder / f"{name}.csv"
    if not p.exists():
        p = folder / f"{name}.csv.gz"
    t = TABLES[name]
    dtypes = {}
    for c in t.cols:
        if c.type == "int":
            dtypes[c.name] = "Int64"
        elif c.type == "float":
            dtypes[c.name] = "float64"
        elif c.type == "bool":
            dtypes[c.name] = "boolean"
        else:
            dtypes[c.name] = object
    df = pd.read_csv(p, dtype=dtypes, keep_default_na=False, na_values=[""])
    for c in t.cols:
        if c.type in ("str", "week", "date"):
            df[c.name] = df[c.name].astype(object).where(df[c.name].notna(), None)
    return df


def read_many(folder: Path, names) -> dict[str, pd.DataFrame]:
    return {n: read_table(folder, n) for n in names}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(obj, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        raise TypeError(type(o))

    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True, default=default) + "\n")


def manifest(folder: Path) -> dict:
    folder = Path(folder)
    files = {}
    for p in sorted(folder.glob("*.csv*")):
        opener = gzip.open if p.suffix == ".gz" else open
        with opener(p, "rb") as f:
            rows = sum(1 for _ in f) - 1
        files[p.name] = {"rows": int(rows), "sha256": sha256(p), "bytes": p.stat().st_size}
    return files
