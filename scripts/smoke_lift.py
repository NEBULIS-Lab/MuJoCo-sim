#!/usr/bin/env python3
"""Run a short headless robosuite Lift episode and save one camera frame."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("egl", "osmesa"), default="egl")
    parser.add_argument("--egl-device", type=int, default=None)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/smoke/lift_agentview.png"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ["MUJOCO_GL"] = args.backend
    if args.egl_device is not None:
        os.environ["MUJOCO_EGL_DEVICE_ID"] = str(args.egl_device)

    # Import only after selecting the OpenGL backend.
    import numpy as np
    import robosuite as suite
    from PIL import Image

    env = suite.make(
        env_name="Lift",
        robots="Panda",
        has_renderer=False,
        has_offscreen_renderer=True,
        use_camera_obs=True,
        camera_names="agentview",
        camera_heights=128,
        camera_widths=128,
        control_freq=20,
        horizon=max(args.steps + 1, 100),
    )

    try:
        obs = env.reset()
        low, high = env.action_spec
        action = np.zeros_like(low)

        for _ in range(args.steps):
            obs, reward, done, info = env.step(action)
            if done:
                break

        frame = obs["agentview_image"]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # MuJoCo camera observations use a bottom-left image origin.
        Image.fromarray(np.flipud(frame)).save(args.output)

        print(f"robosuite={suite.__version__}")
        print(f"action_dim={env.action_dim}")
        print(f"action_shape={action.shape}")
        print(f"observation_keys={sorted(obs.keys())}")
        print(f"frame_shape={frame.shape}")
        print(f"last_reward={reward}")
        print(f"last_done={done}")
        print(f"frame={args.output.resolve()}")
    finally:
        env.close()


if __name__ == "__main__":
    main()
