import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from oryva import io, pipeline  # noqa: E402
from oryva.config import DEFAULT_SEED  # noqa: E402
from oryva.schema import INPUT_TABLES, OUTPUT_TABLES  # noqa: E402


@pytest.fixture(scope="session")
def run(tmp_path_factory):
    """One full starter pipeline run into a temporary root, shared by all tests."""
    root = tmp_path_factory.mktemp("oryva")
    res = pipeline.run_all("starter", DEFAULT_SEED, root, reproduce=False)
    p = pipeline.Paths(root, "starter")
    t = io.read_many(p.data, INPUT_TABLES)
    o = {n: io.read_table(p.out, n) for n in OUTPUT_TABLES}
    gt = io.read_table(p.gt, "ground_truth")
    return {"root": root, "paths": p, "t": t, "o": o, "gt": gt, **res}
