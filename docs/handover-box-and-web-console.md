# 双臂彩色方块交接与网页采集台

## 场景定义

第一个双臂任务为 `ColoredHandoverBox`：

1. 两台独立 Panda 通过 `NullMount` 直接固定在加宽桌面上，位于发送侧和接收侧并面对彼此。
2. 桌面发送侧出现红、绿、蓝三个可抓取方块。
3. 接收侧固定三个红、绿、蓝的开口盒。
4. 每次 reset 随机指定一种目标颜色，并轻微扰动三个方块的位置和朝向。
5. Panda 0 抓取目标方块并送到桌面中间。
6. Panda 1 真正夹住方块后，Panda 0 释放。
7. Panda 1 将方块放进同色盒。

成功判定同时要求：

- 发送臂曾抓住目标方块；
- 接收臂随后抓住目标方块；
- 接收臂抓住时发送臂已经释放，从而形成真实交接证据；
- 目标方块最后位于同色盒内部。

因此，方块因碰撞偶然掉进盒子、由发送臂直接放入盒子，或者放入错误颜色的盒子，
都不会被标成成功。

环境使用 20 Hz 控制频率。每台 Panda 的动作是
`Δx, Δy, Δz, Δrx, Δry, Δrz, gripper` 共 7 维，双臂同步动作为 14 维。
每台 Panda 的本体状态是 7 个手臂关节位置和 2 个夹爪关节位置，共 9 维。

当前桌面宽度为 1.50 m，两基座位于 `y=-0.62 m` 和 `y=+0.62 m`，底面高度与
桌面 `z=0.80 m` 对齐。默认姿态下两末端位于 `y≈±0.163 m`，间距约 0.326 m：
中央具有共同可达区域，同时不会在 reset 后立刻发生夹爪碰撞。

## 在服务器启动

进入项目并启动统一网页采集台：

```bash
cd /data/private/user7/projects/MoJuCo-sim
source .venv/bin/activate

python scripts/teleop_web.py \
  --backend egl \
  --egl-device 0 \
  --image-size 512 \
  --motion-tail-seconds 0.30 \
  --gripper-tail-seconds 0.50 \
  --port 8765 \
  --dataset-dir datasets
```

GPU 编号 `0` 只是命令示例。每次启动前用 `nvidia-smi` 选择空闲 GPU。
网页服务默认只监听服务器 `127.0.0.1`，不会暴露到公网。

## Mac 上如何连接

可以只用一个 Mac 终端。通过带端口转发的普通 SSH 登录服务器：

```bash
ssh -L 8765:127.0.0.1:8765 <服务器地址或 SSH config 别名>
```

登录后直接在该 SSH 会话里运行上面的 `teleop_web.py`。保持终端不关闭，再在 Mac
浏览器打开：

```text
http://127.0.0.1:8765
```

如果希望把隧道和运行命令分开，也可以在第一个 Mac 终端只运行：

```bash
ssh -N -L 8765:127.0.0.1:8765 <服务器地址或别名>
```

再用第二个终端普通 SSH 登录并启动服务。两种方法效果相同。Mac 无需安装 MuJoCo、
CUDA 或 Python 仿真库；浏览器只显示 JPEG 画面并发送按键状态。

## 任务大厅和遥操作

首页包含：

- 单臂 `Panda Lift`；
- 双臂 `彩色方块交接入盒`；
- 多臂任务占位。多臂具体任务稳定前不创建空实现。

进入双臂任务后，全局相机、发送臂腕部相机、接收臂腕部相机同时显示。
全局视角位于任务区左侧，两路腕部相机在右侧上下排列；待确认轨迹、已保存数据和
回收站位于任务控制区下方。网页目标刷新率为 10 FPS，
仿真控制频率仍为 20 Hz，两者互不等同。

