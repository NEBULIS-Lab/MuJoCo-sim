# Publish Public GitHub Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the complete portable MuJoCo multi-arm project, its teaching dataset and artifacts, and its engineering record as the public repository `NEBULIS-Lab/MuJoCo-sim`.

**Architecture:** Curate one reproducible initial Git snapshot: keep code, tasks, tests, documentation, the full ChatGPT record, the current 17 MB Lift HDF5, and current teaching artifacts while excluding machine-specific environments and caches. Validate the snapshot locally, create a direct initial `main` commit, then create and push the public GitHub repository with the authenticated `clzJY` account.

**Tech Stack:** Git, GitHub CLI, Markdown, Python 3.10, pytest, h5py, MuJoCo EGL, robosuite 1.5.2

## Global Constraints

- Target exactly `NEBULIS-Lab/MuJoCo-sim`; never fall back to a personal repository.
- Repository visibility is public and the default branch is `main`.
- Use the currently active GitHub CLI account `clzJY`.
- Publish `ChatGPT-MuJoCo 多机械臂仿真.md`.
- Publish `datasets/lift_scripted_test_3.h5` and every current file under `artifacts/`.
- Do not publish `.venv/`, `.conda/`, credentials, caches, bytecode, or `.egg-info/`.
- Future datasets and artifacts remain ignored unless explicitly allowlisted.
- License the repository under MIT with copyright `NEBULIS-Lab`.
- Create one initial commit directly on `main`; do not create a bootstrap pull request.
- Do not modify the separate COMMVLA reference repository.

---

### Task 1: Create the Public Documentation and Snapshot Policy

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Create: `LICENSE`
- Test: root README relative links, CLI command names, dataset and artifact paths

**Interfaces:**
- Consumes: current commands in `scripts/`, user guides in `docs/`, and the current sample files under `datasets/` and `artifacts/`.
- Produces: a Chinese-first `README.md`, an MIT `LICENSE`, and ignore rules that expose only the approved portable snapshot.

- [x] **Step 1: Verify that the current README does not yet satisfy the publication contract**

Run:

```bash
for text in '项目结构' 'SSH 本地端口转发' '事件触发采集' '内置样例数据' '多电脑访问' '三臂与四臂路线图'; do
  rg -q "$text" README.md || exit 1
done
```

Expected: FAIL because the current README does not contain all six public-learning sections.

- [x] **Step 2: Replace `.gitignore` with explicit machine-state exclusions and teaching allowlists**

Use these rules:

```gitignore
# Python environments and generated packages
.conda/
.venv/
*.egg-info/
__pycache__/
*.py[cod]
.pytest_cache/

# Credentials and local configuration
.env
.env.*
!.env.example
*.pem
*.key
id_rsa
id_ed25519

# Editors, operating systems, and logs
.DS_Store
.idea/
.vscode/
*.swp
*.log

# Data is private by default. The current scripted teaching example is public.
datasets/*
!datasets/lift_scripted_test_3.h5

# Generated artifacts are private by default. Current teaching artifacts are public.
artifacts/*
!artifacts/commvla_lift_test_3/
!artifacts/commvla_lift_test_3/**
!artifacts/replay/
!artifacts/replay/**
!artifacts/smoke/
!artifacts/smoke/**
```

- [x] **Step 3: Add the MIT license**

Create `LICENSE` with the standard MIT text beginning:

```text
MIT License

Copyright (c) 2026 NEBULIS-Lab
```

and containing the complete permission grant and warranty disclaimer.

- [x] **Step 4: Rewrite the root README as the complete operator and learner entrypoint**

Use the title `# MuJoCo-sim：多机械臂仿真与示范数据采集平台` and include these exact top-level sections:

```markdown
## 项目定位
## 当前已实现功能
## 场景预览
## 项目结构
## 环境与平台要求
## 安装
## 快速验证
## 启动 Web 数据采集台
## SSH 本地端口转发与多电脑访问
## 遥操作与事件触发采集
## 内置样例数据与产物
## 数据集结构与 COMMVLA 准备
## 测试
## 设计边界与已知限制
## 三臂与四臂路线图
## 进一步文档
## License
```

