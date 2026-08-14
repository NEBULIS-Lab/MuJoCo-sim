# Restore Panda Wrist Camera Design

Date: 2026-08-14

## Objective

Restore the dual-arm handover task to robosuite's built-in Panda
`eye_in_hand` camera configuration. The wrist views are local manipulation aids;
operators use the global camera for workspace-level positioning. It is acceptable for
the wrist views to contain substantial blank tabletop.

## Root Cause

The image resolution increase from 256 to 512 pixels did not change camera framing.
The framing changed because the handover environment began overriding each Panda wrist
camera's local quaternion and field of view. That custom forward/down transform makes
the sender initially look toward the boxes and the receiver initially look toward the
cubes, which does not match the operator's expected original wrist view.

## Accepted Design

The handover environment will leave each Panda robot model's existing
`eye_in_hand` camera element untouched. It will not set custom wrist camera position,
quaternion, or field of view values. The effective configuration therefore comes from
the installed robosuite Panda MJCF rather than duplicated task-specific constants.

The collection render size remains 512 by 512 pixels per camera. Resolution controls
image detail only; retaining it preserves clearer raw data without changing the native
camera framing. JPEG quality, live polling rate, event-gated recording, HDF5 layout,
global camera configuration, and the current web-page camera arrangement remain
unchanged.

## Code Changes

Remove the custom wrist-camera constants and the per-robot XML mutations from
`src/multiarm_sim/envs/handover_box.py`. Keep the existing logical mapping:

- sender: `robot0_eye_in_hand`;
- receiver: `robot1_eye_in_hand`.

No migration is required for existing HDF5 files. New trajectories will contain images
from the restored native cameras; previously recorded trajectories remain unchanged.

## Verification

Add a runtime regression test that constructs the handover environment and verifies
both wrist cameras use the installed Panda MJCF local position, quaternion, and 75-degree
field of view. The expected values are read from the robosuite Panda model behavior and
checked on the assembled MuJoCo model, so a future accidental task-level override fails
the test.

Render a fresh EGL global/sender/receiver sample at 512 pixels and inspect both wrist
views for the original native framing, including visible gripper fingers and permissible
blank tabletop. Then run the camera-focused tests, the complete EGL test suite, and a
Python syntax check.

## Non-goals

- Do not reduce the default image resolution to 256 pixels.
- Do not design new task-specific wrist camera poses.
- Do not swap sender and receiver streams.
- Do not change the global camera, UI sizing, recording semantics, or dataset schema.