按钮命令会显示递增编号。例如点击开始后，页面先显示“命令 #2 已排队”，服务器完成
环境 reset 后再显示“最近执行：#2 start”和“已就绪，等待输入”。重建 EGL 场景通常需要几秒，
这段时间不应重复点击。如果编号一直处于排队状态，则检查启动服务的终端是否仍有输出，
并重新用 `nvidia-smi` 选择负载较低的 GPU。

通用控制：

```text
A / D：桌面 X 轴负向 / 正向
W / S：桌面 Y 轴正向 / 负向
R / F：上升 / 下降
Space：切换当前机械臂夹爪开合

U / O：末端 roll
I / K：末端 pitch
J / L：末端 yaw
```

两台机器人底座方向相反。服务器已经把上述共同的桌面坐标按键转换到各自 base
frame，所以切换机械臂后不需要自行反转方向。

双臂切换和阶段标签：

```text
1：控制 Panda 0（左侧发送臂）
2：控制 Panda 1（右侧接收臂）
Tab：在两臂间切换
```

页面上的三个阶段按钮会把 `0/1/2` 写入每个时间步的 `task_stage`：

1. 左臂抓取；
2. 中间交接；
3. 右臂入盒。

建议第一次慢速操作：

1. 点击“开始新轨迹”，先确认页面给出的目标颜色。
2. 保持阶段 ① 和 Panda 0，用全局图像移动到目标方块上方，再参考发送臂腕部图像下降。
3. 按一次空格闭合 Panda 0，等待约半秒，抬起并移动到桌面中间。
4. 切换阶段 ②，再按 `2` 控制 Panda 1。Panda 0 会保持姿态和闭合状态。
5. Panda 1 对准方块并按空格闭合；等待稳定接触。
6. 按 `1` 切回 Panda 0，按空格释放；再按 `2` 回到 Panda 1。
7. 切换阶段 ③，把 Panda 1 移到同色盒上方，下降并按空格释放。

遥操作网络心跳超过 0.55 秒时，服务端自动把位移和旋转置零，但保持两只夹爪的
开合状态。页面失焦也会释放移动按键。

## 事件触发录制

点击“开始新轨迹”后，采集器进入 armed 状态，但不会把思考期间的每个静止仿真步
都写进 HDF5：

- 按住位移或旋转键时，以 20 Hz 保存；
- 松开运动键后继续保存 0.30 秒（6 步），保留惯性和短暂接触变化；
- 切换夹爪时保存该动作，并继续保存 0.50 秒（10 步）；
- 阶段变化和首次成功事件至少保留一帧；
- 两臂稳定且没有新输入时，仿真继续运行，但不增加“有效步”计数。

页面显示“正在采集有效动作”时才会增加有效步数；显示“已就绪，等待输入”时，
压缩等待时间仍会累计。这不是网络失联。无有效动作时点击结束不会生成空轨迹。

HDF5 中的 `timestamps` 是压缩等待后的均匀 20 Hz 模型时间；`wall_timestamps`
保留从开始录制起的真实操作时间，`capture_reason` 记录该帧由运动、尾录、夹爪、
阶段或成功中的哪种事件触发。

## 为什么不能把两只机械臂分别保存

操作可以分阶段完成，但数据不能分成两条独立时间线。每个被事件触发器保留的
20 Hz 有效时间步都会同步保存：

```text
actions/panda-0
actions/panda-1
obs/agent/panda-0/qpos
obs/agent/panda-1/qpos
三路同时间步图像
```

当只控制一只机械臂时，另一只的末端增量为零、夹爪状态保持；这些保持动作同样写入。
这样 COMMVLA 才能在同一时刻看到两个 agent 的状态、视觉和动作。`task_stage` 和
`active_arm` 可以在分析时还原你当时正在操作哪一只机械臂。

## 检查、保存、增加和删除数据

采集结束或成功条件触发后，轨迹先进入“待确认”状态，不会立即写入训练 HDF5：

