# Event-gated Teleoperation and Visual Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 20 Hz event-gated web recorder that omits stable operator hesitation, preserves motion and gripper settling, records auditable timing metadata, and presents useful high-resolution global and wrist views.

**Architecture:** Put capture decisions in a pure, independently tested `EventGatedRecorder`; keep environment stepping and HDF5 model time at 20 Hz while only appending decisions marked for capture. Extend both episode buffers with optional timing/reason metadata, then integrate the gate and independent camera JPEG endpoints into the existing web console. Camera transforms remain part of the existing robosuite environment so collection, review and replay see the same views.

**Tech Stack:** Python 3.10, NumPy, h5py, robosuite, MuJoCo EGL, OpenCV, standard-library HTTP server, pytest.

## Global Constraints

- Keep MuJoCo / robosuite control frequency at exactly 20 Hz.
- Default motion-release tail is 0.30 seconds (6 retained 20 Hz steps).
- Default gripper tail is 0.50 seconds (10 retained 20 Hz steps).
- Keep actions as delta end-effector XYZ, axis-angle rotation and gripper command.
- Never modify `/data/private/user7/projects/chenglong-2026-INFOCOM-code-CommVLA`.
- Existing HDF5 files must remain readable and must not be rewritten.
- New optional HDF5 fields must not break the existing COMMVLA adapter.
- Default collection resolution is 512 x 512 per camera; `--image-size` remains configurable.
- The project directory is not a Git repository, so task checkpoints use test results instead of commits.

---

### Task 1: Pure event-gated capture policy

**Files:**
- Create: `src/multiarm_sim/teleop_recording.py`
- Create: `tests/test_teleop_recording.py`

**Interfaces:**
- Produces: `CaptureReason(IntFlag)`, `CaptureDecision`, and `EventGatedRecorder`.
- `EventGatedRecorder.reset(grippers: tuple[bool, ...], stage: int) -> None` arms a clean episode state.
- `EventGatedRecorder.decide(*, motion_active: bool, grippers: tuple[bool, ...], stage: int, success: bool) -> CaptureDecision` returns `capture`, integer `reason`, and cumulative `idle_steps`.

- [x] **Step 1: Write failing policy tests**

Add tests proving that idle steps are skipped, active motion is retained, release creates exactly six tail steps, a gripper transition creates one event step plus ten settling steps, stage transitions are retained once, first success is retained once, and a second arm's gripper can trigger the same recorder.

```python
def test_motion_release_has_six_tail_steps():
    gate = EventGatedRecorder(control_frequency_hz=20, motion_tail_seconds=0.30)
    gate.reset((False, False), stage=0)
    assert gate.decide(motion_active=True, grippers=(False, False), stage=0, success=False).capture
    tail = [gate.decide(motion_active=False, grippers=(False, False), stage=0, success=False).capture for _ in range(7)]
    assert tail == [True] * 6 + [False]
```

