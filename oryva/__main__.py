"""Command line: python -m oryva <command> [--scale starter|full] [--seed N]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import pipeline as pl
from .config import DEFAULT_SEED, SCALES


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m oryva", description="ORYVA demand, inventory & supply planning")
    ap.add_argument("command", choices=["all", "generate", "detect", "plan", "validate", "evaluate", "reproduce", "docs"])
    ap.add_argument("--scale", choices=sorted(SCALES), default="starter")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--no-reproduce", action="store_true", help="skip the double-generation check in 'all'")
    a = ap.parse_args(argv)
    scale = SCALES[a.scale]
    p = pl.Paths(a.root, a.scale)
    if a.command == "all":
        res = pl.run_all(a.scale, a.seed, a.root, reproduce=not a.no_reproduce)
        return 0 if res["validation"]["overall_status"] == "PASS" else 1
    if a.command == "generate":
        pl.stage_generate(scale, a.seed, a.root)
    elif a.command == "detect":
        pl.stage_detect(p, scale.compress)
    elif a.command == "plan":
        pl.stage_plan(p, scale.compress)
    elif a.command == "validate":
        v = pl.stage_validate(p)
        return 0 if v["overall_status"] == "PASS" else 1
    elif a.command == "evaluate":
        pl.stage_evaluate(p, a.seed)
    elif a.command == "reproduce":
        r = pl.stage_reproduce(scale, a.seed, a.root)
        return 0 if r["all_identical"] else 1
    elif a.command == "docs":
        pl.stage_docs(a.root)
    pl.stage_manifest(p) if p.out.exists() else None
    return 0


if __name__ == "__main__":
    sys.exit(main())
