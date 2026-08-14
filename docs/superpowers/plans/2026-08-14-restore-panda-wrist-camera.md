# Restore Panda Wrist Camera Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore both dual-arm handover wrist views to robosuite's built-in Panda `eye_in_hand` camera configuration without reducing image resolution or changing other collection behavior.

**Architecture:** Remove the task-level Panda wrist camera XML mutations and let each robot model supply its native camera pose and field of view. Verify the assembled MuJoCo model at runtime, then inspect fresh EGL renders so the regression test covers configuration while human inspection covers the resulting framing.

**Tech Stack:** Python 3.10, robosuite 1.5.2, MuJoCo EGL, NumPy, pytest, Pillow

## Global Constraints

- Keep the collection render size at 512 by 512 pixels per camera.
- Keep `robot0_eye_in_hand` mapped to sender and `robot1_eye_in_hand` mapped to receiver.
- Do not change the global camera, JPEG quality, polling rate, web layout, recording behavior, or HDF5 schema.
- Do not modify existing HDF5 trajectories.
- `/data/private/user7/projects/MoJuCo-sim` is not a Git repository, so no commit step is performed.

---

### Task 1: Restore Native Panda Wrist Cameras

**Files:**
- Modify: `tests/test_camera_configuration.py`
- Modify: `src/multiarm_sim/envs/handover_box.py`

**Interfaces:**
- Consumes: `make_handover_box_env(image_size: int, horizon: int, seed: int | None)`, `GLOBAL_CAMERA`, and `LOCAL_CAMERAS`.
- Produces: an assembled handover environment whose `robot0_eye_in_hand` and `robot1_eye_in_hand` cameras retain Panda MJCF local pose `[0.05, 0.0, 0.0]`, local quaternion `[0.0, 0.707108, 0.707108, 0.0]`, and field of view `75.0` degrees.

- [x] **Step 1: Replace the custom-direction assertion with a native-camera regression test**

In `tests/test_camera_configuration.py`, replace `test_handover_cameras_cover_global_and_forward_down_wrist_views` with:

```python
def test_handover_uses_global_view_and_native_panda_wrist_cameras():
    from multiarm_sim.envs.handover_box import GLOBAL_CAMERA, LOCAL_CAMERAS, make_handover_box_env

    env = make_handover_box_env(image_size=64, seed=91)
    try:
        observation = env.reset()
        global_id = env.sim.model.camera_name2id(GLOBAL_CAMERA)
        assert env.sim.model.cam_fovy[global_id] == 52.0
        assert observation[f"{GLOBAL_CAMERA}_image"].shape == (64, 64, 3)

        for camera in LOCAL_CAMERAS:
            camera_id = env.sim.model.camera_name2id(camera)
            np.testing.assert_allclose(
                env.sim.model.cam_pos[camera_id],
                np.array([0.05, 0.0, 0.0]),
                atol=1e-6,
            )
            np.testing.assert_allclose(
                env.sim.model.cam_quat[camera_id],
                np.array([0.0, 0.707108, 0.707108, 0.0]),
                atol=1e-5,
            )
            assert env.sim.model.cam_fovy[camera_id] == 75.0
            assert observation[f"{camera}_image"].shape == (64, 64, 3)
            assert np.std(observation[f"{camera}_image"]) > 5.0
    finally:
        env.close()
```

- [x] **Step 2: Run the test and verify the current override fails**

Run:

```bash
MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=6 .venv/bin/python -m pytest \
  tests/test_camera_configuration.py::test_handover_uses_global_view_and_native_panda_wrist_cameras -q
```

Expected: FAIL because the assembled wrist cameras currently use the custom quaternion and 62-degree field of view.

- [x] **Step 3: Remove the task-level wrist camera overrides**

In `src/multiarm_sim/envs/handover_box.py`, delete:

```python
WRIST_CAMERA_POSITION = (0.05, 0.0, 0.0)
WRIST_CAMERA_QUATERNION = (-0.230, 0.669, 0.669, -0.230)
WRIST_CAMERA_FOVY = 62.0
```

Inside `ColoredHandoverBox._load_model`, retain the loop that sets each robot base position and orientation, but delete:

```python
wrist_camera = robot.robot_model.worldbody.find(
    f".//camera[@name='{robot.robot_model.naming_prefix}eye_in_hand']"
)
wrist_camera.set("pos", array_to_string(WRIST_CAMERA_POSITION))
wrist_camera.set("quat", array_to_string(WRIST_CAMERA_QUATERNION))
wrist_camera.set("fovy", str(WRIST_CAMERA_FOVY))
```

Do not change `array_to_string`; the file still uses it for fixed open-box poses.

- [x] **Step 4: Run the focused camera tests**

Run:

```bash
MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=6 .venv/bin/python -m pytest tests/test_camera_configuration.py -q
```

Expected: all camera endpoint, web layout, global camera, and native Panda wrist camera tests pass.

- [x] **Step 5: Render and inspect the native 512-pixel wrist views**

Run:

```bash
MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=6 .venv/bin/python -c "from pathlib import Path; from PIL import Image; from multiarm_sim.envs.handover_box import make_handover_box_env, GLOBAL_CAMERA, LOCAL_CAMERAS, frame_from_observation; env=make_handover_box_env(image_size=512, seed=91); obs=env.reset(); out=Path('/tmp/mujoco_native_wrist_check'); out.mkdir(exist_ok=True); [Image.fromarray(frame_from_observation(obs, camera)).save(out / (camera + '.png')) for camera in (GLOBAL_CAMERA, *LOCAL_CAMERAS)]; print(out); env.close()"
```

Inspect both `/tmp/mujoco_native_wrist_check/robot0_eye_in_hand.png` and `/tmp/mujoco_native_wrist_check/robot1_eye_in_hand.png`. Expected: native Panda framing with gripper fingers visible; blank tabletop is acceptable. Confirm the global image is unchanged.

- [x] **Step 6: Run complete verification**

Run:

```bash
MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=6 .venv/bin/python -m pytest -q
.venv/bin/python -m py_compile src/multiarm_sim/envs/handover_box.py scripts/teleop_web.py
```

Expected: the complete test suite and syntax compilation pass. Existing datasets are read-only throughout this task.