The README must:

- describe single-arm Panda Lift and dual-Panda colored-cube handover;
- embed `artifacts/smoke/lift_agentview_egl.png` and link the replay MP4;
- show the `src/`, `scripts/`, `tests/`, `docs/`, `datasets/`, and `artifacts/` tree;
- state Python `3.10`, MuJoCo `3.8.1`, robosuite `1.5.2`, NumPy `1.26.4`, and Linux x86_64 for the locked environment;
- show both Conda and isolated venv installation commands;
- show EGL and OSMesa smoke tests;
- launch `scripts/teleop_web.py` with `--backend egl --egl-device 6 --image-size 512 --port 8765 --dataset-dir datasets --max-recording-steps 1200`;
- document `ssh -N -o ExitOnForwardFailure=yes -L 8765:127.0.0.1:8765 hkust` and the alternate local port `8766` example;
- warn that every browser controls one shared simulator session;
- document keyboard translation, rotation, gripper, arm selection, and three handover stages from `docs/handover-box-and-web-console.md`;
- explain 20 Hz simulation, 10 FPS live viewing, and event-gated retained samples with motion and gripper tails;
- inventory the three Lift trajectories, HDF5, PNG, MP4, JSON, and NPZ files included in the repository;
- provide replay and COMMVLA preparation commands that match the scripts' actual CLI arguments;
- link all detailed docs and `ChatGPT-MuJoCo%20多机械臂仿真.md`;
- state that current sample data is scripted single-arm data and that human dual-arm data must be collected locally;
- explain future data privacy, Git LFS / Release use, and the planned three-arm then four-arm sequence.

- [x] **Step 5: Validate README headings, commands, and relative links**

Run the publication-contract loop from Step 1 and expect PASS. Then run:

```bash
.venv/bin/python -c "import re; from pathlib import Path; text=Path('README.md').read_text(); links=re.findall(r'!?\[[^]]*\]\(([^)#]+)', text); missing=[link for link in links if not link.startswith(('http://','https://')) and not Path(link.replace('%20',' ')).exists()]; assert not missing, missing; print('relative_links_ok=', len(links))"
.venv/bin/python scripts/teleop_web.py --help >/dev/null
.venv/bin/python scripts/replay_lift_dataset.py --help >/dev/null
.venv/bin/python scripts/prepare_commvla.py --help >/dev/null
.venv/bin/python scripts/prepare_handover_commvla.py --help >/dev/null
```

Expected: all relative links resolve and every documented CLI imports successfully.

### Task 2: Validate and Commit the Complete Portable Snapshot

**Files:**
- Track: all approved files selected by `.gitignore`
- Exclude: machine state and future unapproved data selected by `.gitignore`

**Interfaces:**
- Consumes: the reviewed publication files from Task 1 and the existing simulation project.
- Produces: local Git repository on `main` with one verified initial commit.

- [x] **Step 1: Scan candidate files for secrets without printing secret values**

Run:

```bash
rg -l --hidden --glob '!.venv/**' --glob '!.conda/**' --glob '!datasets/**' \
  --glob '!artifacts/**' \
  '(github_pat_|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY|password\s*[:=])' .
```

Expected: no credential-bearing project file. Investigate any returned filename before proceeding; never print the matched value.

- [x] **Step 2: Validate the included sample data and artifact inventory**

Run:

```bash
.venv/bin/python -c "import h5py; p='datasets/lift_scripted_test_3.h5'; f=h5py.File(p,'r'); assert list(f)==['trajectory_000000','trajectory_000001','trajectory_000002']; assert f.attrs['schema_version']=='multiarm-sim-hdf5-v1'; print('sample_trajectories=', len(f)); f.close()"
find artifacts -type f -printf '%s %p\n' | sort -k2
```

