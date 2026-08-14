"""Shared construction and observation helpers for the first Lift test."""

from __future__ import annotations

import numpy as np

GLOBAL_CAMERA = "agentview"
LOCAL_CAMERA = "robot0_eye_in_hand"
INSTRUCTION = "Lift the red cube above the table."
ROLE_INSTRUCTION = "Move to the red cube, grasp it, and lift it vertically."
CONTROL_FREQUENCY = 20


def make_lift_env(
    *,
    image_size: int = 256,
    horizon: int = 1000,
    seed: int | None = None,
):
    """Create the exact robosuite environment used by collectors and replay."""
    import robosuite as suite

    if seed is not None:
        np.random.seed(seed)
    return suite.make(
        env_name="Lift",
        robots="Panda",
        has_renderer=False,
        has_offscreen_renderer=True,
        use_camera_obs=True,
        camera_names=[GLOBAL_CAMERA, LOCAL_CAMERA],
        camera_heights=[image_size, image_size],
        camera_widths=[image_size, image_size],
        reward_shaping=True,
        control_freq=CONTROL_FREQUENCY,
        horizon=horizon,
        ignore_done=True,
        seed=seed,
    )


def top_left_rgb(image: np.ndarray) -> np.ndarray:
    """Convert MuJoCo's bottom-left image origin to normal image coordinates."""
    return np.ascontiguousarray(np.flipud(image))


def proprio_from_observation(observation: dict) -> np.ndarray:
    """Nine-dimensional Panda joint + gripper state expected by our adapter."""
    return np.concatenate(
        [
            observation["robot0_joint_pos"],
            observation["robot0_gripper_qpos"],
        ]
    ).astype(np.float32)


def frame_from_observation(observation: dict, camera: str) -> np.ndarray:
    return top_left_rgb(observation[f"{camera}_image"])