- [x] **Step 2: Run the tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_teleop_recording.py -q`

Expected: import failure because `multiarm_sim.teleop_recording` does not exist.

- [x] **Step 3: Implement the capture policy**

Use an `IntFlag` with `MOTION`, `MOTION_TAIL`, `GRIPPER`, `GRIPPER_TAIL`, `STAGE`, and `SUCCESS`. Convert seconds to steps with `round(seconds * control_frequency_hz)`. Refresh the motion tail on every active motion step, latch the gripper tail on a gripper-state transition, and increment `idle_steps` only when no reason is present.

- [x] **Step 4: Run the policy tests**

Run: `.venv/bin/python -m pytest tests/test_teleop_recording.py -q`

Expected: all policy tests pass.

### Task 2: Optional capture metadata in both HDF5 buffers

**Files:**
- Modify: `src/multiarm_sim/dataset.py`
- Modify: `src/multiarm_sim/dual_dataset.py`
- Create: `tests/test_capture_metadata.py`

**Interfaces:**
- `EpisodeBuffer.append(...)` and `DualArmEpisodeBuffer.append(...)` gain keyword arguments `wall_timestamp: float | None = None` and `capture_reason: int = 0`.
- Both buffers expose aligned `wall_timestamps` and `capture_reasons` lists.
- Buffers gain metadata fields `recording_policy`, `motion_tail_seconds`, and `gripper_tail_seconds`, defaulting to continuous/zero for legacy and scripted callers.
- HDF5 output gains optional `wall_timestamps` and `capture_reason` datasets plus corresponding policy attributes.

- [x] **Step 1: Write failing buffer and HDF5 tests**

Construct minimal single- and dual-arm buffers with synthetic observations, append two samples, write temporary HDF5 files, and assert:

```python
assert trajectory["wall_timestamps"].shape == (2,)
assert trajectory["capture_reason"].dtype == np.uint16
assert trajectory.attrs["recording_policy"] == "event_gated_20hz"
assert trajectory.attrs["motion_tail_seconds"] == 0.30
assert trajectory.attrs["gripper_tail_seconds"] == 0.50
```

Also run the current validators against a legacy fixture without these optional fields.

- [x] **Step 2: Run the metadata tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_capture_metadata.py -q`

Expected: constructor/append signatures do not accept the new metadata.

- [x] **Step 3: Implement aligned optional metadata**

When `wall_timestamp` is omitted, use `len(actions) / CONTROL_FREQUENCY` before appending so existing scripted callers remain deterministic. Write capture reasons as `uint16`, wall timestamps as `float64`, and policy configuration as trajectory attributes. Extend validation so optional arrays, when present, must match action length.

- [x] **Step 4: Run metadata and legacy validation tests**

Run: `.venv/bin/python -m pytest tests/test_capture_metadata.py -q`

Expected: all metadata and compatibility tests pass.

### Task 3: Integrate event gating and truthful status into the web recorder

**Files:**
- Modify: `scripts/teleop_web.py`
- Create: `tests/test_teleop_web_helpers.py`

**Interfaces:**
- Add CLI flags `--motion-tail-seconds` (default `0.30`), `--gripper-tail-seconds` (default `0.50`), and default `--image-size 512`.
- Add a pure input snapshot helper returning effective non-stale keys, active arm, stage and gripper tuple under one lock.
- Status JSON gains `capturing`, `idle_steps`, `idle_seconds`, and `recording_policy`.

- [x] **Step 1: Write failing helper and CLI tests**

Test that stale inputs clear motion keys, motion-key classification excludes arm/stage selectors, default arguments equal the approved values, and event-gated buffer creation carries policy configuration.

- [x] **Step 2: Run the web helper tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_teleop_web_helpers.py -q`

Expected: new helper/status fields and CLI defaults are missing.

- [x] **Step 3: Integrate one gate per armed trajectory**

On `start`, clear held keys, create/reset `EventGatedRecorder`, store the monotonic episode origin, and set `recording=True`, `capturing=False`. At each 20 Hz loop, take one consistent input snapshot, compute the action, step the environment, ask the gate for a decision, and only append when `decision.capture` is true. Pass `time.monotonic() - episode_origin` and `decision.reason` into the buffer.

On first success, preserve the success sample and transition to pending review. Apply the retained-step maximum only to appended samples. `finish` with an empty buffer returns an explanatory message and leaves no pending episode.

- [x] **Step 4: Update the browser status language**

Display `已就绪，等待输入` while armed/idle, `正在采集有效动作` while capturing, retained step count, and compressed idle duration. Keep review/save/discard/delete/restore behavior unchanged.

- [x] **Step 5: Run helper tests and a no-GPU import check**

Run: `.venv/bin/python -m pytest tests/test_teleop_web_helpers.py -q`

Run: `.venv/bin/python scripts/teleop_web.py --help`

Expected: tests pass and the help output lists the new options without constructing MuJoCo.

### Task 4: Improve camera coverage and split live views

**Files:**
- Modify: `src/multiarm_sim/envs/handover_box.py`
- Modify: `scripts/teleop_web.py`
- Create: `tests/test_camera_configuration.py`

**Interfaces:**
- The global `agentview` camera uses a closer pose and 52-degree vertical field of view.
- Both prefixed `eye_in_hand` XML cameras use an explicit forward/down transform and narrower useful field of view.
- `/api/frame?camera=global|sender|receiver` serves separate JPEGs.
- The browser uses one large global image and two smaller wrist images.

- [x] **Step 1: Write failing static camera and HTML tests**

Assert that environment constants define the approved global field of view, that `_load_model` updates both robot-prefixed wrist camera elements, that JPEG quality is 92, that the default image size is 512, and that the HTML contains three live image elements.

- [x] **Step 2: Run static tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_camera_configuration.py -q`

