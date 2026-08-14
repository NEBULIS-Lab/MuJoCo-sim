import threading
from urllib.request import urlopen

import numpy as np

from scripts import teleop_web


def test_live_frame_endpoint_serves_each_camera_independently(tmp_path):
    state = teleop_web.AppState(tmp_path)
    state.jpegs = {
        "global": b"global-jpeg",
        "sender": b"sender-jpeg",
        "receiver": b"receiver-jpeg",
    }
    server = teleop_web.ThreadingHTTPServer(("127.0.0.1", 0), teleop_web.create_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        for camera, expected in state.jpegs.items():
            with urlopen(f"http://127.0.0.1:{port}/api/frame?camera={camera}") as response:
                assert response.read() == expected
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_console_exposes_global_and_two_wrist_images(tmp_path):
    state = teleop_web.AppState(tmp_path)
    server = teleop_web.ThreadingHTTPServer(("127.0.0.1", 0), teleop_web.create_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urlopen(f"http://127.0.0.1:{port}/") as response:
            html = response.read().decode("utf-8")
        assert 'id="globalFrame"' in html
        assert 'id="senderFrame"' in html
        assert 'id="receiverFrame"' in html
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_console_uses_camera_row_and_lower_data_management(tmp_path):
    state = teleop_web.AppState(tmp_path)
    server = teleop_web.ThreadingHTTPServer(("127.0.0.1", 0), teleop_web.create_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urlopen(f"http://127.0.0.1:{port}/") as response:
            html = response.read().decode("utf-8")

        for element_id in (
            "cameraLayout",
            "wristColumn",
            "dataManagement",
            "globalFrame",
            "senderFrame",
            "receiverFrame",
            "pendingPanel",
            "episodes",
            "trash",
        ):
            assert f'id="{element_id}"' in html
        assert html.index('id="globalFrame"') < html.index('id="wristColumn"')
        assert html.index('id="dataManagement"') > html.index('id="dualControls"')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_console_matches_wrist_height_without_cropping(tmp_path):
    state = teleop_web.AppState(tmp_path)
    server = teleop_web.ThreadingHTTPServer(("127.0.0.1", 0), teleop_web.create_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urlopen(f"http://127.0.0.1:{port}/") as response:
            html = response.read().decode("utf-8")

        assert 'id="wristColumnSlot"' in html
        assert "object-fit:contain" in html
        assert "grid-template-rows:repeat(2,minmax(0,1fr))" in html
        assert "wristColumn').classList.toggle('single-wrist'" in html
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


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
