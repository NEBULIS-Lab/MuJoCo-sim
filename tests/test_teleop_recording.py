from multiarm_sim.teleop_recording import CaptureReason, EventGatedRecorder


def _decide(gate, *, motion=False, grippers=(False, False), stage=0, success=False):
    return gate.decide(
        motion_active=motion,
        grippers=grippers,
        stage=stage,
        success=success,
    )


def test_idle_steps_are_not_captured_and_are_counted():
    gate = EventGatedRecorder(control_frequency_hz=20)
    gate.reset((False, False), stage=0)

    first = _decide(gate)
    second = _decide(gate)

    assert not first.capture
    assert second.idle_steps == 2


def test_motion_release_has_exactly_six_tail_steps():
    gate = EventGatedRecorder(control_frequency_hz=20, motion_tail_seconds=0.30)
    gate.reset((False, False), stage=0)

    active = _decide(gate, motion=True)
    tail = [_decide(gate) for _ in range(7)]

    assert active.reason & CaptureReason.MOTION
    assert [decision.capture for decision in tail] == [True] * 6 + [False]
    assert all(decision.reason & CaptureReason.MOTION_TAIL for decision in tail[:6])


def test_gripper_change_has_event_plus_ten_settling_steps():
    gate = EventGatedRecorder(control_frequency_hz=20, gripper_tail_seconds=0.50)
    gate.reset((False, False), stage=0)

    changed = _decide(gate, grippers=(False, True))
    tail = [_decide(gate, grippers=(False, True)) for _ in range(11)]

    assert changed.reason & CaptureReason.GRIPPER
    assert [decision.capture for decision in tail] == [True] * 10 + [False]
    assert all(decision.reason & CaptureReason.GRIPPER_TAIL for decision in tail[:10])


def test_stage_transition_and_first_success_are_one_shot_events():
    gate = EventGatedRecorder(control_frequency_hz=20)
    gate.reset((False, False), stage=0)

    stage_change = _decide(gate, stage=1)
    same_stage = _decide(gate, stage=1)
    first_success = _decide(gate, stage=1, success=True)
    repeated_success = _decide(gate, stage=1, success=True)

    assert stage_change.reason == CaptureReason.STAGE
    assert not same_stage.capture
    assert first_success.reason == CaptureReason.SUCCESS
    assert not repeated_success.capture


def test_motion_and_gripper_reasons_can_coexist():
    gate = EventGatedRecorder(control_frequency_hz=20)
    gate.reset((False,), stage=0)

    decision = _decide(gate, motion=True, grippers=(True,))

    assert decision.capture
    assert decision.reason & CaptureReason.MOTION
    assert decision.reason & CaptureReason.GRIPPER
