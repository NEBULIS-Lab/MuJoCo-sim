from pathlib import Path

from scripts import teleop_web


class _DualEnv:
    target_color = "blue"
    instruction = "handover blue"


def test_cli_defaults_match_event_gated_collection_design():
    args = teleop_web.parse_args([])

    assert args.image_size == 512
    assert args.motion_tail_seconds == 0.30
    assert args.gripper_tail_seconds == 0.50


def test_input_snapshot_clears_stale_motion_keys(tmp_path):
    state = teleop_web.AppState(Path(tmp_path))
    state.keys = {"w", "r"}
    state.active_arm = 1
    state.stage = 2
    state.grippers = [True, False]
    state.last_input = 10.0

    snapshot = teleop_web._input_snapshot(state, "handover_box", now=11.0)

    assert snapshot.keys == frozenset()
    assert not snapshot.motion_active
    assert snapshot.active_arm == 1
    assert snapshot.stage == 2
    assert snapshot.grippers == (True, False)


def test_only_motion_and_rotation_keys_activate_capture(tmp_path):
    state = teleop_web.AppState(Path(tmp_path))
    state.last_input = 10.0
    state.keys = {"1", "tab"}
    assert not teleop_web._input_snapshot(state, "handover_box", now=10.1).motion_active

    state.keys = {"j"}
    assert teleop_web._input_snapshot(state, "handover_box", now=10.1).motion_active


def test_new_dual_buffer_is_marked_event_gated():
    buffer = teleop_web._new_buffer(
        "handover_box",
        _DualEnv(),
        seed=31,
        motion_tail_seconds=0.30,
        gripper_tail_seconds=0.50,
    )

    assert buffer.recording_policy == "event_gated_20hz"
    assert buffer.motion_tail_seconds == 0.30
    assert buffer.gripper_tail_seconds == 0.50


def test_live_frames_are_throttled_to_ten_hz():
    assert not teleop_web._live_frame_due(now=5.099, last_encoded=5.0, target_hz=10.0)
    assert teleop_web._live_frame_due(now=5.100, last_encoded=5.0, target_hz=10.0)
