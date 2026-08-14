#!/usr/bin/env python3
"""Validate a MuJoCo HDF5 dataset and create COMMVLA adapter assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from multiarm_sim.dataset import prepare_commvla_assets, validate_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("artifacts/commvla_lift"),
    )
    args = parser.parse_args()
    validation = validate_dataset(args.dataset)
    if validation["successful_trajectories"] != len(validation["trajectories"]):
        raise ValueError(
            "Training export requires a success-only HDF5 file. "
            "Keep failed/manual diagnostic episodes in a separate file."
        )
    result = {
        "validation": validation,
        "commvla": prepare_commvla_assets(args.dataset, args.output_directory),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
