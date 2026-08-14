# 第一阶段测试：Panda Lift 与人类遥操作

## 为什么选择 Lift

第一个测试任务固定为：

> **控制一台 Panda 机械臂抓住桌上的红色方块，并将方块抬离桌面。**

它不是最终研究任务，而是仿真与数据管线的单元测试。完整动作只有：

```text
接近方块上方
    ↓
下降到夹爪抓取高度
    ↓
闭合夹爪
    ↓
垂直抬升
```

robosuite 的成功条件是方块中心高度超过桌面高度 4 cm。当前配置为：

- 一台 Panda 和 PandaGripper；
- 20 Hz 策略/动作频率；
- 7 维动作：`Δx, Δy, Δz, Δrx, Δry, Δrz, gripper`；
- `+1` 表示闭合夹爪，`-1` 表示张开；
- 全局相机：`agentview`；
- 局部相机：`robot0_eye_in_hand`；
- 本体状态：7 个手臂关节位置 + 2 个夹爪关节位置；
- 语言指令：`Lift the red cube above the table.`

这个任务能检查：

1. 相机是否方向正确、时间同步；
2. 末端空间动作是否能真实驱动机器人；
3. 夹爪动作符号和接触高度是否正确；
4. observation/state/action 是否属于同一个时间步；
5. episode 是否能根据 MuJoCo state 精确回放；
6. 数据能否被 COMMVLA 的 HDF5 adapter 读取。

## 脚本专家和人工示范分别做什么

脚本专家不是随机动作。它使用 MuJoCo 中的方块和末端真值，通过状态机生成动作。
它适合：

- 验证环境与记录器；
- 快速生成成功基线；
- 大规模随机种子测试；
- 检查任务成功条件。

脚本专家的局限是轨迹单一，而且抓取高度、接触和避障需要针对物理模型调试。
本项目第一次脚本测试确实因为夹爪高度错误而夹空；将 EEF 的几何语义修正为
“两指之间的 grip site”后，三个不同随机种子均成功。

人工遥操作的价值是产生：

- 不同的接近路径；
- 细小修正动作；
- 等待、犹豫和恢复；
- 对视觉反馈更自然的动作分布。

第一轮建议保存 3 条脚本成功轨迹和 3–5 条人类成功轨迹。这个数量只用于格式、
回放和小数据过拟合检查，不能用于评价模型泛化能力。

## 已生成的脚本测试

```bash
source .venv/bin/activate

python scripts/collect_scripted_lift.py \
  --episodes 3 \
  --seed 1300 \
  --image-size 256 \
  --backend egl \
  --egl-device 7 \
  --output datasets/lift_scripted_test_3.h5
```

当前三条轨迹分别为 75、69、75 步，全部成功。

验证、生成 COMMVLA 输入配置和统计：

```bash
python scripts/prepare_commvla.py \
  datasets/lift_scripted_test_3.h5 \
  --output-directory artifacts/commvla_lift_test_3
```

状态回放：

```bash
python scripts/replay_lift_dataset.py \
  datasets/lift_scripted_test_3.h5 \
  --trajectory trajectory_000001 \
  --backend egl \
  --egl-device 7 \
  --output artifacts/replay/lift_scripted_test_3_ep1.mp4
```

## 在服务器启动人类遥操作

先用 `nvidia-smi` 查看空闲 GPU。下面的 `7` 只是示例，负载变化后可以换成其他编号：

```bash
cd /data/private/user7/projects/MoJuCo-sim
source .venv/bin/activate

python scripts/teleop_lift_web.py \
  --backend egl \
  --egl-device 7 \
  --image-size 256 \
  --port 8765 \
  --output datasets/lift_human_success.h5
```

服务只监听服务器的 `127.0.0.1`，不会直接开放到局域网或公网。

## 在 Mac 建立 SSH tunnel

Mac 再开一个终端，使用你平时登录服务器的 SSH 主机名或 SSH config 别名：

```bash
ssh -N -L 8765:127.0.0.1:8765 <你的服务器 SSH 地址或别名>
```

然后在 Mac 浏览器打开：

```text
http://127.0.0.1:8765
```

如果 Mac 本地的 8765 已被占用，可以把左侧端口换成 8876：

```bash
ssh -N -L 8876:127.0.0.1:8765 <SSH 地址或别名>
```

浏览器相应打开 `http://127.0.0.1:8876`。

## 浏览器操作

页面同时显示全局相机和腕部相机。先单击页面一次，让浏览器获得键盘焦点。

```text
A / D：沿 base frame 的 −X / +X
W / S：沿 base frame 的 +Y / −Y
R / F：上升 / 下降
Space：切换夹爪张开 / 闭合

U / O：末端 roll
I / K：末端 pitch
J / L：末端 yaw
```

Lift 不需要旋转，第一轮只使用 `A/D/W/S/R/F/Space`。

推荐操作顺序：

1. 点击 `Start new recording`。环境会 reset，夹爪张开并开始记录。
2. 用全局画面把夹爪移动到红色方块正上方。
3. 用 `F` 缓慢下降；腕部画面用于确认对准。
4. 按一次 `Space` 闭合夹爪，等待约半秒。
5. 用 `R` 垂直抬升。
6. 达到成功高度后，轨迹会自动保存并停止记录。
7. 点击 `Start new recording` 开始下一条。

如果轨迹明显失败，点击 `Discard + reset`，不要点击 `Save now`。`Save now`
用于保留诊断失败轨迹；训练转换器会拒绝混有失败 episode 的 HDF5，防止误训练。

网络输入超过 0.5 秒没有心跳时，服务端会把末端位移和旋转动作置零；夹爪状态保持。
页面失焦时浏览器也会主动释放所有移动按键。

## HDF5 与 COMMVLA

每条轨迹直接包含 COMMVLA 当前 N-agent adapter 读取的路径：

```text
trajectory_xxxxxx/
├── actions/panda-0                       [T, 7]
├── obs/agent/panda-0/qpos                [T, 9]
├── obs/sensor_data/agentview/rgb         [T, H, W, 3]
└── obs/sensor_data/robot0_eye_in_hand/rgb [T, H, W, 3]
```

同时保存额外的可回放字段：

```text
sim/states
sim/final_state
timestamps
rewards
dones
successes
task_stage
```

`prepare_commvla.py` 生成：

- `mujoco_lift_input.json`：任务、agent 角色和相机映射；
- `mujoco_lift_statistics.npz`：与目标仓库逻辑一致的 1%/99% 分位数；
- 原 HDF5 不复制图像，直接作为训练输入。

当前只验证 N-agent HDF5 入口。双臂数据稳定后再实现 TwinVLA RLDS 转换，因为目标
仓库的 RLDS 细节来自其固定版本的外部 TwinVLA，而不是该仓库内部定义。