1. 用播放按钮或滑块回看全局加两路腕部图像。
2. 确认轨迹后点击“确认保存到 HDF5”。
3. 明显失败则点击“丢弃待确认轨迹”。
4. 点击“开始新轨迹”就是向当前任务数据集继续添加 episode。

已保存列表支持随时回放。点击删除时，episode 会先复制到
`handover_box_human.trash.h5`，确认副本落盘后才从训练文件移除。回收站的“恢复”
会把它重新加入训练 HDF5。因此网页删除不是不可恢复删除。

双臂默认数据文件：

```text
datasets/handover_box_human.h5
```

失败轨迹允许人工确认保存，便于诊断和后续研究，但 COMMVLA 训练资产生成命令默认
拒绝混有失败轨迹的数据集，防止无意间训练错误示范。诊断时可显式使用
`--allow-failures`。

## HDF5 与 COMMVLA

每条双臂轨迹的训练字段为：

```text
trajectory_xxxxxx/
├── actions/panda-0                              [T, 7]
├── actions/panda-1                              [T, 7]
├── obs/agent/panda-0/qpos                       [T, 9]
├── obs/agent/panda-1/qpos                       [T, 9]
├── obs/sensor_data/agentview/rgb                [T, H, W, 3]
├── obs/sensor_data/robot0_eye_in_hand/rgb       [T, H, W, 3]
└── obs/sensor_data/robot1_eye_in_hand/rgb       [T, H, W, 3]
```

同时记录：

```text
sim/states
sim/final_state
timestamps
rewards
dones
successes
task_stage
active_arm
wall_timestamps
capture_reason
```

采集到成功示范后，验证并生成 COMMVLA 相机/角色配置和 1%/99% 分位数：

```bash
python scripts/prepare_handover_commvla.py \
  datasets/handover_box_human.h5 \
  --output-dir artifacts/commvla_handover_box
```

生成：

- `handover_box_input.json`：两个 agent 的角色、全局相机和两路局部相机映射；
- `handover_box_statistics.npz`：形状为 `[2, 9]` 的 proprio 统计和 `[2, 7]` 的动作统计。

该 HDF5 已按 `chenglong-2026-INFOCOM-code-CommVLA` 当前
`RoboFactoryNAgentDataset` 的路径直接组织，不需要复制或重编码图像。参考仓库在
实现和验证过程中保持只读。

## Panda 与实验室 Piper 的关系

Panda 不是研究设定的硬性要求。第一阶段选择 Panda，是因为 robosuite 1.5.2 已经
提供完整的 Panda MJCF、夹爪、腕部相机、动力学参数和 `OSC_POSE` 控制器，适合先验证
多臂同步数据链路。

如果最终需要部署到实验室 Piper，正式数据环境应优先采用 Piper。否则 Panda 与
Piper 在自由度、连杆尺度、关节范围、夹爪行程和相机外参上的差异，会增加明显的
sim-to-real gap。

当前服务器已有 RoboTwin 的 AgileX Piper 资产：

```text
cl_2026_INFOCOM/external/benchmarks/RoboTwin/assets/embodiments/piper/
├── piper.urdf
├── meshes/
├── collision_piper.yml
└── config.yml
```

但 robosuite 的内置机器人注册表没有 Piper，所以不能只把 `robots="Panda"` 改成
`robots="Piper"`。正式适配需要：

1. 核对实验室实机的 Piper 型号、固件和夹爪版本；
2. 将 URDF/网格整理为可发布的 MuJoCo MJCF，并保留许可证说明；
3. 定义 6 轴关节、执行器、碰撞体、末端 site、双指夹爪和腕部相机；
4. 标定关节零位、限制、控制增益及桌面安装外参；
5. 接入 robosuite 控制器并重新验证抓取、碰撞和 HDF5 状态维度；
6. 最后才连接官方 `piper_sdk` / CAN 实机接口。

当前修正版 Panda 场景用于继续验证网页采集和双臂任务逻辑，不应被表述为最终的
Piper sim-to-real 模型。