Expected: current 68-degree global view, quality 86 and single combined image fail assertions.

- [x] **Step 3: Implement camera transforms and separate endpoints**

Set the global camera through named constants. Before `ManipulationTask` assembly, update each robot model's prefixed `eye_in_hand` camera XML `pos`, `quat`, and `fovy`. Store live JPEGs by logical camera name in `AppState`; throttle refresh generation to at most 10 Hz and allow the browser to fetch each stream independently.

- [x] **Step 4: Implement the responsive camera layout**

Use a primary global `<img>` followed by a two-column wrist grid that becomes one column on narrow screens. Do not upscale wrist views beyond their natural aspect ratio. Retain the current combined review frame so saved-trajectory review remains synchronized.

- [x] **Step 5: Render and inspect an EGL camera contact sheet**

Run a small off-screen rendering script on an available EGL device at 512 pixels, save a temporary global/sender/receiver contact sheet, and visually verify that the global view includes both arms, cubes, boxes and handover area. Verify both wrist views point forward/down and contain table workspace rather than only a blank horizon.

- [x] **Step 6: Run camera tests**

Run: `.venv/bin/python -m pytest tests/test_camera_configuration.py -q`

Expected: all camera configuration and layout tests pass.

### Task 5: End-to-end recorder verification and operator documentation

**Files:**
- Modify: `docs/handover-box-and-web-console.md`
- Modify: `README.md`
- Create: `tests/test_event_gated_hdf5_integration.py`

**Interfaces:**
- Documentation provides the final server command, Mac tunnel command, status meanings and pilot checklist.
- Integration test produces a temporary dual-arm HDF5 trajectory using event-gated decisions and validates it with the existing dataset validator.

- [x] **Step 1: Write and run the failing integration test**

The test must simulate idle, motion, release tail and gripper tail decisions, append only retained steps to a synthetic dual buffer, save it, and assert equal lengths for all action/state/image/timing/reason arrays plus successful `validate_dual_arm_dataset` output.

Run: `.venv/bin/python -m pytest tests/test_event_gated_hdf5_integration.py -q`

Expected: fail before all integration points are complete.

- [x] **Step 2: Complete integration fixes and run the full suite**

Run: `.venv/bin/python -m pytest -q`

Expected: all tests pass.

- [x] **Step 3: Run project runtime and environment smoke checks**

Run: `.venv/bin/python scripts/check_runtime.py --backend egl --egl-device 6`

Run a one-reset, one-action `ColoredHandoverBox` smoke script at 512 pixels on the selected free EGL device.

Expected: runtime imports succeed, RGB arrays have correct shapes, and no MuJoCo/OpenGL error occurs.

- [x] **Step 4: Update operator documentation**

Document that the saved-step counter pauses during stable idle, control remains 20 Hz, motion release records 0.30 seconds, gripper changes record 0.50 seconds, and the three views refresh independently. Include commands that first select a free GPU with `nvidia-smi`, start the server, open an SSH tunnel from the Mac, and browse to `http://127.0.0.1:8765`.

- [x] **Step 5: Final non-destructive verification**

Run `.venv/bin/python -m pytest -q`, inspect `git diff` only if the directory later becomes a repository, list changed files explicitly, and verify `/data/private/user7/projects/chenglong-2026-INFOCOM-code-CommVLA` was not modified.
