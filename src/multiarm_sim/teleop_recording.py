"""Pure event-gating policy for human web teleoperation recordings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag


class CaptureReason(IntFlag):
    """Why a control step was retained in an event-gated trajectory."""

    NONE = 0
    MOTION = 1 << 0
    MOTION_TAIL = 1 << 1
    GRIPPER = 1 << 2
    GRIPPER_TAIL = 1 << 3
    STAGE = 1 << 4
    SUCCESS = 1 << 5


@dataclass(frozen=True)
class CaptureDecision:
    capture: bool
    reason: CaptureReason
    idle_steps: int


class EventGatedRecorder:
    """Retain commanded motion and short post-command physics settling windows."""

    def __init__(
        self,
        *,
        control_frequency_hz: int,
        motion_tail_seconds: float = 0.30,
        gripper_tail_seconds: float = 0.50,
    ) -> None:
        if control_frequency_hz <= 0:
            raise ValueError("control_frequency_hz must be positive")
        if motion_tail_seconds < 0 or gripper_tail_seconds < 0:
            raise ValueError("tail durations must be non-negative")
        self.control_frequency_hz = int(control_frequency_hz)
        self.motion_tail_seconds = float(motion_tail_seconds)
        self.gripper_tail_seconds = float(gripper_tail_seconds)
        self.motion_tail_steps = round(self.motion_tail_seconds * self.control_frequency_hz)
        self.gripper_tail_steps = round(self.gripper_tail_seconds * self.control_frequency_hz)
        self._armed = False

    def reset(self, grippers: tuple[bool, ...], stage: int) -> None:
        self._grippers = tuple(bool(value) for value in grippers)
        self._stage = int(stage)
        self._success_seen = False
        self._motion_tail_remaining = 0
        self._gripper_tail_remaining = 0
        self._idle_steps = 0
        self._armed = True

    def decide(
        self,
        *,
        motion_active: bool,
        grippers: tuple[bool, ...],
        stage: int,
        success: bool,
    ) -> CaptureDecision:
        if not self._armed:
            raise RuntimeError("reset() must be called before decide()")

        reason = CaptureReason.NONE
        current_grippers = tuple(bool(value) for value in grippers)
        current_stage = int(stage)

        if motion_active:
            reason |= CaptureReason.MOTION
            self._motion_tail_remaining = self.motion_tail_steps
        elif self._motion_tail_remaining > 0:
            reason |= CaptureReason.MOTION_TAIL
            self._motion_tail_remaining -= 1

        if current_grippers != self._grippers:
            reason |= CaptureReason.GRIPPER
            self._gripper_tail_remaining = self.gripper_tail_steps
        elif self._gripper_tail_remaining > 0:
            reason |= CaptureReason.GRIPPER_TAIL
            self._gripper_tail_remaining -= 1

        if current_stage != self._stage:
            reason |= CaptureReason.STAGE

        if success and not self._success_seen:
            reason |= CaptureReason.SUCCESS

        self._grippers = current_grippers
        self._stage = current_stage
        self._success_seen |= bool(success)

        capture = reason != CaptureReason.NONE
        if not capture:
            self._idle_steps += 1
        return CaptureDecision(capture=capture, reason=reason, idle_steps=self._idle_steps)
