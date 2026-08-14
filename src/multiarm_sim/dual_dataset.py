"""COMMVLA-compatible recording and recoverable dataset management for two arms."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

import h5py
import numpy as np

from multiarm_sim.envs.handover_box import (
    CONTROL_FREQUENCY,
    GLOBAL_CAMERA,
    LOCAL_CAMERAS,
    frame_from_observation,
    proprio_from_observation,
)

SCHEMA_VERSION = "multiarm-sim-hdf5-v2"
ROLE_INSTRUCTIONS = (
    "Pick up the requested colored cube and hand it to the receiver arm.",
    "Receive the requested colored cube and place it in the matching open box.",
)


@dataclass
class DualArmEpisodeBuffer:
    """Pre-action observations, synchronous actions, and task annotations."""

    seed: int
    source: str
    target_color: str
    instruction: str
    recording_policy: str = "continuous"
    motion_tail_seconds: float = 0.0
    gripper_tail_seconds: float = 0.0
    actions: list[np.ndarray] = field(default_factory=list)
    proprio: list[list[np.ndarray]] = field(default_factory=lambda: [[], []])
    global_images: list[np.ndarray] = field(default_factory=list)
    local_images: list[list[np.ndarray]] = field(default_factory=lambda: [[], []])
    sim_states: list[np.ndarray] = field(default_factory=list)
    rewards: list[float] = field(default_factory=list)
    dones: list[bool] = field(default_factory=list)
    successes: list[bool] = field(default_factory=list)
    stages: list[int] = field(default_factory=list)
    active_arms: list[int] = field(default_factory=list)
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
        stage: int,
        active_arm: int,
        wall_timestamp: float | None = None,
        capture_reason: int = 0,
    ) -> None:
        action = np.asarray(action, dtype=np.float32)
        if action.shape != (14,):
            raise ValueError(f"Dual-Panda action must have shape (14,), got {action.shape}")
        if wall_timestamp is None:
            wall_timestamp = len(self.actions) / CONTROL_FREQUENCY
        self.actions.append(action.copy())
        for robot_index, camera in enumerate(LOCAL_CAMERAS):
            self.proprio[robot_index].append(proprio_from_observation(observation, robot_index))
            self.local_images[robot_index].append(frame_from_observation(observation, camera))
        self.global_images.append(frame_from_observation(observation, GLOBAL_CAMERA))
        self.sim_states.append(np.asarray(sim_state, dtype=np.float64).copy())
        self.rewards.append(float(reward))
        self.dones.append(bool(done))
        self.successes.append(bool(success))
        self.stages.append(int(stage))
        self.active_arms.append(int(active_arm))
        self.wall_timestamps.append(float(wall_timestamp))
        self.capture_reasons.append(int(capture_reason))

    def __len__(self) -> int:
        return len(self.actions)


def _trajectory_names(handle: h5py.File) -> list[str]:
    return sorted(
        name
        for name in handle
        if name.startswith("trajectory_") and name.removeprefix("trajectory_").isdigit()
    )


def _next_trajectory_name(handle: h5py.File) -> str:
    indices = [int(name.removeprefix("trajectory_")) for name in _trajectory_names(handle)]
    return f"trajectory_{max(indices, default=-1) + 1:06d}"


def _dataset(group: h5py.Group, name: str, values: np.ndarray, *, images: bool = False) -> None:
    kwargs = {}
    if len(values):
        kwargs = {
            "compression": "gzip",
            "compression_opts": 4 if images else 1,
            "shuffle": True,
        }
    group.create_dataset(name, data=values, **kwargs)


def append_dual_arm_episode(
    path: str | Path,
    episode: DualArmEpisodeBuffer,
    *,
    final_sim_state: np.ndarray,
    success: bool,
) -> str:
    """Atomically expose a complete two-agent trajectory in the training HDF5."""
    if not len(episode):
        raise ValueError("Cannot save an empty episode")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "a") as handle:
        existing_agents = handle.attrs.get("num_agents")
        if existing_agents is not None and int(existing_agents) != 2:
            raise ValueError(f"{path} already contains a {existing_agents}-agent dataset")
        handle.attrs["schema_version"] = SCHEMA_VERSION
        handle.attrs["simulator"] = "MuJoCo"
        handle.attrs["environment"] = "multiarm_sim.ColoredHandoverBox"
        handle.attrs["num_agents"] = 2

        name = _next_trajectory_name(handle)
        temporary_name = f"_writing_{uuid.uuid4().hex}"
        trajectory = handle.create_group(temporary_name)
        trajectory.attrs["complete"] = False
        trajectory.attrs["success"] = bool(success)
        trajectory.attrs["seed"] = int(episode.seed)
        trajectory.attrs["source"] = episode.source
        trajectory.attrs["target_color"] = episode.target_color
        trajectory.attrs["instruction"] = episode.instruction
        trajectory.attrs["role_instruction_panda_0"] = ROLE_INSTRUCTIONS[0]
        trajectory.attrs["role_instruction_panda_1"] = ROLE_INSTRUCTIONS[1]
        trajectory.attrs["control_frequency_hz"] = CONTROL_FREQUENCY
        trajectory.attrs["action_semantics"] = "delta_eef_xyz_axis_angle_and_gripper"
        trajectory.attrs["action_gripper"] = "+1 close, -1 open"
        trajectory.attrs["image_origin"] = "top_left"
        trajectory.attrs["created_at"] = datetime.now(timezone.utc).isoformat()
        trajectory.attrs["recording_policy"] = episode.recording_policy
        trajectory.attrs["motion_tail_seconds"] = episode.motion_tail_seconds
        trajectory.attrs["gripper_tail_seconds"] = episode.gripper_tail_seconds

        actions = np.asarray(episode.actions, dtype=np.float32)
        for robot_index in range(2):
            _dataset(trajectory, f"actions/panda-{robot_index}", actions[:, robot_index * 7 : (robot_index + 1) * 7])
            _dataset(
                trajectory,
                f"obs/agent/panda-{robot_index}/qpos",
                np.asarray(episode.proprio[robot_index], dtype=np.float32),
            )
            _dataset(
                trajectory,
                f"obs/sensor_data/{LOCAL_CAMERAS[robot_index]}/rgb",
                np.asarray(episode.local_images[robot_index], dtype=np.uint8),
                images=True,
            )
        _dataset(
            trajectory,
            f"obs/sensor_data/{GLOBAL_CAMERA}/rgb",
            np.asarray(episode.global_images, dtype=np.uint8),
            images=True,
        )
        _dataset(trajectory, "sim/states", np.asarray(episode.sim_states, dtype=np.float64))
        trajectory.create_dataset("sim/final_state", data=np.asarray(final_sim_state, dtype=np.float64))
        trajectory.create_dataset(
            "timestamps",
            data=np.arange(len(episode), dtype=np.float64) / CONTROL_FREQUENCY,
        )
        trajectory.create_dataset("rewards", data=np.asarray(episode.rewards, dtype=np.float32))
        trajectory.create_dataset("dones", data=np.asarray(episode.dones, dtype=np.bool_))
        trajectory.create_dataset("successes", data=np.asarray(episode.successes, dtype=np.bool_))
        trajectory.create_dataset("task_stage", data=np.asarray(episode.stages, dtype=np.int16))
        trajectory.create_dataset("active_arm", data=np.asarray(episode.active_arms, dtype=np.int8))
        trajectory.create_dataset(
            "wall_timestamps", data=np.asarray(episode.wall_timestamps, dtype=np.float64)
        )
        trajectory.create_dataset(
            "capture_reason", data=np.asarray(episode.capture_reasons, dtype=np.uint16)
        )

        trajectory.attrs.modify("complete", True)
        handle.move(temporary_name, name)
        handle.flush()
    return name


def list_episodes(path: str | Path) -> list[dict[str, object]]:
    path = Path(path)
    if not path.exists():
        return []
    episodes = []
    with h5py.File(path, "r") as handle:
        for name in reversed(_trajectory_names(handle)):
            trajectory = handle[name]
            episodes.append(
                {
                    "name": name,
                    "steps": int(trajectory["actions/panda-0"].shape[0]),
                    "success": bool(trajectory.attrs.get("success", False)),
                    "target_color": str(trajectory.attrs.get("target_color", "unknown")),
                    "source": str(trajectory.attrs.get("source", "unknown")),
                    "created_at": str(trajectory.attrs.get("created_at", "")),
                }
            )
    return episodes


def combined_episode_frame(path: str | Path, name: str, index: int) -> tuple[np.ndarray, int]:
    """Read one global + two wrist frame triptych for browser review."""
    with h5py.File(path, "r") as handle:
        if name not in _trajectory_names(handle):
            raise KeyError(name)
        trajectory = handle[name]
        total = int(trajectory["actions/panda-0"].shape[0])
        index = min(max(int(index), 0), total - 1)
        images = [
            trajectory[f"obs/sensor_data/{GLOBAL_CAMERA}/rgb"][index],
            trajectory[f"obs/sensor_data/{LOCAL_CAMERAS[0]}/rgb"][index],
            trajectory[f"obs/sensor_data/{LOCAL_CAMERAS[1]}/rgb"][index],
        ]
        return np.concatenate(images, axis=1), total


def trash_path(path: str | Path) -> Path:
    path = Path(path)
    return path.with_name(f"{path.stem}.trash{path.suffix or '.h5'}")


def recoverable_delete(path: str | Path, name: str) -> str:
    """Copy an episode to a sidecar trash HDF5 before removing it from training data."""
    path = Path(path)
    destination = trash_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    trash_name = f"deleted_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    with h5py.File(path, "a") as source, h5py.File(destination, "a") as trash:
        if name not in _trajectory_names(source):
            raise KeyError(name)
        source.copy(name, trash, name=trash_name)
        trash[trash_name].attrs["original_name"] = name
        trash[trash_name].attrs["deleted_at"] = datetime.now(timezone.utc).isoformat()
        trash.flush()
        del source[name]
        source.flush()
    return trash_name


def list_trash(path: str | Path) -> list[dict[str, object]]:
    destination = trash_path(path)
    if not destination.exists():
        return []
    with h5py.File(destination, "r") as handle:
        return [
            {
                "trash_name": name,
                "original_name": str(group.attrs.get("original_name", "")),
                "deleted_at": str(group.attrs.get("deleted_at", "")),
                "steps": int(group["actions/panda-0"].shape[0]),
            }
            for name, group in reversed(list(handle.items()))
        ]


def restore_episode(path: str | Path, trash_name: str) -> str:
    path = Path(path)
    destination = trash_path(path)
    with h5py.File(destination, "a") as trash, h5py.File(path, "a") as target:
        if trash_name not in trash:
            raise KeyError(trash_name)
        preferred = str(trash[trash_name].attrs.get("original_name", ""))
        name = preferred if preferred and preferred not in target else _next_trajectory_name(target)
        trash.copy(trash_name, target, name=name)
        target[name].attrs["restored_at"] = datetime.now(timezone.utc).isoformat()
        target.flush()
        del trash[trash_name]
        trash.flush()
    return name


def validate_dual_arm_dataset(path: str | Path) -> dict[str, object]:
    path = Path(path)
    report: dict[str, object] = {"path": str(path.resolve()), "trajectories": [], "total_steps": 0}
    with h5py.File(path, "r") as handle:
        for name in _trajectory_names(handle):
            trajectory = handle[name]
            required = [
                trajectory[f"actions/panda-{i}"] for i in range(2)
            ] + [
                trajectory[f"obs/agent/panda-{i}/qpos"] for i in range(2)
            ] + [
                trajectory[f"obs/sensor_data/{camera}/rgb"]
                for camera in (GLOBAL_CAMERA, *LOCAL_CAMERAS)
            ] + [trajectory["sim/states"]]
            required += [
                trajectory[name]
                for name in ("wall_timestamps", "capture_reason")
                if name in trajectory
            ]
            lengths = [int(item.shape[0]) for item in required]
            if len(set(lengths)) != 1:
                raise ValueError(f"{name} has misaligned sequence lengths: {lengths}")
            steps = lengths[0]
            for robot_index in range(2):
                if trajectory[f"actions/panda-{robot_index}"].shape[1:] != (7,):
                    raise ValueError(f"{name} panda-{robot_index} action is not [T,7]")
                if trajectory[f"obs/agent/panda-{robot_index}/qpos"].shape[1:] != (9,):
                    raise ValueError(f"{name} panda-{robot_index} proprio is not [T,9]")
            report["trajectories"].append(
                {
                    "name": name,
                    "steps": steps,
                    "success": bool(trajectory.attrs.get("success", False)),
                    "target_color": str(trajectory.attrs.get("target_color", "unknown")),
                }
            )
            report["total_steps"] += steps
    return report


def prepare_dual_commvla_assets(
    h5_path: str | Path,
    output_directory: str | Path,
    *,
    require_success: bool = True,
) -> dict[str, object]:
    """Create the JSON camera/role config and per-agent quantile statistics."""
    h5_path = Path(h5_path)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    config_path = output_directory / "handover_box_input.json"
    statistics_path = output_directory / "handover_box_statistics.npz"

    config = {
        "task_name": "MuJoCoColoredHandoverBox-rs",
        "global_instruction": (
            "Pass the requested colored cube from the sender arm to the receiver arm, "
            "then place it in the matching open box."
        ),
        "agents": [
            {
                "agent_id": index,
                "role_instruction": ROLE_INSTRUCTIONS[index],
                "local_camera": LOCAL_CAMERAS[index],
            }
            for index in range(2)
        ],
        "cameras": {
            "global": GLOBAL_CAMERA,
            "agents": list(LOCAL_CAMERAS),
            "known_shared_views": [],
        },
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    proprio = [[], []]
    actions = [[], []]
    with h5py.File(h5_path, "r") as handle:
        names = _trajectory_names(handle)
        if not names:
            raise ValueError("Dataset contains no trajectories")
        failed = [name for name in names if not bool(handle[name].attrs.get("success", False))]
        if failed and require_success:
            raise ValueError(
                "Training assets require successful demonstrations only; "
                f"move or recollect these failed trajectories: {failed}"
            )
        for name in names:
            trajectory = handle[name]
            for robot_index in range(2):
                proprio[robot_index].append(
                    trajectory[f"obs/agent/panda-{robot_index}/qpos"][:]
                )
                actions[robot_index].append(trajectory[f"actions/panda-{robot_index}"][:])
    proprio_arrays = [np.concatenate(items, axis=0) for items in proprio]
    action_arrays = [np.concatenate(items, axis=0) for items in actions]
    np.savez(
        statistics_path,
        proprio_low=np.stack([np.quantile(values, 0.01, axis=0) for values in proprio_arrays]),
        proprio_high=np.stack([np.quantile(values, 0.99, axis=0) for values in proprio_arrays]),
        action_low=np.stack([np.quantile(values, 0.01, axis=0) for values in action_arrays]),
        action_high=np.stack([np.quantile(values, 0.99, axis=0) for values in action_arrays]),
    )
    return {
        "h5": str(h5_path.resolve()),
        "input_config": str(config_path.resolve()),
        "statistics": str(statistics_path.resolve()),
        "num_agents": 2,
        "trajectories": len(names),
    }
