"""Planning calendar: integer week index <-> ISO week label.

Week index 1 is ISO week 2026W01 (starting Monday 2025-12-29). Indices <= 0
are weeks in 2025 (orders placed before the snapshot).
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np

BASE = date.fromisocalendar(2026, 1, 1)
_LO, _HI = -120, 200
_OFFSET = -_LO


def week_start(w: int) -> date:
    return BASE + timedelta(weeks=int(w) - 1)


def label(w: int) -> str:
    y, wk, _ = week_start(w).isocalendar()
    return f"{y}W{wk:02d}"


_LABELS = np.array([label(w) for w in range(_LO, _HI)], dtype=object)
_INDEX = {lab: w for w, lab in zip(range(_LO, _HI), _LABELS)}


def labels(weeks) -> np.ndarray:
    arr = np.asarray(weeks, dtype=np.int64)
    return _LABELS[arr + _OFFSET]


def index(lab: str) -> int:
    return _INDEX[lab]


def indices(labs) -> np.ndarray:
    return np.array([_INDEX[x] for x in labs], dtype=np.int64)


def is_valid(lab: str) -> bool:
    return lab in _INDEX
