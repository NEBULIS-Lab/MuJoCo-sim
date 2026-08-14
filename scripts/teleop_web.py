#!/usr/bin/env python3
"""Unified browser teleoperation and dataset review over an SSH tunnel."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import time
from urllib.parse import parse_qs, urlparse

from multiarm_sim.teleop_recording import EventGatedRecorder


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>MuJoCo 遥操作与数据管理</title>
  <style>
    :root{--bg:#10151d;--panel:#18212d;--line:#344253;--text:#edf3f8;--muted:#9eacba;
      --blue:#65a9ff;--green:#6ed69b;--red:#ff7c84;--yellow:#ffd27a}
    *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);
      font:15px/1.5 system-ui,-apple-system,sans-serif} main{max-width:1220px;margin:auto;padding:22px}
    h1,h2,h3{margin:.3em 0}.muted{color:var(--muted)} .hidden{display:none!important}
    .top{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}
    .card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
    .card.available{cursor:pointer}.card.available:hover{border-color:var(--blue);transform:translateY(-1px)}
    .tag{display:inline-block;border:1px solid var(--line);border-radius:99px;padding:2px 9px;color:var(--muted)}
    button,select,input{font:inherit} button{color:var(--text);background:#263447;border:1px solid #455a72;
      border-radius:7px;padding:7px 12px;margin:3px;cursor:pointer} button:hover{border-color:var(--blue)}
    button.primary{background:#1769c2} button.good{background:#187146} button.danger{background:#7b2930}
    button:disabled{opacity:.45;cursor:not-allowed}.task-stack,.data-management{display:grid;gap:15px}
    .camera-layout{display:grid;grid-template-columns:minmax(0,3fr) minmax(300px,2fr);gap:12px;align-items:stretch}
    .global-camera,.wrist-column-slot{min-width:0}.wrist-column-slot{position:relative;min-height:0}
    .wrist-column{position:absolute;inset:0;min-width:0;min-height:0;display:grid;
      grid-template-rows:repeat(2,minmax(0,1fr));gap:9px}
    .wrist-column.single-wrist{grid-template-rows:minmax(0,1fr)}
    .wrist-view{min-height:0;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .wrist-view .live-frame{display:block;width:100%;height:100%;min-height:0;object-fit:contain}
    .dataset-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:15px}
    .live-frame,#reviewFrame{width:100%;background:#080b10;border-radius:8px;border:1px solid var(--line)}
    .camera-title{color:var(--muted);font-size:13px;margin:6px 0 3px}
    code,kbd{color:#b9ddff;background:#111923;border:1px solid #334255;border-radius:4px;padding:1px 5px}
    .statusline{display:flex;flex-wrap:wrap;gap:7px;margin:9px 0}.pill{padding:3px 9px;border-radius:99px;background:#253345}
    .active{outline:2px solid var(--yellow)} .stage button.active{background:#86631b}
    .episode{border-top:1px solid var(--line);padding:9px 0}.episode:first-child{border-top:0}
    .episode-row{display:flex;justify-content:space-between;gap:8px;align-items:center}
    .ok{color:var(--green)}.bad{color:var(--red)}.warn{color:var(--yellow)}
    #toast{position:fixed;right:20px;bottom:20px;padding:10px 16px;background:#263447;border:1px solid var(--line);
      border-radius:8px;display:none}.controls{margin:10px 0}.review-controls{display:flex;align-items:center;gap:7px}
    .review-controls input{flex:1}@media(max-width:850px){
      .camera-layout,.dataset-grid{grid-template-columns:1fr}
      .wrist-column-slot{position:static}.wrist-column{position:static;inset:auto;grid-template-rows:none}
      .wrist-column.single-wrist{grid-template-rows:none}.wrist-view{display:block}.wrist-view .live-frame{height:auto}
    }
  </style>
</head>
<body><main>
  <div class="top"><div><h1>MuJoCo 数据采集台</h1><div class="muted">物理、渲染和 HDF5 均在 Linux；Mac 浏览器只传按键和查看画面。</div></div>
    <button id="lobbyBtn" class="hidden" onclick="showLobby()">任务大厅</button></div>

  <section id="lobby">
    <h2>选择机械臂规模</h2>
    <div class="grid">
      <article class="card available" onclick="choose('lift')"><span class="tag">单臂</span><h3>Panda Lift</h3>
        <p>抓取并抬起桌面方块。用于检查基础控制与单智能体数据链路。</p><b>进入任务 →</b></article>
      <article class="card available" onclick="choose('handover_box')"><span class="tag">双臂</span><h3>彩色方块交接入盒</h3>
        <p>发送臂抓取指定颜色，交给接收臂，再放入同色开口盒。</p><b>进入任务 →</b></article>
      <article class="card"><span class="tag">多臂 · 后续</span><h3>多机械臂协同</h3>
        <p class="muted">接口已按任务注册表保留；等双臂数据流程稳定后再加入具体任务，避免空目录和无用代码。</p></article>
    </div>
  </section>

  <section id="workspace" class="hidden">
    <div class="task-stack">
        <div class="panel task-panel">
          <h2 id="taskTitle">任务</h2><div id="instruction" class="warn">正在初始化……</div>
          <div id="serverMessage" class="muted">等待服务器状态……</div>
          <div class="statusline">
            <span class="pill" id="recPill">未录制</span><span class="pill" id="stepPill">0 个有效步</span>
            <span class="pill" id="idlePill">已压缩等待 0.0 秒</span>
            <span class="pill" id="successPill">未成功</span><span class="pill" id="targetPill"></span>
          </div>
          <div id="cameraLayout" class="camera-layout">
            <div class="global-camera"><div class="camera-title">全局视角</div><img id="globalFrame" class="live-frame" alt="MuJoCo global camera"></div>
            <div id="wristColumnSlot" class="wrist-column-slot">
              <div id="wristColumn" class="wrist-column">
                <div class="wrist-view"><div class="camera-title">发送臂腕部</div><img id="senderFrame" class="live-frame" alt="sender wrist camera"></div>
                <div id="receiverCamera" class="wrist-view"><div class="camera-title">接收臂腕部</div><img id="receiverFrame" class="live-frame" alt="receiver wrist camera"></div>
              </div>
            </div>
          </div>
          <div class="controls">
            <button class="primary" onclick="sendCommand('start')">开始新轨迹</button>
            <button onclick="sendCommand('finish')">结束并检查</button>
            <button class="danger" onclick="sendCommand('discard')">放弃当前轨迹</button>
          </div>
          <div id="dualControls">
            <b>当前控制：</b>
            <button id="arm0" onclick="setArm(0)">1 · 左侧发送臂</button>
            <button id="arm1" onclick="setArm(1)">2 · 右侧接收臂</button>
            <div class="stage"><b>阶段标签：</b>
              <button id="stage0" onclick="setStage(0)">① 左臂抓取</button>
              <button id="stage1" onclick="setStage(1)">② 中间交接</button>
              <button id="stage2" onclick="setStage(2)">③ 右臂入盒</button>
            </div>
          </div>
          <p><kbd>A/D</kbd>、<kbd>W/S</kbd>、<kbd>R/F</kbd>：沿桌面 X/Y/Z 移动；
            <kbd>U/O</kbd>、<kbd>I/K</kbd>、<kbd>J/L</kbd>：旋转；<kbd>空格</kbd>：开合当前夹爪。
            双臂可用 <kbd>1</kbd>/<kbd>2</kbd> 或 <kbd>Tab</kbd> 切换。</p>
          <p class="muted">切换机械臂后，未激活机械臂保持姿态和夹爪状态；每个仿真步仍同步保存两臂动作。</p>
        </div>
      <section id="dataManagement" class="data-management">
        <div id="pendingPanel" class="panel hidden">
          <h3>待确认轨迹</h3><p id="pendingText"></p>
          <img id="reviewFrame"><div class="review-controls">
            <button onclick="toggleReview()">▶/Ⅱ</button><input id="reviewSlider" type="range" min="0" value="0" oninput="reviewAt(+this.value)">
          </div>
          <button class="good" onclick="sendCommand('confirm')">确认保存到 HDF5</button>
          <button class="danger" onclick="sendCommand('discard_pending')">丢弃待确认轨迹</button>
        </div>
        <div class="dataset-grid">
          <div class="panel"><h3>已保存数据</h3><div id="episodes" class="muted">暂无轨迹</div></div>
          <div class="panel"><h3>回收站</h3><div id="trash" class="muted">暂无已删除轨迹</div></div>
        </div>
      </section>
    </div>
  </section>
  <div id="toast"></div>
</main>
<script>
let currentTask=null, keys=new Set(), activeArm=0, stage=0, grippers=[false,false];
let status={}, reviewTimer=null, reviewSource='pending', reviewName='', reviewSteps=0;
const $=id=>document.getElementById(id);
async function post(path,data){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const j=await r.json();if(!r.ok)throw new Error(j.error||'request failed');return j}
function toast(s){$('toast').textContent=s;$('toast').style.display='block';setTimeout(()=>$('toast').style.display='none',2200)}
async function choose(task){currentTask=task;$('lobby').classList.add('hidden');$('workspace').classList.remove('hidden');
  $('lobbyBtn').classList.remove('hidden');$('dualControls').classList.toggle('hidden',task!=='handover_box');
  $('receiverCamera').classList.toggle('hidden',task!=='handover_box');
  $('wristColumn').classList.toggle('single-wrist',task!=='handover_box');
  try{const result=await post('/api/select',{task});toast(`任务命令 #${result.command_id} 已送达服务器`)}
  catch(e){currentTask=null;showLobby();toast(e.message)}}
function showLobby(){$('workspace').classList.add('hidden');$('lobby').classList.remove('hidden');$('lobbyBtn').classList.add('hidden')}
async function sendCommand(name,extra={}){try{if(name==='start'){reviewSource='pending';reviewName='';$('reviewFrame').removeAttribute('src')}
  const result=await post('/api/command',{command:name,...extra});
  toast(`命令 #${result.command_id} 已送达服务器`);
  $('serverMessage').textContent=`等待执行：#${result.command_id} ${name}`;
  }catch(e){toast(e.message)}}
function setArm(i){activeArm=i;sendInput();paintControls()} function setStage(i){stage=i;sendInput();paintControls()}
function paintControls(){for(let i=0;i<2;i++)$('arm'+i)?.classList.toggle('active',i===activeArm);
  for(let i=0;i<3;i++)$('stage'+i)?.classList.toggle('active',i===stage)}
function sendInput(){if(!currentTask)return;post('/api/input',{keys:[...keys],active_arm:activeArm,stage,grippers}).catch(()=>{})}
window.addEventListener('keydown',e=>{if($('workspace').classList.contains('hidden'))return;let k=e.key.toLowerCase();
  if(k===' '&&!e.repeat){grippers[activeArm]=!grippers[activeArm];e.preventDefault()}
  else if(k==='1'){setArm(0);e.preventDefault()}else if(k==='2'){setArm(1);e.preventDefault()}
  else if(k==='tab'){setArm(1-activeArm);e.preventDefault()}else keys.add(k);sendInput()});
window.addEventListener('keyup',e=>{keys.delete(e.key.toLowerCase());sendInput()});
window.addEventListener('blur',()=>{keys.clear();sendInput()});setInterval(sendInput,150);
function reviewAt(i){if(reviewSteps<1)return;i=Math.max(0,Math.min(i,reviewSteps-1));$('reviewSlider').value=i;
  $('reviewFrame').src=`/api/review-frame?source=${encodeURIComponent(reviewSource)}&name=${encodeURIComponent(reviewName)}&index=${i}&t=${Date.now()}`}
function toggleReview(){if(reviewTimer){clearInterval(reviewTimer);reviewTimer=null;return}reviewTimer=setInterval(()=>{
  let i=(+$('reviewSlider').value+1)%Math.max(reviewSteps,1);reviewAt(i)},80)}
function openSaved(name,steps){reviewSource='saved';reviewName=name;reviewSteps=steps;$('pendingPanel').classList.remove('hidden');
  $('pendingText').textContent=`回放已保存轨迹 ${name}（${steps} 步）`;$('reviewSlider').max=Math.max(steps-1,0);reviewAt(0)}
function deleteEp(name){if(confirm(`将 ${name} 移入可恢复回收站？`))sendCommand('delete',{name})}
function renderLists(s){let e=s.episodes||[];$('episodes').innerHTML=e.length?e.map(x=>`<div class="episode"><div class="episode-row">
  <span><b>${x.name}</b> · ${x.steps} 步 · <span class="${x.success?'ok':'bad'}">${x.success?'成功':'未成功'}</span><br>
  <small>${x.target_color||''} ${x.created_at||''}</small></span><span><button onclick="openSaved('${x.name}',${x.steps})">回放</button>
  <button class="danger" onclick="deleteEp('${x.name}')">删除</button></span></div></div>`).join(''):'<span class="muted">暂无轨迹</span>';
  let t=s.trash||[];$('trash').innerHTML=t.length?t.map(x=>`<div class="episode"><b>${x.original_name}</b> · ${x.steps} 步
  <button onclick="sendCommand('restore',{name:'${x.trash_name}'})">恢复</button></div>`).join(''):'<span class="muted">暂无已删除轨迹</span>'}
async function poll(){try{let r=await fetch('/api/status'),s=await r.json();status=s;if(!currentTask||s.task!==currentTask)return;
  $('taskTitle').textContent=s.task_title;$('instruction').textContent=s.instruction;
  $('serverMessage').textContent=s.message+(s.last_executed_command?` ｜ 最近执行：#${s.last_executed_command.id} ${s.last_executed_command.command}`:'');
  $('recPill').textContent=s.recording?(s.capturing?'● 正在采集有效动作':'已就绪，等待输入'):'未录制';
  $('stepPill').textContent=`${s.steps} 个有效步`;$('idlePill').textContent=`已压缩等待 ${(s.idle_seconds||0).toFixed(1)} 秒`;
  $('successPill').textContent=s.success?'任务成功':'尚未成功';$('successPill').className='pill '+(s.success?'ok':'');
  $('targetPill').textContent=s.target_color?`目标：${s.target_color}`:'';
  let tick=Date.now();$('globalFrame').src='/api/frame?camera=global&t='+tick;
  $('senderFrame').src='/api/frame?camera=sender&t='+tick;
  if(currentTask==='handover_box')$('receiverFrame').src='/api/frame?camera=receiver&t='+tick;
  activeArm=s.active_arm;stage=s.stage;paintControls();renderLists(s);
  if(s.pending&&reviewSource==='pending'){$('pendingPanel').classList.remove('hidden');reviewSteps=s.pending_steps;
    $('pendingText').textContent=`${s.pending_success?'成功':'未成功'} · ${s.pending_steps} 步。请先回放，再决定是否保存。`;
    $('reviewSlider').max=Math.max(reviewSteps-1,0);if(!$('reviewFrame').src.includes('/api/review-frame'))reviewAt(0)}
  else if(!s.pending&&reviewSource==='pending')$('pendingPanel').classList.add('hidden');
 }catch(e){}}setInterval(poll,100);poll();paintControls();
</script></body></html>"""


