import h5py
import numpy as np

from multiarm_sim.dual_dataset import (
    DualArmEpisodeBuffer,
    append_dual_arm_episode,
    validate_dual_arm_dataset,
)
from multiarm_sim.teleop_recording import EventGatedRecorder


def _observation(step: int) -> dict:
    image = np.full((8, 8, 3), step, dtype=np.uint8)
    result = {"agentview_image": image}
    for agent in range(2):
        result[f"robot{agent}_joint_pos"] = np.full(7, step + agent, dtype=np.float32)
        result[f"robot{agent}_gripper_qpos"] = np.full(2, agent, dtype=np.float32)
        result[f"robot{agent}_eye_in_hand_image"] = image + agent
    return result


def test_event_gate_produces_a_commvla_aligned_dual_arm_trajectory(tmp_path):
    gate = EventGatedRecorder(
        control_frequency_hz=20,
        motion_tail_seconds=0.30,
        gripper_tail_seconds=0.50,
    )
    gate.reset((False, False), stage=0)
    episode = DualArmEpisodeBuffer(
        seed=44,
        source="human_web_teleop",
        target_color="green",
        instruction="handover green",
        recording_policy="event_gated_20hz",
        motion_tail_seconds=0.30,
        gripper_tail_seconds=0.50,
    )
    events = [
        (False, (False, False)),
        (True, (False, False)),
        (False, (False, False)),
        (False, (False, True)),
    ] + [(False, (False, True))] * 11

    for simulation_step, (motion, grippers) in enumerate(events):
        decision = gate.decide(
            motion_active=motion,
            grippers=grippers,
            stage=0,
            success=False,
        )
        if not decision.capture:
            continue
        episode.append(
            observation=_observation(simulation_step),
            sim_state=np.array([simulation_step], dtype=np.float64),
            action=np.zeros(14, dtype=np.float32),
            reward=0.0,
            done=False,
            success=False,
            stage=0,
            active_arm=1,
            wall_timestamp=simulation_step / 20.0,
            capture_reason=int(decision.reason),
        )

    output = tmp_path / "event-gated-dual.h5"
    name = append_dual_arm_episode(
        output,
        episode,
        final_sim_state=np.array([99.0]),
        success=False,
    )
    report = validate_dual_arm_dataset(output)

    assert report["total_steps"] == len(episode) == 13
    with h5py.File(output, "r") as handle:
        trajectory = handle[name]
        lengths = {
            trajectory["actions/panda-0"].shape[0],
            trajectory["actions/panda-1"].shape[0],
            trajectory["obs/agent/panda-0/qpos"].shape[0],
            trajectory["obs/agent/panda-1/qpos"].shape[0],
            trajectory["obs/sensor_data/agentview/rgb"].shape[0],
            trajectory["wall_timestamps"].shape[0],
            trajectory["capture_reason"].shape[0],
        }
        assert lengths == {13}
        assert trajectory["wall_timestamps"][-1] > trajectory["timestamps"][-1]
