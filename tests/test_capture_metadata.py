import h5py
import numpy as np

from multiarm_sim.dataset import EpisodeBuffer, append_episode, validate_dataset
from multiarm_sim.dual_dataset import (
    DualArmEpisodeBuffer,
    append_dual_arm_episode,
    validate_dual_arm_dataset,
)


def _observation(num_agents: int) -> dict:
    image = np.arange(4 * 4 * 3, dtype=np.uint8).reshape(4, 4, 3)
    observation = {"agentview_image": image}
    for index in range(num_agents):
        observation[f"robot{index}_joint_pos"] = np.arange(7, dtype=np.float32)
        observation[f"robot{index}_gripper_qpos"] = np.array([0.1, -0.1], dtype=np.float32)
        observation[f"robot{index}_eye_in_hand_image"] = image + index
    return observation


def test_single_arm_hdf5_preserves_capture_metadata(tmp_path):
    output = tmp_path / "single.h5"
    episode = EpisodeBuffer(
        seed=11,
        source="human_web_teleop",
        recording_policy="event_gated_20hz",
        motion_tail_seconds=0.30,
        gripper_tail_seconds=0.50,
    )
    for index in range(2):
        episode.append(
            observation=_observation(1),
            sim_state=np.array([index], dtype=np.float64),
            action=np.zeros(7, dtype=np.float32),
            reward=0.0,
            done=False,
            success=False,
            wall_timestamp=1.25 + index * 0.07,
            capture_reason=1 << index,
        )

    name = append_episode(output, episode, final_sim_state=np.array([2.0]), success=False)

    with h5py.File(output, "r") as handle:
        trajectory = handle[name]
        np.testing.assert_allclose(trajectory["wall_timestamps"][:], [1.25, 1.32])
        np.testing.assert_array_equal(trajectory["capture_reason"][:], [1, 2])
        assert trajectory["capture_reason"].dtype == np.dtype("uint16")
        assert trajectory.attrs["recording_policy"] == "event_gated_20hz"
        assert trajectory.attrs["motion_tail_seconds"] == 0.30
        assert trajectory.attrs["gripper_tail_seconds"] == 0.50
    assert validate_dataset(output)["total_steps"] == 2


def test_dual_arm_hdf5_preserves_aligned_capture_metadata(tmp_path):
    output = tmp_path / "dual.h5"
    episode = DualArmEpisodeBuffer(
        seed=12,
        source="human_web_teleop",
        target_color="red",
        instruction="handover red",
        recording_policy="event_gated_20hz",
        motion_tail_seconds=0.30,
        gripper_tail_seconds=0.50,
    )
    episode.append(
        observation=_observation(2),
        sim_state=np.array([0.0, 1.0]),
        action=np.zeros(14, dtype=np.float32),
        reward=0.0,
        done=False,
        success=False,
        stage=1,
        active_arm=1,
        wall_timestamp=0.4,
        capture_reason=20,
    )

    name = append_dual_arm_episode(
        output,
        episode,
        final_sim_state=np.array([2.0, 3.0]),
        success=False,
    )

    with h5py.File(output, "r") as handle:
        trajectory = handle[name]
        assert trajectory["wall_timestamps"].shape == (1,)
        assert trajectory["capture_reason"].shape == (1,)
        assert trajectory["actions/panda-0"].shape[0] == 1
        assert trajectory["actions/panda-1"].shape[0] == 1
    assert validate_dual_arm_dataset(output)["total_steps"] == 1


def test_legacy_append_defaults_to_uniform_wall_time(tmp_path):
    output = tmp_path / "legacy-compatible.h5"
    episode = EpisodeBuffer(seed=13, source="scripted_oracle")
    episode.append(
        observation=_observation(1),
        sim_state=np.array([0.0]),
        action=np.zeros(7, dtype=np.float32),
        reward=0.0,
        done=False,
        success=False,
    )

    name = append_episode(output, episode, final_sim_state=np.array([1.0]), success=False)

    with h5py.File(output, "r") as handle:
        trajectory = handle[name]
        assert trajectory.attrs["recording_policy"] == "continuous"
        np.testing.assert_allclose(trajectory["wall_timestamps"][:], [0.0])
        np.testing.assert_array_equal(trajectory["capture_reason"][:], [0])
