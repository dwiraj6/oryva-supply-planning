"""Deterministic, zero-padded, immutable identifiers (brief Section 4)."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

PATTERNS = {
    "sku": r"SKU-\d{6}",
    "location": r"LOC-\d{3}",
    "supplier": r"SUP-\d{4}",
    "week": r"\d{4}W\d{2}",
    "demand": r"DEM-SKU-\d{6}-LOC-\d{3}-\d{4}W\d{2}",
    "po": r"PO-2026-\d{6}",
    "shortage": r"SHORT-2026-\d{6}",
    "mitigation": r"MIT-SHORT-2026-\d{6}-\d{2}",
}


def sku(i: int) -> str:
    return f"SKU-{i:06d}"


def location(i: int) -> str:
    return f"LOC-{i:03d}"


def supplier(i: int) -> str:
    return f"SUP-{i:04d}"


def po(i: int) -> str:
    return f"PO-2026-{i:06d}"


def shortage(i: int) -> str:
    return f"SHORT-2026-{i:06d}"


def mitigation(shortage_id: str, k: int) -> str:
    return f"MIT-{shortage_id}-{k:02d}"


def seq(prefix: str, n: int, width: int, start: int = 1) -> np.ndarray:
    """Vectorised sequential ids: prefix + zero padded counter."""
    return np.array([f"{prefix}{i:0{width}d}" for i in range(start, start + n)], dtype=object)


def demand_ids(sku_ids: pd.Series, loc_ids: pd.Series, weeks: pd.Series) -> pd.Series:
    return "DEM-" + sku_ids.astype(str) + "-" + loc_ids.astype(str) + "-" + weeks.astype(str)


def matches(pattern_key: str, values: pd.Series) -> pd.Series:
    rx = re.compile(rf"^{PATTERNS[pattern_key]}$")
    return values.astype(str).map(lambda v: bool(rx.match(v)))