TASKS = {
    "lift": {
        "title": "单臂 · Panda Lift",
        "output": "lift_human.h5",
        "arms": 1,
    },
    "handover_box": {
        "title": "双臂 · 彩色方块交接入盒",
        "output": "handover_box_human.h5",
        "arms": 2,
    },
}


MOTION_KEYS = frozenset("adwsrfuoikjl")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, default=Path("datasets"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--backend", choices=("egl", "osmesa"), default="egl")
    parser.add_argument("--egl-device", type=int, default=None)
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--seed", type=int, default=3000)
    parser.add_argument("--max-recording-steps", type=int, default=1200)
    parser.add_argument("--translation-scale", type=float, default=0.28)
    parser.add_argument("--rotation-scale", type=float, default=0.20)
    parser.add_argument("--motion-tail-seconds", type=float, default=0.30)
    parser.add_argument("--gripper-tail-seconds", type=float, default=0.50)
    return parser.parse_args(argv)


class AppState:
    def __init__(self, dataset_dir: Path):
        self.lock = threading.RLock()
        self.dataset_dir = dataset_dir
        self.task: str | None = None
        self.keys: set[str] = set()
        self.active_arm = 0
        self.stage = 0
        self.grippers = [False, False]
        self.last_input = 0.0
        self.commands: list[dict] = []
        self.next_command_id = 1
        self.last_queued_command: dict | None = None
        self.last_executed_command: dict | None = None
        self.jpegs: dict[str, bytes] = {}
        self.recording = False
        self.capturing = False
        self.steps = 0
        self.idle_steps = 0
        self.success = False
        self.pending = False
        self.pending_steps = 0
        self.pending_success = False
        self.target_color = ""
        self.instruction = ""
        self.message = "请从任务大厅选择任务。"
        self.episodes: list[dict] = []
        self.trash: list[dict] = []
        self.pending_buffer = None

    def output_path(self) -> Path | None:
        if self.task is None:
            return None
        return self.dataset_dir / TASKS[self.task]["output"]


@dataclass(frozen=True)
class InputSnapshot:
    keys: frozenset[str]
    active_arm: int
    stage: int
    grippers: tuple[bool, ...]

    @property
    def motion_active(self) -> bool:
        return bool(self.keys & MOTION_KEYS)


def _input_snapshot(
    state: AppState,
    task: str,
    *,
    now: float | None = None,
) -> InputSnapshot:
    now = time.monotonic() if now is None else float(now)
    with state.lock:
        keys = frozenset() if now - state.last_input > 0.55 else frozenset(state.keys)
        active_arm = 0 if task == "lift" else state.active_arm
        gripper_count = 1 if task == "lift" else 2
        return InputSnapshot(
            keys=keys,
            active_arm=active_arm,
            stage=state.stage,
            grippers=tuple(state.grippers[:gripper_count]),
        )


def _live_frame_due(*, now: float, last_encoded: float, target_hz: float = 10.0) -> bool:
    if target_hz <= 0:
        raise ValueError("target_hz must be positive")
    return now - last_encoded >= (1.0 / target_hz) - 1e-9


def _encode_rgb(rgb):
    import cv2

    ok, encoded = cv2.imencode(
        ".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92]
    )
    return encoded.tobytes() if ok else b""


def _pending_frame(buffer, index: int):
    import numpy as np

    index = min(max(index, 0), len(buffer) - 1)
    if hasattr(buffer, "local_images") and len(buffer.local_images) == 2 and isinstance(buffer.local_images[0], list):
        images = [buffer.global_images[index], buffer.local_images[0][index], buffer.local_images[1][index]]
    else:
        images = [buffer.global_images[index], buffer.local_images[index]]
    return np.concatenate(images, axis=1)


def _saved_frame(path: Path, name: str, index: int):
    import h5py
    import numpy as np

    with h5py.File(path, "r") as handle:
        if name not in handle or not name.startswith("trajectory_"):
            raise KeyError(name)
        group = handle[name]
        cameras = sorted(group["obs/sensor_data"].keys())
        cameras.sort(key=lambda c: (c != "agentview", c))
        total = int(group["actions/panda-0"].shape[0])
        index = min(max(index, 0), total - 1)
        return np.concatenate([group[f"obs/sensor_data/{camera}/rgb"][index] for camera in cameras[:3]], axis=1)


def _generic_episode_list(path: Path) -> list[dict]:
    import h5py

    if not path.exists():
        return []
    result = []
    with h5py.File(path, "r") as handle:
        names = sorted((n for n in handle if n.startswith("trajectory_")), reverse=True)
        for name in names:
            group = handle[name]
            result.append(
                {
                    "name": name,
                    "steps": int(group["actions/panda-0"].shape[0]),
                    "success": bool(group.attrs.get("success", False)),
                    "target_color": str(group.attrs.get("target_color", "")),
                    "created_at": str(group.attrs.get("created_at", "")),
                }
            )
    return result


def create_handler(state: AppState):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload, code=200):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _bytes(self, body: bytes, content_type: str, code=200):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._bytes(HTML.encode(), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/status":
                with state.lock:
                    payload = {
                        "task": state.task,
                        "task_title": TASKS[state.task]["title"] if state.task else "",
                        "recording": state.recording,
                        "capturing": state.capturing,
                        "steps": state.steps,
                        "idle_steps": state.idle_steps,
                        "idle_seconds": state.idle_steps / 20.0,
                        "recording_policy": "event_gated_20hz",
                        "success": state.success,
                        "pending": state.pending,
                        "pending_steps": state.pending_steps,
                        "pending_success": state.pending_success,
                        "target_color": state.target_color,
                        "instruction": state.instruction,
                        "message": state.message,
                        "active_arm": state.active_arm,
                        "stage": state.stage,
                        "episodes": state.episodes,
                        "trash": state.trash,
                        "last_queued_command": state.last_queued_command,
                        "last_executed_command": state.last_executed_command,
                    }
                self._json(payload)
                return
            if parsed.path == "/api/frame":
                camera = parse_qs(parsed.query).get("camera", ["global"])[0]
                with state.lock:
                    body = state.jpegs.get(camera, b"")
                self._bytes(body, "image/jpeg", 200 if body else 503)
                return
            if parsed.path == "/api/review-frame":
                query = parse_qs(parsed.query)
                source = query.get("source", ["pending"])[0]
                name = query.get("name", [""])[0]
                try:
                    index = int(query.get("index", ["0"])[0])
                    if source == "pending":
                        with state.lock:
                            if state.pending_buffer is None:
                                raise KeyError("no pending trajectory")
                            rgb = _pending_frame(state.pending_buffer, index)
                    else:
                        path = state.output_path()
                        if path is None:
                            raise KeyError("no task")
                        rgb = _saved_frame(path, name, index)
                    self._bytes(_encode_rgb(rgb), "image/jpeg")
                except (KeyError, IndexError, ValueError) as exc:
                    self._json({"error": str(exc)}, 404)
                return
            self._json({"error": "not found"}, 404)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                self._json({"error": "invalid JSON"}, 400)
                return
            parsed = urlparse(self.path)
            if parsed.path == "/api/select":
                task = str(payload.get("task", ""))
                if task not in TASKS:
                    self._json({"error": "unknown task"}, 400)
                    return
                with state.lock:
                    if state.recording or state.pending:
                        self._json(
                            {"error": "请先结束并保存，或明确放弃当前轨迹，再切换任务。"},
                            409,
                        )
                        return
                    command_id = state.next_command_id
                    state.next_command_id += 1
                    item = {"id": command_id, "command": "select", "task": task}
                    state.commands.append(item)
                    state.last_queued_command = item
                    state.message = f"命令 #{command_id} 已排队：初始化 {TASKS[task]['title']}。"
                self._json({"ok": True, "command_id": command_id})
                return
            if parsed.path == "/api/input":
                with state.lock:
                    state.keys = {str(k).lower() for k in payload.get("keys", [])}
                    state.active_arm = min(max(int(payload.get("active_arm", 0)), 0), 1)
                    state.stage = min(max(int(payload.get("stage", 0)), 0), 2)
                    supplied = payload.get("grippers", [False, False])
                    state.grippers = [bool(supplied[0]), bool(supplied[1])]
                    state.last_input = time.monotonic()
                self._json({"ok": True})
                return
            if parsed.path == "/api/command":
                command = str(payload.get("command", ""))
                if command not in {
                    "start", "finish", "confirm", "discard", "discard_pending", "delete", "restore"
                }:
                    self._json({"error": "unknown command"}, 400)
                    return
                with state.lock:
                    command_id = state.next_command_id
                    state.next_command_id += 1
                    item = {
                        "id": command_id,
                        "command": command,
                        "name": str(payload.get("name", "")),
                    }
                    state.commands.append(item)
                    state.last_queued_command = item
                    labels = {
                        "start": "开始新轨迹",
                        "finish": "结束并检查",
                        "confirm": "确认保存",
                        "discard": "放弃当前轨迹",
                        "discard_pending": "丢弃待确认轨迹",
                        "delete": "移入回收站",
                        "restore": "恢复轨迹",
                    }
                    state.message = f"命令 #{command_id} 已排队：{labels[command]}。"
                self._json({"ok": True, "command_id": command_id})
                return
            self._json({"error": "not found"}, 404)

        def log_message(self, format, *args):
            return

    return Handler


def _make_env(task: str, image_size: int, horizon: int, seed: int):
    if task == "lift":
        from multiarm_sim.lift import make_lift_env

        return make_lift_env(image_size=image_size, horizon=horizon, seed=seed)
    from multiarm_sim.envs.handover_box import make_handover_box_env

    return make_handover_box_env(image_size=image_size, horizon=horizon, seed=seed)


def _new_buffer(
    task: str,
    env,
    seed: int,
    *,
    motion_tail_seconds: float,
    gripper_tail_seconds: float,
):
    if task == "lift":
        from multiarm_sim.dataset import EpisodeBuffer

        return EpisodeBuffer(
            seed=seed,
            source="human_web_teleop",
            recording_policy="event_gated_20hz",
            motion_tail_seconds=motion_tail_seconds,
            gripper_tail_seconds=gripper_tail_seconds,
        )
    from multiarm_sim.dual_dataset import DualArmEpisodeBuffer

    return DualArmEpisodeBuffer(
        seed=seed,
        source="human_web_teleop",
        target_color=env.target_color,
        instruction=env.instruction,
        recording_policy="event_gated_20hz",
        motion_tail_seconds=motion_tail_seconds,
        gripper_tail_seconds=gripper_tail_seconds,
    )


def _action(snapshot: InputSnapshot, task: str, translation: float, rotation: float):
    import numpy as np

    keys = snapshot.keys
    active = snapshot.active_arm
    grippers = snapshot.grippers
    world = np.array(
        [
            translation * (("d" in keys) - ("a" in keys)),
            translation * (("w" in keys) - ("s" in keys)),
            translation * (("r" in keys) - ("f" in keys)),
            rotation * (("o" in keys) - ("u" in keys)),
            rotation * (("i" in keys) - ("k" in keys)),
            rotation * (("l" in keys) - ("j" in keys)),
        ],
        dtype=np.float32,
    )
    if task == "lift":
        return np.r_[world, 1.0 if grippers[0] else -1.0].astype(np.float32)
    actions = np.zeros((2, 7), dtype=np.float32)
    # Both robots use base-frame OSC. Convert common table/world XY controls
    # into each opposed base frame so keys feel the same after switching arms.
    if active == 0:
        actions[active, :3] = [world[1], -world[0], world[2]]
        actions[active, 3:6] = [world[4], -world[3], world[5]]
    else:
        actions[active, :3] = [-world[1], world[0], world[2]]
        actions[active, 3:6] = [-world[4], world[3], world[5]]
    actions[:, 6] = [1.0 if closed else -1.0 for closed in grippers]
    return actions.reshape(-1)


def _encode_live(observation: dict, task: str, state: AppState):
    if task == "lift":
        from multiarm_sim.lift import GLOBAL_CAMERA, LOCAL_CAMERA, frame_from_observation

        cameras = (("global", GLOBAL_CAMERA), ("sender", LOCAL_CAMERA))
    else:
        from multiarm_sim.envs.handover_box import GLOBAL_CAMERA, LOCAL_CAMERAS, frame_from_observation

        cameras = (
            ("global", GLOBAL_CAMERA),
            ("sender", LOCAL_CAMERAS[0]),
            ("receiver", LOCAL_CAMERAS[1]),
        )
    encoded = {
        logical_name: _encode_rgb(frame_from_observation(observation, camera_name))
        for logical_name, camera_name in cameras
    }
    with state.lock:
        state.jpegs = encoded


def _refresh_lists(state: AppState):
    from multiarm_sim.dual_dataset import list_trash

    path = state.output_path()
    if path is None:
        return
    episodes = _generic_episode_list(path)
    trash = list_trash(path)
    with state.lock:
        state.episodes = episodes
        state.trash = trash


def main() -> None:
    args = parse_args()
    os.environ["MUJOCO_GL"] = args.backend
    if args.egl_device is not None:
        os.environ["MUJOCO_EGL_DEVICE_ID"] = str(args.egl_device)
    args.dataset_dir.mkdir(parents=True, exist_ok=True)

    state = AppState(args.dataset_dir)
    server = ThreadingHTTPServer((args.host, args.port), create_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"web_url=http://{args.host}:{args.port}")
    print(f"dataset_dir={args.dataset_dir.resolve()}")
    print("Keep this process running; open the URL through an SSH local tunnel from the Mac.")

    env = None
    observation = None
    buffer = None
    pending_final_state = None
    capture_gate = None
    episode_started_at = None
    episode_seed = args.seed
    task = None
    period = 1.0 / 20
    last_live_encoded = float("-inf")

    try:
        while True:
            started = time.monotonic()
            with state.lock:
                commands, state.commands = state.commands, []

            for item in commands:
                command = item["command"]
                if command == "select":
                    task = item["task"]
                    with state.lock:
                        state.task = task
                        state.message = "正在初始化场景……"
                        state.jpegs = {}
                        state.recording = False
                        state.capturing = False
                        state.pending = False
                        state.pending_buffer = None
                    if env is not None:
                        env.close()
                    episode_seed += 1
                    env = _make_env(task, args.image_size, args.max_recording_steps + 1, episode_seed)
                    observation = env.reset()
                    buffer = None
                    pending_final_state = None
                    with state.lock:
                        state.target_color = getattr(env, "target_color", "")
                        state.instruction = getattr(
                            env, "instruction", "Lift the cube above the table."
                        )
                        state.message = "场景已就绪。可以先试操作，再点击“开始新轨迹”。"
                        state.steps = 0
                        state.idle_steps = 0
                        state.success = False
                        state.grippers = [False, False]
                    _refresh_lists(state)
                    _encode_live(observation, task, state)
                    last_live_encoded = time.monotonic()
                    with state.lock:
                        state.last_executed_command = item
                    continue

                if env is None or task is None:
                    with state.lock:
                        state.message = "请先选择任务。"
                        state.last_executed_command = item
                    continue

                if command == "start":
                    episode_seed += 1
                    env.close()
                    env = _make_env(task, args.image_size, args.max_recording_steps + 1, episode_seed)
                    observation = env.reset()
                    buffer = _new_buffer(
                        task,
                        env,
                        episode_seed,
                        motion_tail_seconds=args.motion_tail_seconds,
                        gripper_tail_seconds=args.gripper_tail_seconds,
                    )
                    pending_final_state = None
                    with state.lock:
                        state.recording = True
                        state.capturing = False
                        state.pending = False
                        state.pending_buffer = None
                        state.steps = 0
                        state.idle_steps = 0
                        state.success = False
                        state.grippers = [False, False]
                        state.active_arm = 0
                        state.stage = 0
                        state.keys.clear()
                        state.last_input = 0.0
                        state.target_color = getattr(env, "target_color", "")
                        state.instruction = getattr(
                            env, "instruction", "Lift the cube above the table."
                        )
                        state.message = "正在录制。"
                    capture_gate = EventGatedRecorder(
                        control_frequency_hz=20,
                        motion_tail_seconds=args.motion_tail_seconds,
                        gripper_tail_seconds=args.gripper_tail_seconds,
                    )
                    capture_gate.reset((False,) if task == "lift" else (False, False), stage=0)
                    episode_started_at = time.monotonic()
                elif command == "finish":
                    with state.lock:
                        if state.recording and buffer is not None and len(buffer):
                            state.recording = False
                            state.capturing = False
                            state.pending = True
                            state.pending_buffer = buffer
                            state.pending_steps = len(buffer)
                            state.pending_success = state.success
                            pending_final_state = env.sim.get_state().flatten().copy()
                            state.message = "轨迹待确认：请回放后保存或丢弃。"
                        else:
                            state.recording = False
                            state.capturing = False
                            state.message = "本条轨迹没有有效动作，已结束且不会生成空数据。"
                            buffer = None
                            capture_gate = None
                            episode_started_at = None
                elif command == "confirm":
                    with state.lock:
                        pending = state.pending_buffer
                        pending_success = state.pending_success
                    if pending is None or pending_final_state is None:
                        with state.lock:
                            state.message = "没有待确认轨迹。"
                    else:
                        path = state.output_path()
                        if task == "lift":
                            from multiarm_sim.dataset import append_episode

                            name = append_episode(
                                path, pending, final_sim_state=pending_final_state, success=pending_success
                            )
                        else:
                            from multiarm_sim.dual_dataset import append_dual_arm_episode

                            name = append_dual_arm_episode(
                                path, pending, final_sim_state=pending_final_state, success=pending_success
                            )
                        with state.lock:
                            state.pending = False
                            state.pending_buffer = None
                            state.message = f"已保存 {name}。"
                        buffer = None
                        capture_gate = None
                        episode_started_at = None
                        pending_final_state = None
                        _refresh_lists(state)
                elif command in {"discard", "discard_pending"}:
                    with state.lock:
                        state.recording = False
                        state.capturing = False
                        state.pending = False
                        state.pending_buffer = None
                        state.steps = 0
                        state.idle_steps = 0
                        state.success = False
                        state.message = "当前轨迹已放弃；已保存数据不受影响。"
                    buffer = None
                    capture_gate = None
                    episode_started_at = None
                    pending_final_state = None
                elif command == "delete":
                    from multiarm_sim.dual_dataset import recoverable_delete

                    try:
                        trash_name = recoverable_delete(state.output_path(), item["name"])
                        with state.lock:
                            state.message = f"{item['name']} 已移入回收站 {trash_name}。"
                    except (KeyError, OSError, ValueError) as exc:
                        with state.lock:
                            state.message = f"删除失败：{exc}"
                    _refresh_lists(state)
                elif command == "restore":
                    from multiarm_sim.dual_dataset import restore_episode

                    try:
                        name = restore_episode(state.output_path(), item["name"])
                        with state.lock:
                            state.message = f"已恢复为 {name}。"
                    except (KeyError, OSError, ValueError) as exc:
                        with state.lock:
                            state.message = f"恢复失败：{exc}"
                    _refresh_lists(state)
                with state.lock:
                    state.last_executed_command = item

            if env is None or task is None:
                time.sleep(0.05)
                continue

            snapshot = _input_snapshot(state, task)
            action = _action(snapshot, task, args.translation_scale, args.rotation_scale)
            pre_observation = observation
            pre_state = env.sim.get_state().flatten().copy()
            observation, reward, done, _ = env.step(action)
            success = bool(env._check_success())

            with state.lock:
                recording = state.recording
                active_arm = snapshot.active_arm
                stage = snapshot.stage
            if recording and buffer is not None and capture_gate is not None:
                decision = capture_gate.decide(
                    motion_active=snapshot.motion_active,
                    grippers=snapshot.grippers,
                    stage=stage,
                    success=success,
                )
                with state.lock:
                    state.capturing = decision.capture
                    state.idle_steps = decision.idle_steps
                if not decision.capture:
                    encode_time = time.monotonic()
                    if _live_frame_due(now=encode_time, last_encoded=last_live_encoded):
                        _encode_live(observation, task, state)
                        last_live_encoded = encode_time
                    remaining = period - (time.monotonic() - started)
                    if remaining > 0:
                        time.sleep(remaining)
                    continue
                wall_timestamp = time.monotonic() - episode_started_at
                if task == "lift":
                    buffer.append(
                        observation=pre_observation,
                        sim_state=pre_state,
                        action=action,
                        reward=reward,
                        done=done,
                        success=success,
                        stage=stage,
                        wall_timestamp=wall_timestamp,
                        capture_reason=int(decision.reason),
                    )
                else:
                    buffer.append(
                        observation=pre_observation,
                        sim_state=pre_state,
                        action=action,
                        reward=reward,
                        done=done,
                        success=success,
                        stage=stage,
                        active_arm=active_arm,
                        wall_timestamp=wall_timestamp,
                        capture_reason=int(decision.reason),
                    )
                with state.lock:
                    state.steps = len(buffer)
                    state.success = success
                if success or len(buffer) >= args.max_recording_steps:
                    pending_final_state = env.sim.get_state().flatten().copy()
                    with state.lock:
                        state.recording = False
                        state.capturing = False
                        state.pending = True
                        state.pending_buffer = buffer
                        state.pending_steps = len(buffer)
                        state.pending_success = success
                        state.message = (
                            "任务成功，轨迹已停止并等待确认。"
                            if success
                            else "达到最大步数，轨迹已停止并等待确认。"
                        )

            encode_time = time.monotonic()
            if _live_frame_due(now=encode_time, last_encoded=last_live_encoded):
                _encode_live(observation, task, state)
                last_live_encoded = encode_time
            remaining = period - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        print("Stopping web teleoperation server.")
    finally:
        server.shutdown()
        server.server_close()
        if env is not None:
            env.close()


if __name__ == "__main__":
    main()
