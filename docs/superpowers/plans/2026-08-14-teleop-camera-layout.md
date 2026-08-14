# Teleoperation Camera Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebalance the web task window into a 60/40 global-versus-wrist camera row and move trajectory management below it.

**Architecture:** Change only the embedded HTML and CSS in `scripts/teleop_web.py`. Preserve every existing element ID and JavaScript endpoint while replacing the outer two-column task/aside layout with a camera grid and a separate lower data-management grid.

**Tech Stack:** HTML5, CSS Grid, standard-library Python HTTP server, pytest.

## Global Constraints

- Do not change simulation, camera rendering, polling, JPEG, recording or HDF5 behavior.
- Desktop camera layout is 60% global view and 40% vertically stacked wrist views.
- Pending review spans the full lower row; saved episodes and trash use two columns below it.
- Below 850 pixels, cameras and saved/trash panels become one column.
- Preserve all existing DOM IDs and JavaScript behavior.
- On desktop, the complete right wrist column must end at the same height as the left
  global-camera column.
- Wrist images must use proportional contain rendering without cropping or distortion.
- The directory is not a Git repository, so verification replaces commit steps.

---

### Task 1: Responsive task and data-management layout

**Files:**
- Modify: `scripts/teleop_web.py`
- Modify: `tests/test_camera_configuration.py`

**Interfaces:**
- Consumes: existing `HTML`, `create_handler(state)`, and the DOM IDs used by the current JavaScript.
- Produces: `cameraLayout`, `wristColumn`, and `dataManagement` semantic containers without changing HTTP routes.

- [x] **Step 1: Add a failing HTTP-rendered DOM test**

Extend the real HTTP response test to parse the served HTML and assert that:

```python
assert 'id="cameraLayout"' in html
assert 'id="wristColumn"' in html
assert 'id="dataManagement"' in html
assert html.index('id="globalFrame"') < html.index('id="wristColumn"')
assert html.index('id="dataManagement"') > html.index('id="dualControls"')
```

Also assert that `pendingPanel`, `episodes`, `trash`, `globalFrame`, `senderFrame`, and
`receiverFrame` remain present.

- [x] **Step 2: Run the targeted test and verify it fails**

Run: `.venv/bin/python -m pytest tests/test_camera_configuration.py::test_web_console_uses_camera_row_and_lower_data_management -q`

Expected: FAIL because the three new semantic containers do not exist.

- [x] **Step 3: Implement the 60/40 desktop layout**

Replace `.layout`, `.wrist-grid`, the nested task `<div>` and `<aside>` with:

```html
<div class="task-stack">
  <div class="panel task-panel">
    <div id="cameraLayout" class="camera-layout">
      <div class="global-camera">...</div>
      <div id="wristColumn" class="wrist-column">...</div>
    </div>
    ...existing controls and instructions...
  </div>
  <section id="dataManagement" class="data-management">
    ...pending review...
    <div class="dataset-grid">...saved...trash...</div>
  </section>
</div>
```

Use `grid-template-columns:minmax(0,3fr) minmax(300px,2fr)` for the camera row,
`grid-template-columns:1fr 1fr` for saved/trash, and one-column media rules below
850 pixels. Keep the receiver camera hide/show logic unchanged.

- [x] **Step 4: Run targeted and full regression tests**

Run: `.venv/bin/python -m pytest tests/test_camera_configuration.py -q`

Run: `MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=6 .venv/bin/python -m pytest -q`

Expected: all tests pass.

- [x] **Step 5: Verify the served page structure**

Start the web server on a temporary port and request `/`. Confirm the three new
containers and all existing control/review IDs are present, with no API or status error.

### Task 2: Equal-height uncropped wrist column

**Files:**
- Modify: `scripts/teleop_web.py`
- Modify: `tests/test_camera_configuration.py`

**Interfaces:**
- Consumes: `cameraLayout`, `globalFrame`, `wristColumn`, `senderFrame`,
  `receiverCamera`, `receiverFrame`, and `choose(task)` from Task 1.
- Produces: `wristColumnSlot` as a non-size-contributing grid slot and the
  `single-wrist` class for the single-arm layout.

- [x] **Step 1: Add a failing served-page contract test**

Extend the real HTTP HTML test with hand-derived requirements:

```python
assert 'id="wristColumnSlot"' in html
assert "object-fit:contain" in html
assert "grid-template-rows:repeat(2,minmax(0,1fr))" in html
assert "wristColumn').classList.toggle('single-wrist'" in html
```

The test catches regressions where the right column contributes two square intrinsic
heights, crops a wrist image, or leaves a single-arm task in a half-height row.

- [x] **Step 2: Run the targeted test and verify it fails**

Run: `.venv/bin/python -m pytest tests/test_camera_configuration.py::test_web_console_matches_wrist_height_without_cropping -q`

Expected: FAIL because `wristColumnSlot` and the equal-height rules do not exist.

- [x] **Step 3: Implement the desktop equal-height slot**

Wrap the wrist column in:

```html
<div id="wristColumnSlot" class="wrist-column-slot">
  <div id="wristColumn" class="wrist-column">...</div>
</div>
```

Use an in-flow relative slot with an absolutely positioned wrist column so only the
global camera contributes intrinsic row height. Divide the absolute column into two
`minmax(0,1fr)` rows. Give each wrist view an auto-height title row and a flexible image
row; render each image with `width:100%`, `height:100%`, and `object-fit:contain`.

- [x] **Step 4: Preserve single-arm and narrow-screen behavior**

In `choose(task)`, toggle `single-wrist` on `wristColumn` when the task is not
`handover_box`. The class changes the desktop grid to one row. Below 850 pixels, restore
the slot and wrist column to normal flow and each image to `height:auto`, preserving the
full-width global/sender/receiver order.

- [x] **Step 5: Run targeted and complete verification**

Run: `.venv/bin/python -m pytest tests/test_camera_configuration.py -q`

Run: `MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=6 .venv/bin/python -m pytest -q`

Run: `.venv/bin/python -m py_compile scripts/teleop_web.py`

Expected: all tests and compilation pass.
