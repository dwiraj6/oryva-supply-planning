"""Seeded random streams.

Each logical stream gets its own numpy Generator derived from
(seed, stream code, *keys). Master entities are drawn with the entity number
as a key, so SKU-000042 has identical attributes in the starter and full
datasets. Nothing here depends on Python's hash randomisation or wall time.
"""
from __future__ import annotations

import numpy as np

STREAMS = {
    "sku": 11, "location": 12, "supplier": 13, "category": 14,
    "assortment": 21, "bom": 22, "supplier_sku": 23, "substitute": 24,
    "lead_time": 25, "demand": 31, "production": 32, "inventory": 33,
    "po": 41, "po_status": 42, "capacity": 43, "shipment": 44,
    "boundary": 51, "inject": 52,
}


def rng(seed: int, stream: str, *keys: int) -> np.random.Generator:
    return np.random.default_rng([int(seed), STREAMS[stream], *[int(k) for k in keys]])