Expected: three readable trajectories and seven current teaching artifacts.

- [x] **Step 3: Initialize Git with `main` and inspect ignore behavior**

Run:

```bash
git init -b main
git check-ignore -v .venv/pyvenv.cfg src/multiarm_sim.egg-info/PKG-INFO
git check-ignore datasets/lift_scripted_test_3.h5 && exit 1 || true
git check-ignore artifacts/replay/lift_scripted_test_3_ep1.mp4 && exit 1 || true
```

Expected: the environment and egg-info are ignored, while the approved sample HDF5 and replay MP4 are not ignored.

- [x] **Step 4: Stage the approved project and inspect every staged path and size**

The user has explicitly confirmed that the entire portable project is in scope, so run:

```bash
git add -A
git status --short
git diff --cached --stat
git ls-files -z | xargs -0 -r stat -c '%s %n' | sort -nr | head -30
```

Expected: sample data and artifacts are present; `.venv/`, `.conda/`, caches, and `.egg-info/` are absent; no staged file exceeds 100 MB.

- [x] **Step 5: Run complete simulation and syntax verification on the staged tree**

Run:

```bash
MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=6 .venv/bin/python -m pytest -q
.venv/bin/python -m py_compile scripts/*.py src/multiarm_sim/*.py src/multiarm_sim/envs/*.py
```

Expected: all tests and compilation pass.

- [x] **Step 6: Set local commit identity if needed and create the initial commit**

Run:

```bash
test -n "$(git config user.name)" || git config user.name clzJY
test -n "$(git config user.email)" || git config user.email "$(gh api user --jq '.id|tostring')+clzJY@users.noreply.github.com"
git commit -m "Initial MuJoCo multi-arm simulation platform"
git status --short --branch
```

Expected: one root commit on clean local `main`.

### Task 3: Create and Verify the Public GitHub Repository

**Files:**
- Remote repository: `NEBULIS-Lab/MuJoCo-sim`
- Local remote: `origin`

**Interfaces:**
- Consumes: clean verified `main` root commit from Task 2 and authenticated GitHub CLI account `clzJY`.
- Produces: public GitHub repository, tracked `origin/main`, repository description, and six topics.

- [x] **Step 1: Reconfirm authenticated account and repository nonexistence**

Run:

```bash
test "$(gh api user --jq .login)" = "clzJY"
if gh repo view NEBULIS-Lab/MuJoCo-sim >/dev/null 2>&1; then
  echo 'Target repository already exists; stop before creation.' >&2
  exit 1
fi
```

Expected: account check passes and the target still does not exist.

- [x] **Step 2: Create the public repository and push `main`**

Run:

```bash
gh repo create NEBULIS-Lab/MuJoCo-sim \
  --public \
  --description "MuJoCo and robosuite platform for multi-arm teleoperation, demonstration collection, replay, and VLA dataset preparation" \
  --source . \
  --remote origin \
  --push
```

Expected: GitHub creates only `NEBULIS-Lab/MuJoCo-sim`, pushes the root commit, and configures `main` to track `origin/main`. If organization policy rejects creation, stop and report the permission error without creating another repository.

- [x] **Step 3: Add repository topics**

Run:

```bash
gh repo edit NEBULIS-Lab/MuJoCo-sim \
  --add-topic mujoco \
  --add-topic robosuite \
  --add-topic robotics \
  --add-topic multi-arm \
  --add-topic teleoperation \
  --add-topic vla
```

Expected: all six topics are visible on the repository.

- [x] **Step 4: Verify remote identity, visibility, branch, commit, and clean state**

Run:

```bash
git remote -v
git status --short --branch
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
gh repo view NEBULIS-Lab/MuJoCo-sim --json nameWithOwner,url,visibility,defaultBranchRef,description,repositoryTopics
```

Expected: `origin` targets `NEBULIS-Lab/MuJoCo-sim`, local and remote commits match, visibility is `PUBLIC`, default branch is `main`, and the working tree is clean.
