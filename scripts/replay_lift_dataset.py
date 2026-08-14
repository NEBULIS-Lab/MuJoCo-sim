#!/usr/bin/env python3
"""Replay recorded MuJoCo states, compare rendered frames, and write an MP4."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--trajectory", default="trajectory_000000")
    parser.add_argument("--camera", choices=("agentview", "robot0_eye_in_hand"), default="agentview")
    parser.add_argument("--output", type=Path, default=Path("artifacts/replay/lift.mp4"))
    parser.add_argument("--backend", choices=("egl", "osmesa"), default="egl")
    parser.add_argument("--egl-device", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ["MUJOCO_GL"] = args.backend
    if args.egl_device is not None:
        os.environ["MUJOCO_EGL_DEVICE_ID"] = str(args.egl_device)

    import h5py
    import imageio.v2 as imageio
    import numpy as np

    from multiarm_sim.lift import CONTROL_FREQUENCY, make_lift_env, top_left_rgb

    with h5py.File(args.dataset, "r") as handle:
        trajectory = handle[args.trajectory]
        states = trajectory["sim/states"][:]
        stored = trajectory[f"obs/sensor_data/{args.camera}/rgb"][:]
        seed = int(trajectory.attrs["seed"])

    image_size = int(stored.shape[1])
    env = make_lift_env(image_size=image_size, horizon=len(states) + 1, seed=seed)
    rendered_frames = []
    errors = []
    try:
        env.reset()
        for state, expected in zip(states, stored):
            env.sim.set_state_from_flattened(state)
            env.sim.forward()
            rendered = top_left_rgb(
                env.sim.render(
                    camera_name=args.camera,
                    height=image_size,
                    width=image_size,
                )
            )
            rendered_frames.append(rendered)
            errors.append(float(np.abs(rendered.astype(np.int16) - expected.astype(np.int16)).mean()))
    finally:
        env.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(args.output, rendered_frames, fps=CONTROL_FREQUENCY, macro_block_size=1)
    print(f"trajectory={args.trajectory}")
    print(f"frames={len(rendered_frames)}")
    print(f"mean_absolute_pixel_error={float(np.mean(errors)):.6f}")
    print(f"max_frame_absolute_pixel_error={float(np.max(errors)):.6f}")
    print(f"video={args.output.resolve()}")


if __name__ == "__main__":
    main()

