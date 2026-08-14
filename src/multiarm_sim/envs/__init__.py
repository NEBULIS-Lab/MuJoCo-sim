"""Custom MuJoCo / robosuite environments used by this project."""

from multiarm_sim.envs.handover_box import (
    COLORS,
    CONTROL_FREQUENCY,
    GLOBAL_CAMERA,
    LOCAL_CAMERAS,
    ColoredHandoverBox,
    frame_from_observation,
    make_handover_box_env,
    proprio_from_observation,
)

__all__ = [
    "COLORS",
    "CONTROL_FREQUENCY",
    "GLOBAL_CAMERA",
    "LOCAL_CAMERAS",
    "ColoredHandoverBox",
    "frame_from_observation",
    "make_handover_box_env",
    "proprio_from_observation",
]
