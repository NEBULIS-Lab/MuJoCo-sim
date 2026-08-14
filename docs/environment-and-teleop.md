# 服务器环境与 Mac 遥操作说明

## 已核查的平台

- 系统：Ubuntu 24.04.3 LTS，Linux x86_64，glibc 2.39。
- CPU：2 × AMD EPYC 9554，共 256 个逻辑 CPU。
- GPU：8 × NVIDIA RTX 5880 Ada Generation（每张约 48 GB）。
- NVIDIA 驱动：595.58.03。
- 当前 SSH 会话没有 `DISPLAY` / Wayland 桌面会话。
- 系统具有 NVIDIA EGL、Mesa EGL、OSMesa 和 Xvfb。
- 已用现有 MuJoCo 3.8.1 环境分别验证 EGL 与 OSMesa 能创建离屏渲染上下文。

“没有显示器”不等于“不能渲染”。批量采集时不需要打开桌面窗口：

```text
MuJoCo physics
      |
      +-- EGL (NVIDIA GPU, 首选) --> RGB/depth/segmentation arrays
      |
      +-- OSMesa (CPU, 诊断后备) --> RGB/depth/segmentation arrays
```

## 为什么不直接复用旧 Conda 环境

服务器上的既有环境跨越 robosuite 1.2.0、1.4.0、1.4.1 和 MuJoCo 2.3.3、3.2.0、3.8.1；它们还混有 LIBERO、旧 Gym、不同 NumPy 和训练框架。直接复用会使新平台依赖旧项目的兼容性约束。

本项目固定使用：

- Python 3.10.20
- MuJoCo 3.8.1
- robosuite 1.5.2
- NumPy 1.26.4

MuJoCo 3.8.1 已在本服务器成功离屏渲染；robosuite 1.5.2 是当前稳定的 1.5 系列版本。现有包缓存可以由 Conda / pip 自动复用，但不直接复制另一个环境的 `site-packages`，因为二进制扩展、绝对路径和依赖关系可能失效。

实际项目 venv 已完成 `pip check`，没有依赖冲突；EGL 与 OSMesa 均已生成
`120 × 160 × 3` 的 RGB 图像，Panda Lift 也已生成 `128 × 128 × 3`
的 `agentview` 画面。完整解析版本见
`requirements-lock-linux-py310.txt`。

## Mac 上“看到并遥操作”有三种方式

### 1. 先生成视频或帧（当前阶段）

服务器使用 EGL 运行仿真并保存 PNG / MP4，然后通过 SSH / 文件同步在 Mac 查看。这最稳定，适合检查相机、动作和回放，不支持实时控制。

### 2. X11 或远程桌面转发（只适合临时调试）

Mac 安装 XQuartz 后可以尝试 `ssh -Y`，或者由服务器提供 VNC / xpra 桌面。优点是现有 viewer 改动少；缺点是 OpenGL 转发、键盘焦点、延迟和断线恢复都较脆弱。当前服务器有 Xvfb，但没有检测到 xpra / TurboVNC，因此这不是首选主线。

### 3. 浏览器遥操作界面（计划采用）

推荐最终结构：

```text
Mac browser
  keyboard / gamepad / SpaceMouse-like commands
                |
          SSH tunnel (只开放 localhost)
                |
Linux teleop service
  action arbitration + safety limits
                |
MuJoCo + robosuite
  EGL render --> JPEG/WebRTC frames --> browser
                |
          episode recorder
```

浏览器方案不把 MuJoCo 窗口“搬到 Mac”，而是让 Linux 保持物理仿真和渲染，Mac 只接收画面并发送输入。它有几个重要优点：

- 不依赖 X11 / OpenGL 窗口转发。
- Mac 只需浏览器，Apple Silicon 与 Linux x86_64 的二进制差异不影响服务端。
- 可以设计“切换 active arm，其余机械臂 hold”的单人多臂操作方式。
- 网络断开时服务端可以立即置零动作、停止 episode，避免轨迹失控。
- 通过 SSH tunnel 使用时无需把控制端口暴露到局域网或公网。

浏览器遥操作会在单臂记录/回放闭环完成后实现。第一版使用键盘或浏览器 Gamepad API；SpaceMouse 需要单独确认设备型号和 Mac 浏览器/驱动能否提供原始输入。

## 在 Apple Silicon Mac 下载 Linux x86_64 wheel

服务器目标不是 macOS 包，而是：

```text
CPython 3.10
Linux x86_64
manylinux_2_28（服务器 glibc 2.39 可兼容）
```

在 Mac 建议使用一个纯下载目录，不要把这些 Linux wheel 安装到 Mac：

```bash
mkdir -p wheelhouse-linux-py310

python3 -m pip download \
  --dest wheelhouse-linux-py310 \
  --platform manylinux_2_28_x86_64 \
  --python-version 310 \
  --implementation cp \
  --abi cp310 \
  --only-binary=:all: \
  numpy==1.26.4 \
  mujoco==3.8.1 \
  opencv-python==4.10.0.84 \
  h5py==3.16.0 \
  imageio==2.37.3 \
  imageio-ffmpeg==0.6.0
```

`robosuite==1.5.2` 自身及部分纯 Python 依赖可能没有适合 `--only-binary=:all:` 的 wheel。更稳妥的离线做法是在一台可联网的 Linux x86_64 机器或 `linux/amd64` 容器中运行：

```bash
python -m pip download --dest wheelhouse -r requirements.txt
```

本项目现在已经有准确的 `requirements-lock-linux-py310.txt`。若 Mac 上有
Docker Desktop，最稳妥的完整离线准备方式是在 Linux x86_64 容器中构建
wheelhouse，因为 `evdev` 只有源码包，需要在 Linux 目标 ABI 下编译：

```bash
docker run --rm --platform linux/amd64 \
  -v "$PWD:/work" -w /work python:3.10-slim \
  bash -lc '
    apt-get update &&
    apt-get install -y --no-install-recommends build-essential linux-libc-dev &&
    python -m pip wheel \
      --wheel-dir wheelhouse-linux-py310 \
      -r requirements-lock-linux-py310.txt
  '
```

将 `wheelhouse-linux-py310/` 和 lock 文件复制到服务器后，可以完全离线安装：

```bash
python -m pip install \
  --no-index \
  --find-links wheelhouse-linux-py310 \
  -r requirements-lock-linux-py310.txt
```
