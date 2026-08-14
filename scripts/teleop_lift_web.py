#!/usr/bin/env python3
"""Browser-based Lift teleoperation over an SSH tunnel.

The HTTP server binds to localhost only. The Mac browser supplies key states;
MuJoCo physics, EGL rendering, and HDF5 recording remain on Linux.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlparse


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MuJoCo Lift teleoperation</title>
  <style>
    body { background:#16181d; color:#eee; font:16px system-ui; margin:24px; }
    img { width:min(100%, 900px); border:1px solid #555; image-rendering:auto; }
    button { font-size:16px; margin:4px; padding:8px 14px; }
    code { color:#9ee6a8; } .warn { color:#ffce70; }
  </style>
</head>
<body>
  <h2>MuJoCo Panda Lift</h2>
  <img id="frame" src="/frame.jpg">
  <p id="status">Connecting…</p>
  <p>
    <button onclick="command('start')">Start new recording</button>
    <button onclick="command('save')">Save now</button>
    <button onclick="command('discard')">Discard + reset</button>
  </p>
  <p>
    Translation: <code>A/D = −/+ X</code>,
    <code>W/S = +/− Y</code>,
    <code>R/F = +/− Z</code>.
    Rotation: <code>U/O roll</code>, <code>I/K pitch</code>,
    <code>J/L yaw</code>. <code>Space</code> toggles gripper.
  </p>
  <p class="warn">Click this page once before using the keyboard. Release keys before switching windows.</p>
<script>
const keys = new Set();
let gripperClosed = false;
async function post(path, payload) {
  await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                     body:JSON.stringify(payload)});
}
function sendInput() {
  post('/input', {keys:[...keys], gripper_closed:gripperClosed});
}
window.addEventListener('keydown', ev => {
  const key = ev.key.toLowerCase();
  if (key === ' ') {
    if (!ev.repeat) gripperClosed = !gripperClosed;
    ev.preventDefault();
  } else {
    keys.add(key);
  }
  sendInput();
});
window.addEventListener('keyup', ev => {
  keys.delete(ev.key.toLowerCase());
  sendInput();
});
window.addEventListener('blur', () => { keys.clear(); sendInput(); });
async function command(name) {
  keys.clear();
  if (name === 'start' || name === 'discard') gripperClosed = false;
  await post('/command', {command:name});
  sendInput();
}
setInterval(sendInput, 150);
setInterval(() => {
  document.getElementById('frame').src = '/frame.jpg?t=' + Date.now();
}, 100);
setInterval(async () => {
  const r = await fetch('/status');
  const s = await r.json();
  document.getElementById('status').textContent =
    `recording=${s.recording} steps=${s.steps} success=${s.success} ` +
    `gripper=${gripperClosed ? 'closed' : 'open'} | ${s.message}`;
}, 300);
</script>
</body>
</html>"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("datasets/lift_human.h5"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--backend", choices=("egl", "osmesa"), default="egl")
    parser.add_argument("--egl-device", type=int, default=None)
    parser.add_argument("--image-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=2000)
    parser.add_argument("--max-recording-steps", type=int, default=1200)
    parser.add_argument("--translation-scale", type=float, default=0.28)
    parser.add_argument("--rotation-scale", type=float, default=0.20)
    return parser.parse_args()


class TeleopState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.keys: set[str] = set()
        self.gripper_closed = False
        self.last_input = 0.0
        self.pending_command: str | None = None
        self.jpeg = b""
        self.recording = False
        self.steps = 0
        self.success = False
        self.message = "Press Start new recording."


def create_handler(state: TeleopState):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                body = HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/frame.jpg":
                with state.lock:
                    body = state.jpeg
                self.send_response(200 if body else 503)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/status":
                with state.lock:
                    payload = {
                        "recording": state.recording,
                        "steps": state.steps,
                        "success": state.success,
                        "message": state.message,
                    }
                self._json(payload)
                return
            self._json({"error": "not found"}, 404)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self._json({"error": "invalid json"}, 400)
                return
            path = urlparse(self.path).path
            if path == "/input":
                with state.lock:
                    state.keys = {str(key).lower() for key in payload.get("keys", [])}
                    state.gripper_closed = bool(payload.get("gripper_closed", False))
                    state.last_input = time.monotonic()
                self._json({"ok": True})
                return
            if path == "/command":
                command = str(payload.get("command", ""))
                if command not in {"start", "save", "discard"}:
                    self._json({"error": "unknown command"}, 400)
                    return
                with state.lock:
                    state.pending_command = command
                self._json({"ok": True})
                return
            self._json({"error": "not found"}, 404)

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def action_from_state(state: TeleopState, translation: float, rotation: float):
    import numpy as np

    with state.lock:
        stale = time.monotonic() - state.last_input > 0.5
        keys = set() if stale else state.keys.copy()
        closed = state.gripper_closed
    action = np.zeros(7, dtype=np.float32)
    action[0] = translation * (("d" in keys) - ("a" in keys))
    action[1] = translation * (("w" in keys) - ("s" in keys))
    action[2] = translation * (("r" in keys) - ("f" in keys))
    action[3] = rotation * (("o" in keys) - ("u" in keys))
    action[4] = rotation * (("i" in keys) - ("k" in keys))
    action[5] = rotation * (("l" in keys) - ("j" in keys))
    action[6] = 1.0 if closed else -1.0
    return action


def encode_view(observation: dict, state: TeleopState) -> None:
    import cv2
    import numpy as np

    from multiarm_sim.lift import GLOBAL_CAMERA, LOCAL_CAMERA, frame_from_observation

    global_rgb = frame_from_observation(observation, GLOBAL_CAMERA)
    local_rgb = frame_from_observation(observation, LOCAL_CAMERA)
    combined = np.concatenate([global_rgb, local_rgb], axis=1)
    bgr = cv2.cvtColor(combined, cv2.COLOR_RGB2BGR)
    cv2.putText(bgr, "global", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 255, 80), 2)
    cv2.putText(
        bgr,
        "wrist",
        (global_rgb.shape[1] + 8, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (80, 255, 80),
        2,
    )
    ok, encoded = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if ok:
        with state.lock:
            state.jpeg = encoded.tobytes()


def main() -> None:
    args = parse_args()
    os.environ["MUJOCO_GL"] = args.backend
    if args.egl_device is not None:
        os.environ["MUJOCO_EGL_DEVICE_ID"] = str(args.egl_device)

    from multiarm_sim.dataset import EpisodeBuffer, append_episode
    from multiarm_sim.lift import CONTROL_FREQUENCY, make_lift_env

    state = TeleopState()
    env = make_lift_env(
        image_size=args.image_size,
        horizon=args.max_recording_steps + 1,
        seed=args.seed,
    )
    observation = env.reset()
    encode_view(observation, state)
    buffer: EpisodeBuffer | None = None
    episode_seed = args.seed

    server = ThreadingHTTPServer((args.host, args.port), create_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"teleop_url=http://{args.host}:{args.port}")
    print(f"dataset={args.output.resolve()}")
    print("Use an SSH local tunnel from the Mac; press Ctrl-C here to stop.")

    period = 1.0 / CONTROL_FREQUENCY
    try:
        while True:
            started = time.monotonic()
            with state.lock:
                command = state.pending_command
                state.pending_command = None

            if command in {"start", "discard"}:
                episode_seed += 1
                # Recreate the environment so the stored seed exactly identifies
                # the placement RNG for this episode.
                env.close()
                env = make_lift_env(
                    image_size=args.image_size,
                    horizon=args.max_recording_steps + 1,
                    seed=episode_seed,
                )
                observation = env.reset()
                buffer = EpisodeBuffer(seed=episode_seed, source="human_web_teleop")
                with state.lock:
                    state.keys.clear()
                    state.gripper_closed = False
                    state.steps = 0
                    state.success = False
                    state.recording = command == "start"
                    state.message = (
                        "Recording. Lift the cube."
                        if command == "start"
                        else "Discarded. Press Start when ready."
                    )
                encode_view(observation, state)

            if command == "save":
                with state.lock:
                    was_recording = state.recording
                    success = state.success
                    state.recording = False
                if was_recording and buffer is not None and len(buffer):
                    name = append_episode(
                        args.output,
                        buffer,
                        final_sim_state=env.sim.get_state().flatten(),
                        success=success,
                    )
                    with state.lock:
                        state.message = f"Saved {name}, success={success}."
                else:
                    with state.lock:
                        state.message = "Nothing was recording."

            action = action_from_state(state, args.translation_scale, args.rotation_scale)
            pre_observation = observation
            pre_state = env.sim.get_state().flatten().copy()
            observation, reward, done, _ = env.step(action)
            success = bool(env._check_success())

            with state.lock:
                recording = state.recording
            if recording and buffer is not None:
                buffer.append(
                    observation=pre_observation,
                    sim_state=pre_state,
                    action=action,
                    reward=reward,
                    done=done,
                    success=success,
                )
                with state.lock:
                    state.steps = len(buffer)
                    state.success = success

                if success or len(buffer) >= args.max_recording_steps:
                    name = append_episode(
                        args.output,
                        buffer,
                        final_sim_state=env.sim.get_state().flatten(),
                        success=success,
                    )
                    with state.lock:
                        state.recording = False
                        state.message = (
                            f"Automatically saved {name}, success={success}. "
                            "Press Start for another episode."
                        )

            encode_view(observation, state)
            remaining = period - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        print("Stopping teleoperation server.")
    finally:
        server.shutdown()
        server.server_close()
        env.close()


if __name__ == "__main__":
    main()
