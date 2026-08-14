#!/usr/bin/env python3
"""Validate a handover dataset and prepare assets consumed by COMMVLA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from multiarm_sim.dual_dataset import (
    prepare_dual_commvla_assets,
    validate_dual_arm_dataset,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/commvla_handover_box"),
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Prepare diagnostic assets even when failed demonstrations are present.",
    )
    args = parser.parse_args()
    report = validate_dual_arm_dataset(args.dataset)
    assets = prepare_dual_commvla_assets(
        args.dataset,
        args.output_dir,
        require_success=not args.allow_failures,
    )
    print(json.dumps({"validation": report, "assets": assets}, indent=2))


if __name__ == "__main__":
    main()
