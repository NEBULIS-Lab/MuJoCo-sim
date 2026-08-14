"""HDF5 recording and COMMVLA-compatible metadata for MuJoCo episodes."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import uuid

import h5py
import numpy as np

from multiarm_sim.lift import (
    CONTROL_FREQUENCY,
    GLOBAL_CAMERA,
    INSTRUCTION,
    LOCAL_CAMERA,
    ROLE_INSTRUCTION,
    frame_from_observation,
    proprio_from_observation,
)

SCHEMA_VERSION = "multiarm-sim-hdf5-v1"


@dataclass
class EpisodeBuffer:
    """In-memory buffer with pre-action observations and simulator states."""

    seed: int
    source: str
    recording_policy: str = "continuous"
    motion_tail_seconds: float = 0.0
    gripper_tail_seconds: float = 0.0
    actions: list[np.ndarray] = field(default_factory=list)
    proprio: list[np.ndarray] = field(default_factory=list)
    global_images: list[np.ndarray] = field(default_factory=list)
    local_images: list[np.ndarray] = field(default_factory=list)
    sim_states: list[np.ndarray] = field(default_factory=list)
    rewards: list[float] = field(default_factory=list)
    dones: list[bool] = field(default_factory=list)
    successes: list[bool] = field(default_factory=list)
    stages: list[int] = field(default_factory=list)
    wall_timestamps: list[float] = field(default_factory=list)
    capture_reasons: list[int] = field(default_factory=list)

    def append(
        self,
        *,
        observation: dict,
        sim_state: np.ndarray,
        action: np.ndarray,
        reward: float,
        done: bool,
        success: bool,
        stage: int = -1,
        wall_timestamp: float | None = None,
        capture_reason: int = 0,
    ) -> None:
        if wall_timestamp is None:
            wall_timestamp = len(self.actions) / CONTROL_FREQUENCY
        self.actions.append(np.asarray(action, dtype=np.float32).copy())
        self.proprio.append(proprio_from_observation(observation))
        self.global_images.append(frame_from_observation(observation, GLOBAL_CAMERA))
        self.local_images.append(frame_from_observation(observation, LOCAL_CAMERA))
        self.sim_states.append(np.asarray(sim_state, dtype=np.float64).copy())
        self.rewards.append(float(reward))
        self.dones.append(bool(done))
        self.successes.append(bool(success))
        self.stages.append(int(stage))
        self.wall_timestamps.append(float(wall_timestamp))
        self.capture_reasons.append(int(capture_reason))

    def __len__(self) -> int:
        return len(self.actions)


def _next_trajectory_name(handle: h5py.File) -> str:
    indices = [
        int(name.removeprefix("trajectory_"))
        for name in handle
        if name.startswith("trajectory_") and name.removeprefix("trajectory_").isdigit()
    ]
    return f"trajectory_{max(indices, default=-1) + 1:06d}"


def _dataset(group: h5py.Group, name: str, values: np.ndarray, *, images: bool = False) -> None:
    kwargs = {}
    if len(values) > 0:
        kwargs = {
            "compression": "gzip",
            "compression_opts": 4 if images else 1,
            "shuffle": True,
        }
    group.create_dataset(name, data=values, **kwargs)


def append_episode(
    path: str | Path,
    episode: EpisodeBuffer,
    *,
    final_sim_state: np.ndarray,
    success: bool,
) -> str:
    """Append one complete trajectory without exposing a partial top-level group."""
    if len(episode) == 0:
        raise ValueError("Cannot save an empty episode")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "a") as handle:
        handle.attrs["schema_version"] = SCHEMA_VERSION
        handle.attrs["simulator"] = "MuJoCo"
        handle.attrs["environment"] = "robosuite.Lift"
        handle.attrs["num_agents"] = 1

        trajectory_name = _next_trajectory_name(handle)
        temporary_name = f"_writing_{uuid.uuid4().hex}"
        trajectory = handle.create_group(temporary_name)
        trajectory.attrs["complete"] = False
        trajectory.attrs["success"] = bool(success)
        trajectory.attrs["seed"] = int(episode.seed)
        trajectory.attrs["source"] = episode.source
        trajectory.attrs["instruction"] = INSTRUCTION
        trajectory.attrs["role_instruction_panda_0"] = ROLE_INSTRUCTION
        trajectory.attrs["control_frequency_hz"] = CONTROL_FREQUENCY
        trajectory.attrs["action_semantics"] = "delta_eef_xyz_axis_angle_and_gripper"
        trajectory.attrs["action_gripper"] = "+1 close, -1 open"
        trajectory.attrs["image_origin"] = "top_left"
        trajectory.attrs["recording_policy"] = episode.recording_policy
        trajectory.attrs["motion_tail_seconds"] = episode.motion_tail_seconds
        trajectory.attrs["gripper_tail_seconds"] = episode.gripper_tail_seconds

        _dataset(
            trajectory,
            "actions/panda-0",
            np.asarray(episode.actions, dtype=np.float32),
        )
        _dataset(
            trajectory,
            "obs/agent/panda-0/qpos",
            np.asarray(episode.proprio, dtype=np.float32),
        )
        _dataset(
            trajectory,
            f"obs/sensor_data/{GLOBAL_CAMERA}/rgb",
            np.asarray(episode.global_images, dtype=np.uint8),
            images=True,
        )
        _dataset(
            trajectory,
            f"obs/sensor_data/{LOCAL_CAMERA}/rgb",
            np.asarray(episode.local_images, dtype=np.uint8),
            images=True,
        )
        _dataset(
            trajectory,
            "sim/states",
            np.asarray(episode.sim_states, dtype=np.float64),
        )
        trajectory.create_dataset(
            "sim/final_state",
            data=np.asarray(final_sim_state, dtype=np.float64),
        )
        trajectory.create_dataset(
            "timestamps",
            data=np.arange(len(episode), dtype=np.float64) / CONTROL_FREQUENCY,
        )
        trajectory.create_dataset("rewards", data=np.asarray(episode.rewards, dtype=np.float32))
        trajectory.create_dataset("dones", data=np.asarray(episode.dones, dtype=np.bool_))
        trajectory.create_dataset("successes", data=np.asarray(episode.successes, dtype=np.bool_))
        trajectory.create_dataset("task_stage", data=np.asarray(episode.stages, dtype=np.int16))
        trajectory.create_dataset(
            "wall_timestamps", data=np.asarray(episode.wall_timestamps, dtype=np.float64)
        )
        trajectory.create_dataset(
            "capture_reason", data=np.asarray(episode.capture_reasons, dtype=np.uint16)
        )

        trajectory.attrs.modify("complete", True)
        handle.move(temporary_name, trajectory_name)
        handle.flush()
    return trajectory_name


def trajectory_names(handle: h5py.File) -> list[str]:
    return sorted(name for name in handle if name.startswith("trajectory_"))


def validate_dataset(path: str | Path) -> dict:
    """Validate the fields and alignments consumed by the COMMVLA HDF5 adapter."""
    path = Path(path)
    report: dict[str, object] = {
        "path": str(path.resolve()),
        "schema_version": None,
        "trajectories": [],
        "total_steps": 0,
        "successful_trajectories": 0,
    }
    with h5py.File(path, "r") as handle:
        report["schema_version"] = handle.attrs.get("schema_version", "missing")
        names = trajectory_names(handle)
        if not names:
            raise ValueError("Dataset contains no complete trajectories")
        for name in names:
            trajectory = handle[name]
            required = {
                "actions/panda-0": trajectory["actions/panda-0"],
                "obs/agent/panda-0/qpos": trajectory["obs/agent/panda-0/qpos"],
                f"obs/sensor_data/{GLOBAL_CAMERA}/rgb": trajectory[
                    f"obs/sensor_data/{GLOBAL_CAMERA}/rgb"
                ],
                f"obs/sensor_data/{LOCAL_CAMERA}/rgb": trajectory[
                    f"obs/sensor_data/{LOCAL_CAMERA}/rgb"
                ],
                "sim/states": trajectory["sim/states"],
            }
            lengths = {key: int(value.shape[0]) for key, value in required.items()}
            for optional_name in ("wall_timestamps", "capture_reason"):
                if optional_name in trajectory:
                    lengths[optional_name] = int(trajectory[optional_name].shape[0])
            if len(set(lengths.values())) != 1:
                raise ValueError(f"{name} has misaligned lengths: {lengths}")
            steps = next(iter(lengths.values()))
            if required["actions/panda-0"].shape[1:] != (7,):
                raise ValueError(f"{name} actions must have shape [T, 7]")
            if required["obs/agent/panda-0/qpos"].shape[1:] != (9,):
                raise ValueError(f"{name} proprio must have shape [T, 9]")
            for camera in (GLOBAL_CAMERA, LOCAL_CAMERA):
                images = required[f"obs/sensor_data/{camera}/rgb"]
                if len(images.shape) != 4 or images.shape[-1] != 3 or images.dtype != np.uint8:
                    raise ValueError(f"{name} camera {camera} is not uint8 [T,H,W,3]")
            if not np.isfinite(required["actions/panda-0"][:]).all():
                raise ValueError(f"{name} contains non-finite actions")
            success = bool(trajectory.attrs["success"])
            report["trajectories"].append(
                {
                    "name": name,
                    "steps": steps,
                    "success": success,
                    "source": str(trajectory.attrs["source"]),
                    "seed": int(trajectory.attrs["seed"]),
                    "image_shape": list(
                        required[f"obs/sensor_data/{GLOBAL_CAMERA}/rgb"].shape[1:]
                    ),
                    "action_shape": list(required["actions/panda-0"].shape),
                    "proprio_shape": list(required["obs/agent/panda-0/qpos"].shape),
                }
            )
            report["total_steps"] += steps
            report["successful_trajectories"] += int(success)
    return report


def prepare_commvla_assets(h5_path: str | Path, output_directory: str | Path) -> dict:
    """Create the JSON input config and quantile statistics used by COMMVLA."""
    h5_path = Path(h5_path)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    input_config_path = output_directory / "mujoco_lift_input.json"
    statistics_path = output_directory / "mujoco_lift_statistics.npz"

    config = {
        "task_name": "MuJoCoLift-rs",
        "global_instruction": INSTRUCTION,
        "agents": [
            {
                "agent_id": 0,
                "role_instruction": ROLE_INSTRUCTION,
                "local_camera": LOCAL_CAMERA,
            }
        ],
        "cameras": {
            "global": GLOBAL_CAMERA,
            "agents": [LOCAL_CAMERA],
            "known_shared_views": [],
        },
    }
    input_config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    proprio_values = []
    action_values = []
    with h5py.File(h5_path, "r") as handle:
        for name in trajectory_names(handle):
            trajectory = handle[name]
            proprio_values.append(trajectory["obs/agent/panda-0/qpos"][:])
            action_values.append(trajectory["actions/panda-0"][:])
    proprio = np.concatenate(proprio_values, axis=0)
    actions = np.concatenate(action_values, axis=0)
    np.savez(
        statistics_path,
        proprio_low=np.quantile(proprio, 0.01, axis=0)[np.newaxis, :],
        proprio_high=np.quantile(proprio, 0.99, axis=0)[np.newaxis, :],
        action_low=np.quantile(actions, 0.01, axis=0)[np.newaxis, :],
        action_high=np.quantile(actions, 0.99, axis=0)[np.newaxis, :],
    )
    return {
        "h5": str(h5_path.resolve()),
        "input_config": str(input_config_path.resolve()),
        "statistics": str(statistics_path.resolve()),
        "num_agents": 1,
    }
