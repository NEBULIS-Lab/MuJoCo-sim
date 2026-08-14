# Event-gated teleoperation and visual-quality design

Date: 2026-08-14

## Objective

Improve the current single-operator web teleoperation workflow before collecting
pilot dual-arm handover data. Keep the MuJoCo / robosuite environment at 20 Hz,
avoid recording long periods of operator hesitation, preserve physically meaningful
settling and handover states, and make the three camera views clear enough for both
human operation and later VLA experiments.

This change is limited to the existing single-arm Lift and dual-arm ColoredHandoverBox
workflow. Three-arm and four-arm tasks are out of scope until the dual-arm data pipeline
has passed an end-to-end validation.

## Recording semantics

The environment continues stepping at 20 Hz regardless of whether a sample is saved.
While a trajectory is active, a step is appended to the episode buffer when any of the
following conditions is true:

1. A motion or rotation key is held.
2. A gripper command has just changed.
3. The recorder is within a configurable post-input tail window.
4. The recorder is within a configurable post-gripper tail window.
5. A task event requires preservation, including task-stage change or first success.

Default tail windows are:

- Motion release: 0.30 seconds, or 6 control steps at 20 Hz.
- Gripper toggle: 0.50 seconds, or 10 control steps at 20 Hz.

The first saved step in a burst uses the observation and simulator state immediately
before the corresponding action. Each burst therefore retains the transition from the
current state into the commanded motion. Both agents remain synchronized: if either
arm causes a sample to be saved, actions, proprioception and images for both arms are
saved at that same index.

Idle gaps are intentionally compressed out of the model-time trajectory. The dataset
stores wall-clock timestamps separately so the original operator timing remains
auditable. The uniformly sampled model timestamp remains based on 20 Hz over retained
steps. This avoids presenting irregularly spaced action tensors to the current COMMVLA
loader while retaining evidence about omitted waiting time.

Each retained step records a compact reason bit mask covering motion input, gripper
tail, motion tail, stage transition and success. Each trajectory records the recording
policy name and tail-window configuration as HDF5 metadata.

## User-interface behavior

`Start new trajectory` still resets the task and arms the recorder. The UI distinguishes:

- armed but idle: the trajectory exists, but no new sample is currently being appended;
- actively capturing: input or a tail/event condition is causing 20 Hz samples to be saved;
- pending review: recording has ended and the retained trajectory can be reviewed.

The step counter reports saved steps, not simulation steps. A second status value reports
compressed idle time so the operator can see that the system is responsive even when the
saved-step counter is stationary.

Finishing an armed trajectory with no retained steps produces a clear message and does
not create an empty pending trajectory. Discard, review, save, recoverable delete and
restore retain their current behavior.

## Camera and web-display design

The default collection render size increases from 256 to 512 pixels per camera. The
command-line `--image-size` option remains available so lower resolutions can be used
for diagnostics.

The global handover camera is moved closer and its vertical field of view is narrowed
from 68 degrees to approximately 52 degrees, while ensuring both Panda arms, all colored
cubes, all open boxes and the shared handover region remain visible throughout the task.
The exact pose is accepted only after an off-screen render test confirms this coverage.

Wrist cameras are calibrated to look forward and slightly downward from each gripper so
that the active cube and handover region can enter the frame during normal operation.
The implementation should use existing robosuite robot-camera elements rather than add
new duplicate cameras unless the built-in camera transforms cannot meet the coverage
requirement.

The web page presents the global view as the primary large image, with the sender and
receiver wrist views below it. Live JPEG quality increases from 86 to 92. Live-view
polling targets 10 FPS independently from the 20 Hz environment loop; failure to reach
10 FPS must not slow simulation or alter saved timestamps.

High-resolution images are stored in the raw pilot dataset. COMMVLA conversion or
training preprocessing performs any resize required by the model, rather than reducing
information during capture.

## Data flow and compatibility

The raw HDF5 schema remains compatible with the current COMMVLA adapter:

- each retained index has synchronized actions, states and camera images;
- actions retain the existing delta end-effector plus gripper semantics;
- `control_frequency_hz` remains 20;
- existing required groups and attributes retain their names.

New optional datasets and attributes provide wall-clock timing, capture reasons and
recording-policy metadata. The COMMVLA adapter may ignore these fields, so this change
does not modify the reference COMMVLA repository.

Existing HDF5 files remain readable and are never rewritten in place. The new recorder
only adds the optional metadata to newly captured trajectories.

## Failure handling

- Browser input heartbeat expiry clears held motion keys, preventing a stuck command.
- A gripper toggle is latched and receives its full tail even if the keyboard event is
  brief.
- If rendering or JPEG encoding is slow, the live viewer may drop visual updates; data
  capture remains governed by the environment loop.
- If a non-idle physics change occurs after a tail ends, it is not silently represented
  as an adjacent 20 Hz transition. Pilot validation must check dropped objects and
  contact settling; tail durations are adjusted if such gaps are observed.
- Dataset writes remain atomic at trajectory confirmation, as in the current recorder.

## Verification and pilot acceptance

Automated checks cover:

1. no input produces no saved steps after the recorder is armed;
2. motion input saves at 20 Hz while active and for six steps after release;
3. a gripper toggle saves ten settling steps;
4. either arm triggers synchronized two-agent samples;
5. capture-reason, wall-time, action, state and image arrays have identical length;
6. legacy files without the new optional fields remain valid;
7. the web command lifecycle still supports start, finish, discard, confirm, replay,
   recoverable delete and restore;
8. camera renders have the requested shape and contain the task workspace.

After automated verification, collect 10 to 20 dual-arm pilot trajectories. The pilot is
accepted when several full handover successes can be saved and replayed, HDF5 validation
passes, COMMVLA preparation succeeds, a COMMVLA batch can be loaded, and a short training
smoke run completes forward and backward computation. Policy quality is not an acceptance
criterion for this small pilot.

Only after this pilot passes should the project define a generic N-agent task API and
design the first three-arm task. Four-arm work follows after the three-arm schema and UI
have demonstrated that they do not depend on two-arm-specific assumptions.
