#!/usr/bin/env python3
"""Check imports and a real MuJoCo off-screen render.

Set MUJOCO_GL before importing mujoco. Examples:

    python scripts/check_runtime.py --backend egl --egl-device 0
    python scripts/check_runtime.py --backend osmesa
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("egl", "osmesa"), default="egl")
    parser.add_argument(
        "--egl-device",
        type=int,
        default=None,
        help="Physical EGL device index; omit unless a specific GPU is required.",
    )
    return parser.parse_args()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def main() -> None:
    args = parse_args()
    os.environ["MUJOCO_GL"] = args.backend
    if args.egl_device is not None:
        os.environ["MUJOCO_EGL_DEVICE_ID"] = str(args.egl_device)

    # These imports must happen after MUJOCO_GL is set.
    import mujoco
    import numpy as np
    import robosuite

    xml = """
    <mujoco model="runtime_check">
      <worldbody>
        <light pos="0 0 3"/>
        <geom type="plane" size="1 1 0.1" rgba="0.7 0.7 0.7 1"/>
        <body pos="0 0 0.3">
          <freejoint/>
          <geom type="box" size="0.1 0.1 0.1" rgba="0.8 0.1 0.1 1"/>
        </body>
      </worldbody>
    </mujoco>
    """
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    renderer = mujoco.Renderer(model, height=120, width=160)
    renderer.update_scene(data)
    image = renderer.render()
    renderer.close()

    if image.shape != (120, 160, 3) or image.dtype != np.uint8:
        raise RuntimeError(
            f"Unexpected render output: shape={image.shape}, dtype={image.dtype}"
        )

    result = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "mujoco": mujoco.__version__,
        "robosuite": robosuite.__version__,
        "numpy": np.__version__,
        "h5py": package_version("h5py"),
        "backend": args.backend,
        "egl_device": args.egl_device,
        "render_shape": list(image.shape),
        "render_dtype": str(image.dtype),
        "render_mean": float(image.mean()),
        "status": "ok",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

