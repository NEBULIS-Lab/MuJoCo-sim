# MuJoCo 多机械臂仿真

**User:** Anonymous  
**Created:** 7/28/2026 21:02:39  
**Updated:** 7/28/2026 21:46:57  
**Exported:** 7/29/2026 11:20:43  
**Link:** [https://chatgpt.com/g/g-p-6a17eff4555c8191a1a1d9758bf043a8-tong-xin-ji-jie-bi/c/6a68a839-0f0c-83ea-833f-1313f2789e5e](https://chatgpt.com/g/g-p-6a17eff4555c8191a1a1d9758bf043a8-tong-xin-ji-jie-bi/c/6a68a839-0f0c-83ea-833f-1313f2789e5e)  

## Prompt:
2026/7/28 21:02:38

我想构建自己的双臂，三臂，四臂任务的数据集，用来仿真训练，似乎是可以使用MUJOCO来帮助实现的，你能告诉我怎么进行吗？我也会在codex中进行这个任务，但是我希望先了解一下这个过程和内容

## Response:
2026/7/28 21:02:39

我会先把 MuJoCo 在这件事里扮演的角色讲清楚，再给你一条能落到 Codex 的“双臂→三臂→四臂”数据集构建路线。重点会放在任务环境、数据采集、数据格式、训练接口和评测设计。

先给你一个核心判断：**MuJoCo 负责物理与渲染，但“数据集”还需要你额外实现任务环境、专家/遥操作采集器、轨迹记录器和格式转换器。** 对你的研究，最合适的不是直接裸写 MuJoCo，而是用 **MuJoCo + robosuite** 搭环境，再保留一个独立的数据层。官方 robosuite 已支持同一仿真中实例化多个带唯一 ID 的机器人，但三臂、四臂协作任务需要你自己定义。

> **搜索多臂任务数据集创建方法**
>
> [模型编辑 - MuJoCo 文档](https://docs.mujoco.cn/en/stable/programming/modeledit.html)
> [Welcome to robosuite’s documentation! — robosuite 1.5 documentation](https://robosuite.ai/docs/index.html)
> [Dataset Contents and Visualization — robomimic 0.5 documentation](https://robomimic.github.io/docs/tutorials/dataset_contents.html)
> [LeRobot - Hugging Face](https://huggingface.co/docs/lerobot/index)
> [Modeling - MuJoCo Documentation](https://mujoco.readthedocs.io/en/stable/modeling.html)
> [Using LeRobotDataset - LeRobot Documentation](https://dctx-team.github.io/lerobot-zh/en/lerobot-dataset-v3/)
> [GitHub - ARISE-Initiative/robosuite: robosuite: A Modular Simulation ...](https://github.com/ARISE-Initiative/robosuite)
> [robomimic基础教程（四）——开源数据集 - 技术栈](https://jishuzhan.net/article/1839835618008371202)
> [Dataset Format and Structure | huggingface/lerobot | DeepWiki](https://deepwiki.com/huggingface/lerobot/2.1-dataset-format-and-structure)
> [【学习】robosuite安装配置添加自定义机械臂教程](https://www.cnblogs.com/quantoublog/articles/19568250)
> [具身智能 | Robosuite使用教程（一） - 知乎](https://zhuanlan.zhihu.com/p/6621264369)
> [robomimic基础教程（四）——开源数据集-CSDN博客](https://blog.csdn.net/qq_28912651/article/details/142320250)
> [MuJoCo — Advanced Physics Simulation](https://mujoco.org/)
> [robosuite: robosuite：机器人学习的模块化仿真框架和基准](https://gitee.com/jiaojianjun-com/robosuite)
> [LeRobot · Hugging Face - Hugging Face 文档](https://hugging-face.cn/docs/lerobot/index)
> [robosuite: A Modular Simulation Framework and Benchmark for Robot Learning](https://arxiv.org/abs/2009.12293)
>
> **已搜索 16 个网站**
>
> 
>
> **分析任务设计**
>
> 我正在考虑如何整合MuJoCo与Robosuite，设计多臂任务，并解决数据集问题。同时需要注意动作规划、环境配置以及任务支持的机器人数量。
>
> **分析任务设计**
>
> 
>
> **设计任务框架**
>
> 我正在考虑任务的不同类型和定义评估标准，还需要明确数据结构和任务分割，以确保模型一致性和对任务的充分验证。
>
> **设计任务框架**
>
> 
>
> **正在搜索网页**
>
> [Robots — robosuite 1.5 documentation](https://robosuite.ai/docs/modules/robots.html)
> [Dataset Contents and Visualization — robomimic 0.5 documentation](https://robomimic.github.io/docs/tutorials/dataset_contents.html)
> [LeRobot · Hugging Face](https://huggingface.co/docs/lerobot/index)
> [Modeling - MuJoCo Documentation](https://mujoco.readthedocs.io/en/stable/modeling.html)
>
> **已搜索 4 个网站**
>
> 
>
> 思考了 1m 30s

可以。**MuJoCo 很适合充当多机械臂数据集的物理仿真底座**，但它本身不会直接替你生成“可训练的数据集”。完整系统应当是一条数据生产流水线：

> 任务定义 → 多机械臂场景 → 控制/专家策略 → 轨迹采集 → 数据质检 → 格式转换 → 模型训练与评测

对你目前的 CommVLA 研究，我更推荐下面的技术组合：

- **MuJoCo**：物理、碰撞、接触、传感器和渲染。
- **robosuite**：机械臂模型、控制器、多机器人管理、任务环境、遥操作和数据采集。
- **你自己设计的中间数据格式**：保存多智能体观测、动作、通信和任务信息。
- **LeRobotDataset / robomimic 导出器**：分别服务 VLA 训练和传统模仿学习基线。

MuJoCo 支持模块化 MJCF 场景构建；robosuite 则在 MuJoCo 上提供了更高层的机器人和任务抽象。同一仿真中可以实例化多个相同机械臂，每个机器人都会获得唯一 ID，并分别处理自己的动作和观测。([MuJoCo](https://mujoco.readthedocs.io/en/stable/modeling.html))

---

# 一、首先明确你要构建的是什么

你的目标更适合定义为：

> **多个独立 SingleVLA 机械臂组成的协作系统**，而不是一个传统意义上的“双臂机器人”。

两者有本质差别：

- 传统双臂机器人：两个手臂属于一个机器人本体，通常由一个集中式策略控制。
- 你的系统：每个机械臂都是一个独立 agent，有自己的相机、状态、动作和模型，只通过通信进行协作。

因此，在仿真中应当创建：

```text
Agent 0: Panda / UR5 / 其他机械臂
Agent 1: 相同的机械臂
Agent 2: 相同的机械臂
Agent 3: 相同的机械臂
```

每个 agent 都应有：

```text
local observation
local proprioception
local controller
local action
local camera
communication interface
```

而环境还可以额外保存一个：

```text
privileged global state
```

这个全局状态只用于生成专家轨迹、计算奖励和评测，不能偷偷作为分布式策略输入。

---

# 二、推荐的整体架构

建议把系统分成六层。

## 1. MuJoCo 场景层

负责：

- 机械臂模型；
- 桌子、容器、工具和操作物体；
- 碰撞和接触；
- 摄像机；
- 关节和末端执行器状态；
- 仿真状态保存和恢复。

场景可以采用模块化 MJCF：

```text
scene.xml
robot.xml
table.xml
objects.xml
cameras.xml
```

不过不要直接把同一个 `robot.xml` 简单 `include` 四次，因为 MuJoCo 元素名称需要唯一，同一文件重复包含也可能导致命名冲突。使用 robosuite 的机器人实例化机制，或者利用 MJCF 的复制、前缀和程序化模型编辑机制，会更加稳妥。([MuJoCo](https://mujoco.readthedocs.io/en/stable/modeling.html))

## 2. 多机械臂环境层

实现类似：

```python
class MultiArmManipulationEnv:
    def reset(self):
        ...

    def step(self, actions):
        ...

    def get_agent_observation(self, agent_id):
        ...

    def check_success(self):
        ...
```

robosuite 的环境会把输入动作分发到各个机器人，每个机器人再通过自己的控制器将高层动作转换成底层力矩；随后环境收集各机器人的观测并返回。([robosuite](https://robosuite.ai/docs/modules/robots.html))

## 3. 任务生成层

不要给双臂、三臂、四臂分别手工写完全不同的任务。

更好的做法是定义一个**随机械臂数量参数化的任务族**：

```python
task = SequentialHandover(
    num_agents=N,
    object_type="red_cube",
    topology="chain",
)
```

当：

```text
N = 2：A → B → goal
N = 3：A → B → C → goal
N = 4：A → B → C → D → goal
```

这样你才能真正研究：

> 同一个任务和同一个模型，能否随着 agent 数量增加而扩展。

## 4. 控制和专家层

建议开始时统一使用末端空间控制，而不是直接控制关节力矩。

每个机械臂的动作可以定义为：

```text
Δx, Δy, Δz,
Δroll, Δpitch, Δyaw,
gripper
```

也就是每臂 7 维。robosuite 当前提供 OSC、IK、关节位置、关节速度和关节力矩等控制方式，末端位姿控制更方便编写专家策略和进行遥操作。([robosuite](https://robosuite.ai/docs/demos.html))

对于四个机械臂，动作可以表示成：

```text
action.shape = [4, 7]
```

而不是一开始就硬编码为 28 维向量。训练时可以再展平，或者使用 agent token 表示。

## 5. 数据记录层

记录每一步：

```text
observation_t
action_t
next_observation_t
reward_t
done_t
timestamp_t
communication_t
```

同时保存：

```text
initial simulator state
MuJoCo model configuration
task seed
object placement seed
camera parameters
success/failure reason
```

robosuite 自带轨迹记录和人类演示采集功能，可以保存 MuJoCo 状态和动作，并支持通过键盘、SpaceMouse、DualSense 和 MuJoCo GUI 进行遥操作。([robosuite](https://robosuite.ai/docs/algorithms/demonstrations.html))

## 6. 数据转换层

不要让原始数据直接绑定到某一个模型代码库。

建议先保存一份自己的标准数据，再分别导出为：

```text
Raw MultiArm Dataset
├── Robomimic HDF5
├── LeRobotDataset
└── RLDS / Open X-Embodiment-compatible
```

robomimic 使用带有轨迹、状态、动作、观测和环境元数据的 HDF5 结构，并提供数据集检查和轨迹回放工具。([robomimic](https://robomimic.github.io/docs/tutorials/dataset_contents.html))

LeRobotDataset 当前采用 Parquet 保存状态和动作，用 MP4 或图像保存视觉数据，并支持多相机、时间戳、任务文本、统计信息和回合级元数据，更适合后续 VLA 训练。([GitHub](https://github.com/huggingface/lerobot))

RLDS 则适合未来与 Open X-Embodiment 风格的数据和模型兼容；OXE 将数据表示为 episode 序列，并结合 RGB 观测、任务文本和机器人动作。([GitHub](https://github.com/google-deepmind/open_x_embodiment))

---

# 三、最适合你开始的任务：N-Arm Relay

我认为你的第一个任务不应该是复杂装配，而应当是：

> **N 个机械臂顺序传递一个物体。**

例如：

```text
Instruction:
"Pass the red block along the robot chain and place it in the blue bin."
```

场景布局：

```text
Robot 0        Robot 1        Robot 2        Robot 3
   |              |              |              |
Start object   Handover 1     Handover 2       Goal
```

双臂时：

```text
Robot 0 抓取 → Robot 1 接收 → 放入目标区
```

三臂时：

```text
Robot 0 → Robot 1 → Robot 2 → 目标区
```

四臂时：

```text
Robot 0 → Robot 1 → Robot 2 → Robot 3 → 目标区
```

这个任务有几个优点：

1. 同一个任务生成器可以自然扩展到 2、3、4 臂。
2. 每个机器人都有清晰角色。
3. 可以明确构造通信需求。
4. 可以定义稳定的阶段标签。
5. 专家策略容易用状态机实现。
6. 后面可以增加随机角色和动态重规划。

专家状态机可以写成：

```text
APPROACH
GRASP
LIFT
MOVE_TO_HANDOVER
WAIT_FOR_RECEIVER
RELEASE
RETREAT
```

接收机械臂则是：

```text
WAIT_FOR_SENDER
APPROACH_HANDOVER
GRASP
CONFIRM_GRASP
MOVE_TO_NEXT
```

这比一开始让强化学习自己探索抓取、传递和配合稳定得多。

---

# 四、任务类型应该怎样逐步扩展

在完成 Relay 之后，再增加下面几类任务。

## 1. 并行独立任务

每个机械臂处理不同物体：

```text
Robot 0：红色物体分类
Robot 1：蓝色物体分类
Robot 2：绿色物体分类
Robot 3：黄色物体分类
```

这类任务主要检查多 agent 执行和场景扩展，不一定强依赖通信。

## 2. 顺序依赖任务

例如：

```text
Robot 0 打开盒子
Robot 1 取出零件
Robot 2 清理遮挡物
Robot 3 完成装配
```

后续 agent 必须等待前序子任务完成。

## 3. 共同操作物体

例如：

- 两臂抬长板；
- 三臂稳定柔性物体；
- 四臂共同搬运大型物体；
- 一臂固定、一臂插入、一臂旋转、一臂检测。

这类任务的物理接触更复杂，建议放到后期。

## 4. 动态角色分配

环境只给出目标：

```text
"Place all components into the assembly area."
```

系统需要自己决定：

```text
谁抓哪个物体
谁负责传递
谁负责装配
谁空闲等待
```

这才能进一步体现多 agent 协作和可扩展性。

## 5. 通信必要型任务

这是与你的论文最相关的一类。

例如：

- Robot 0 能看到目标颜色，但看不到物体；
- Robot 1 能看到物体，但看不到目标；
- Robot 2 掌握任务指令；
- Robot 3 执行最终放置。

不通信就无法完成任务。

否则，审稿人可能会质疑：

> 多机械臂虽然传了信息，但每个机器人根据自己的视觉也能完成，通信是否真的必要？

---

# 五、数据集中具体应保存什么

建议每个 episode 至少包含以下结构。

```text
episode/
├── metadata
│   ├── episode_id
│   ├── task_name
│   ├── task_family
│   ├── language_instruction
│   ├── num_agents
│   ├── robot_types
│   ├── random_seed
│   ├── success
│   └── failure_reason
│
├── observations
│   ├── global_camera
│   ├── agent_0
│   │   ├── wrist_rgb
│   │   ├── local_rgb
│   │   ├── joint_position
│   │   ├── joint_velocity
│   │   ├── end_effector_pose
│   │   └── gripper_state
│   ├── agent_1
│   ├── agent_2
│   └── agent_3
│
├── actions
│   ├── agent_0_action
│   ├── agent_1_action
│   ├── agent_2_action
│   └── agent_3_action
│
├── communication
│   ├── sender
│   ├── receiver
│   ├── message_type
│   ├── send_timestamp
│   ├── arrival_timestamp
│   ├── payload_bytes
│   ├── dropped
│   ├── latency
│   ├── age_of_information
│   ├── communication_path
│   └── synchronization_layers
│
└── privileged
    ├── mujoco_state
    ├── object_poses
    ├── contact_states
    ├── task_stage
    └── collision_information
```

其中，`privileged` 数据只用于：

- 专家控制器；
- 奖励计算；
- 阶段标注；
- 离线分析；
- 结果评测。

不能默认输入到 VLA。

---

# 六、针对 CommVLA，通信数据要单独设计

一般机器人数据集只保存 observation 和 action，但你的工作必须额外保存通信轨迹。

建议每条消息保存：

```python
{
    "sender": 0,
    "receiver": 1,
    "step": 124,
    "path": "common_hidden",
    "layer": 12,
    "payload_bytes": 32768,
    "send_time": 6.20,
    "arrival_time": 6.24,
    "latency": 0.04,
    "dropped": False,
    "staleness": 0.04,
    "compression": "NSPR",
}
```

这里需要区分两类内容。

### 基础数据集

保存：

- 图像；
- proprioception；
- 动作；
- 任务文本；
- agent 身份；
- 仿真状态；
- 通信事件和网络参数。

### 模型相关缓存

单独保存：

- hidden states；
- KV cache；
- action token；
- common-hidden workspace；
- 压缩前后 payload。

不要把所有 hidden states 直接塞进主要数据集。它们体积巨大，而且绑定特定模型版本、层数和 checkpoint。

更好的结构是：

```text
dataset/
├── base_episodes/
└── feature_cache/
    ├── checkpoint_hash/
    ├── layer_00/
    ├── layer_02/
    └── layer_04/
```

每个 feature cache 必须记录：

```text
model checkpoint hash
tokenizer version
layer index
precision
compression method
```

这样以后更换 VLA，不需要重做整个 MuJoCo 数据集。

---

# 七、动作表示一定要提前统一

这是多机械臂数据集中非常容易出问题的地方。

建议同构阶段统一使用：

```text
每臂：
6D 末端位姿增量 + 1D gripper
```

并统一规定：

- 平移是在机械臂 base frame 中表示；
- 旋转采用 axis-angle，避免欧拉角奇异；
- gripper 范围统一为 `[-1, 1]` 或 `[0, 1]`；
- 所有机械臂使用相同动作顺序；
- 每一帧有准确 timestamp；
- 明确 action 是 absolute、delta 还是 velocity。

OXE 中也明确区分了绝对动作、增量动作和速度动作，因此你自己的数据格式里必须记录动作语义，而不能只保存一串数字。([GitHub](https://github.com/google-deepmind/open_x_embodiment))

对于可变数量机械臂，可以采用：

```text
action: [max_agents, action_dim]
agent_mask: [max_agents]
```

例如最多四臂：

```text
双臂：
agent_mask = [1, 1, 0, 0]

三臂：
agent_mask = [1, 1, 1, 0]

四臂：
agent_mask = [1, 1, 1, 1]
```

这种方式容易与现有 Transformer 和 VLA 批训练代码结合。

---

# 八、演示数据怎样采集

建议依次使用三种方式。

## 第一阶段：脚本专家

先用 MuJoCo 的完整状态编写确定性的专家：

```text
获取物体位姿
生成抓取点
移动末端
闭合夹爪
移动到交接点
等待另一机械臂
释放物体
```

优点是：

- 快；
- 成功率高；
- 可大规模并行；
- 能检查环境和数据记录是否正确；
- 容易生成阶段标签。

第一版数据集应主要依赖脚本专家。

## 第二阶段：人工遥操作

脚本专家通常太平滑、太理想，人工遥操作可以增加：

- 动作多样性；
- 修正动作；
- 等待和犹豫；
- 不同抓取方式；
- 接近真实操作的轨迹分布。

robosuite 已经提供键盘、SpaceMouse、DualSense 和 GUI 遥操作工具，也支持多相机观察和演示保存。([robosuite](https://robosuite.ai/docs/algorithms/demonstrations.html))

三臂和四臂遥操作可以先采用：

```text
按键切换当前控制机械臂
```

或者：

```text
一个操作者控制发送方
另一个操作者控制接收方
```

不需要一开始就同时人工控制四个机械臂。

## 第三阶段：策略 rollout

训练出初始模型后，使用模型自己执行，并记录：

- 成功轨迹；
- 失败轨迹；
- 恢复轨迹；
- 通信失败轨迹；
- 碰撞轨迹；
- 长时间等待轨迹。

这类数据可以用于 DAgger、失败恢复和通信鲁棒性训练。

---

# 九、必须同时保存状态和视觉数据

robosuite 的演示格式会保存 MuJoCo 状态和动作，并可以根据状态重新渲染不同摄像机观测。官方文档也特别提示，仅靠动作重放会因数值误差发生漂移，不同机器之间不能保证严格复现，因此回放时更可靠的方法是直接恢复仿真状态。([robosuite](https://robosuite.ai/docs/algorithms/demonstrations.html))

所以建议同时保存：

```text
1. MuJoCo simulator state
2. policy observation
3. action
4. rendered camera stream
```

其中：

- MuJoCo state 用于精确复现和重新渲染；
- RGB 图像用于训练；
- action 用于行为克隆；
- metadata 用于任务和条件筛选。

---

# 十、数据集切分不能只随机分 episode

你的论文真正有价值的切分应包括：

## 基础切分

```text
Train：训练物体位置和场景
Validation：新随机种子
Test：新物体位置、纹理和光照
```

## 任务泛化切分

```text
Seen task templates
Unseen task templates
Unseen language paraphrases
Unseen object combinations
```

## 机械臂数量泛化

这是最重要的：

```text
Train: 2 arms
Test: 3 arms and 4 arms
```

或者：

```text
Train: 2 and 3 arms
Test: 4 arms
```

这能直接回答：

> 模型是否真的具有 agent-number scalability？

## 通信泛化

```text
Train: stable network
Test:
- bandwidth limitation
- latency
- packet loss
- stale information
- asymmetric links
- changing topology
```

## 拓扑泛化

```text
Chain
Star
Fully connected
Dynamic neighbor graph
```

这样数据集不仅是机械臂任务数据集，也是通信协作 benchmark。

---

# 十一、需要记录的评测指标

任务层面：

```text
Task success rate
Subtask success rate
Time to completion
Object drop rate
Collision count
Maximum contact force
```

协作层面：

```text
Per-agent idle time
Workload balance
Handover waiting time
Synchronization error
Role allocation accuracy
```

通信层面：

```text
Total transmitted bytes
Bytes per agent
Messages per episode
End-to-end latency
Packet loss robustness
Information staleness
Success under bandwidth limits
```

扩展性层面：

```text
Success versus number of agents
Latency versus number of agents
Communication versus number of agents
Inference time versus number of agents
```

最终最好画出：

```text
N = 2, 3, 4, ...
```

对应的成功率、通信量和执行时间曲线。

---

# 十二、仿真随机化和 Sim-to-Real

基础任务跑通后，再加入：

- 物体位置随机化；
- 物体尺寸和质量随机化；
- 摩擦系数随机化；
- 相机位置随机化；
- 纹理和光照随机化；
- 关节噪声；
- 图像噪声；
- 传感器延迟；
- 控制延迟。

robosuite 提供视觉 domain randomization，也支持通过 Observable 模拟传感器噪声、采样频率和延迟；动力学参数还可以通过相应的 modder 进行调整。([robosuite](https://robosuite.ai/docs/demos.html))

但不建议第一版就加入过多随机化。正确顺序是：

```text
固定场景跑通
→ 位置随机化
→ 视觉随机化
→ 动力学随机化
→ 网络随机化
→ 真机迁移
```

---

# 十三、推荐的代码目录

可以让 Codex 按下面的结构实现：

```text
multiarm_dataset/
├── configs/
│   ├── robots/
│   ├── tasks/
│   ├── cameras/
│   └── networks/
│
├── assets/
│   ├── robots/
│   ├── objects/
│   └── arenas/
│
├── envs/
│   ├── base_multiarm_env.py
│   ├── multiarm_observables.py
│   └── networked_multiarm_env.py
│
├── tasks/
│   ├── sequential_handover.py
│   ├── collaborative_lift.py
│   ├── distributed_sorting.py
│   └── cooperative_assembly.py
│
├── experts/
│   ├── state_machine.py
│   ├── grasp_planner.py
│   └── handover_expert.py
│
├── controllers/
│   ├── action_adapter.py
│   └── multiarm_controller.py
│
├── communication/
│   ├── channel.py
│   ├── message.py
│   ├── topology.py
│   └── impairment.py
│
├── collectors/
│   ├── scripted_collector.py
│   ├── teleop_collector.py
│   └── rollout_collector.py
│
├── dataset/
│   ├── schema.py
│   ├── writer.py
│   ├── reader.py
│   ├── validator.py
│   └── statistics.py
│
├── exporters/
│   ├── to_robomimic.py
│   ├── to_lerobot.py
│   └── to_rlds.py
│
├── visualization/
│   ├── replay_episode.py
│   └── render_dataset.py
│
└── tests/
    ├── test_reset.py
    ├── test_action_space.py
    ├── test_replay.py
    └── test_dataset_schema.py
```

---

# 十四、第一阶段最小可行版本

不要直接开始四臂大规模数据采集。第一阶段可以严格限定为：

### 环境

```text
2 个 Panda
1 张长桌
1 个红色方块
1 个蓝色目标容器
3 个摄像机：
- global camera
- robot0 wrist camera
- robot1 wrist camera
```

### 任务

```text
Robot 0 抓起方块
Robot 0 将方块交给 Robot 1
Robot 1 将方块放入容器
```

### 动作

```text
每臂 7D OSC_POSE action
```

### 数据

```text
MuJoCo state
RGB images
Proprioception
Actions
Task stage
Language instruction
Success
Communication events
```

### 验收条件

```text
1. 环境可以 reset 100 次而不发生穿模
2. 脚本专家成功率稳定
3. 保存后的 episode 可以精确重放
4. 图像、状态和动作时间同步
5. 数据可以导出为 LeRobotDataset
6. 一个简单 BC 模型可以过拟合少量轨迹
```

完成这一步之后，再把：

```python
num_agents = 2
```

改成：

```python
num_agents = 3
num_agents = 4
```

并扩展交接站数量。

---

# 十五、最需要避免的几个问题

### 1. 任务其实不需要通信

即便切断消息也能完成，就无法证明 CommVLA 的价值。

### 2. 使用全局相机掩盖了分布式问题

全局相机可以记录，但不应默认提供给所有 agent。

### 3. 双臂、三臂和四臂任务完全不同

这样无法证明数量扩展能力，只能证明分别训练了三个任务。

### 4. 动作坐标系不统一

不同机器人使用不同 base frame，却直接拼接动作，会让训练非常混乱。

### 5. 只保存 action，不保存 MuJoCo state

动作重放会逐渐漂移，难以复现实验。([robosuite](https://robosuite.ai/docs/algorithms/demonstrations.html))

### 6. 一开始就采集大量数据

应该先检查小数据能否回放、能否训练、能否过拟合，再扩大采集规模。

### 7. 把 hidden states 当作基础数据集

hidden states 应属于模型特征缓存，而不是任务数据集本身。

---

# 最终建议

你的路线可以收敛为：

```text
MuJoCo
    ↓
robosuite 多机器人环境
    ↓
N-Arm 参数化任务生成器
    ↓
脚本专家 + 遥操作 + policy rollout
    ↓
多智能体、语言、视觉、动作、通信统一数据格式
    ↓
LeRobot / robomimic / RLDS 导出
    ↓
同构双臂训练
    ↓
三臂与四臂零样本或少样本扩展
    ↓
通信受限条件评测
```

**最合理的第一个 Codex 任务是实现 `SequentialHandoverEnv(num_agents=2)`，完成可重放的数据采集闭环，而不是直接实现整个四臂数据集系统。** 只要双臂版本的数据结构从一开始就保留 `agent_id`、`agent_mask`、通信事件和参数化机器人数量，后续扩展到三臂、四臂就不会推倒重来。

---

**Sources:**

- [Modeling - MuJoCo Documentation](https://mujoco.readthedocs.io/en/stable/modeling.html)
- [Robots — robosuite 1.5 documentation](https://robosuite.ai/docs/modules/robots.html)
- [Dataset Contents and Visualization — robomimic 0.5 documentation](https://robomimic.github.io/docs/tutorials/dataset_contents.html)
- [GitHub - huggingface/lerobot: 🤗 LeRobot: Making AI for Robotics more accessible with end-to-end learning · GitHub](https://github.com/huggingface/lerobot)

## Prompt:
2026/7/28 21:12:22

你可以详细了解本项目中的内容，我们并不具体去记录任何通信的内容，本质上还是让模型自己去学会怎么利用通信的信息和内容。另外我是想知道，如果我想自己去搭建这样的一个仿真平台，我应该怎么做？第一步是什么，第二步是什么，不是给我一大堆我在过程中碰到的问题。我现在都不知道怎么去搭建出对应的场景，怎么去操作这些数据，我一个人怎么实现双臂，三臂，乃至多臂的任务数据采集呢？

## Response:
2026/7/28 21:12:24

你说得对，我上一条把重点放偏了。你这里的数据集不是“通信日志数据集”，而是**多机械臂协作示范数据集**；模型在训练中自行学习何时、如何利用另一机械臂传来的中间信息。下面我按“一个人真正怎么从零搭起来”的顺序讲，并结合你已经在使用的 RoboTwin/TwinVLA 体系来选路线。

> **浏览MuJoCo、RoboTwin及多机器人环境文档**
>
> [Modeling - MuJoCo Documentation](https://mujoco.readthedocs.io/en/stable/modeling.html)
> [Human Demonstrations — robosuite 1.5 documentation](https://robosuite.ai/docs/algorithms/demonstrations.html)
> [RoboTwin: Dual-Arm Robot Benchmark with Generative Digital Twins](https://github.com/TianxingChen/RoboTwin/diffs/0?base_sha=88dc4f4c9e182d4861d30dad1e2aba335dc53d33&head_user=Liang-ZX&name=main&pull_number=38&qualified_name=refs%2Fheads%2Fmain&sha1=88dc4f4c9e182d4861d30dad1e2aba335dc53d33&sha2=effa07e27d473f953b2f86e8f1716c087591e92b&short_path=b335630&unchanged=expanded&w=false)
>
> **已搜索 3 个网站**
>
> 
>
> 思考了 1m 39s

你说得对。这里应该先把目标重新定义清楚：

> 你要构建的不是“通信数据集”，而是**同步的多机械臂协作示范数据集**。

数据里只需要记录每个机械臂在同一时刻看到什么、处于什么状态、采取什么动作，以及任务是否成功。至于模型交换哪些 hidden states、如何利用通信信息，应当由 CommVLA 在训练过程中自行学习，不需要人为提供通信标签。

---

# 一、先决定仿真底座

结合你的目标，我建议：

> **使用 MuJoCo + robosuite 搭建新的 N-arm 仿真平台。**

不要直接从裸 MuJoCo XML 开始。MuJoCo 负责物理模拟，但 robosuite 已经提供了：

- Panda 等机械臂模型；
- 夹爪；
- 末端控制器；
- 桌面场景；
- 相机；
- 物体；
- 环境 `reset/step` 接口；
- 数据记录和回放接口。

更重要的是，robosuite 1.5 的环境接口可以直接接收一个单臂机器人列表，例如 `["Panda", "Panda", "Panda"]`，从而实例化三个独立机械臂，这比从 RoboTwin 现有代码扩展更自然。([robosuite](https://robosuite.ai/docs/source/robosuite.environments.manipulation.html?utm_source=chatgpt.com))

RoboTwin 2.0 很适合继续做现有双臂实验和生成双臂数据，但它当前基于 SAPIEN，核心代码与控制 API 明显围绕 `left` 和 `right` 两个机械臂设计。把它扩展到三臂、四臂并不是修改一个配置，而是要重构机器人类、控制 API、相机、动作拼接和数据保存。([GitHub](https://github.com/RoboTwin-Platform/RoboTwin/blob/main/envs/robot/robot.py?utm_source=chatgpt.com))

所以建议分工：

- **现有 INFOCOM/TwinVLA 实验**：继续使用 RoboTwin；
- **新的 N-arm 数据集和 ICLR 扩展实验**：使用 MuJoCo + robosuite；
- 最后写一个数据转换器，将新数据转换成你的 VLA 训练格式。

---

# 二、真正的第一步：跑通一个单臂闭环

第一步不是搭三臂场景，也不是开始采集数据。

第一步是：

> 用 robosuite 跑通一个 Panda 的现成 `Lift` 任务，并完成“运行-记录-回放”的完整闭环。

你需要确认四件事：

1. 能显示 Panda、桌面和方块；
2. 能通过 OSC 或 IK 控制末端移动；
3. 能保存一条轨迹；
4. 保存后的轨迹可以重新播放。

robosuite 已提供随机动作、控制器测试、轨迹记录和回放示例；其 `DataCollectionWrapper` 会保存仿真状态和动作，官方示例也展示了如何重新载入这些状态进行回放。([GitHub](https://github.com/ARISE-Initiative/robosuite/blob/master/docs/demos.md?utm_source=chatgpt.com))

这一阶段不需要改模型，不需要写新任务，也不需要训练 VLA。

完成标准只有一个：

> 你能够解释一次 `env.reset()`、一次 `env.step(action)`、返回的 observation，以及一条 episode 是怎样被保存的。

---

# 三、第二步：只搭一个空的多臂场景

完成单臂闭环后，再新建：

```text
NArmTableEnv
```

第一版场景中只放：

- 一张桌子；
- 两个 Panda；
- 一个全局相机；
- 每个 Panda 一个腕部相机。

**不要先放物体，不要先设计任务。**

robosuite 的自定义环境本质上就是把 arena、robot 和 object 组合成一个 MuJoCo 模型。官方教程也是按照“创建 world-加入机器人-加入桌面-加入物体”的顺序构建场景。([GitHub](https://github.com/ARISE-Initiative/robosuite/blob/master/docs/tutorials/add_environment.md?utm_source=chatgpt.com))

你的环境接口可以设计成：

```python
env = NArmTableEnv(num_agents=2)
```

内部使用：

```python
robots = ["Panda"] * num_agents
```

机械臂位置由一个布局函数生成：

```python
def get_robot_base_poses(num_agents):
    ...
```

例如：

```text
双臂：桌子两侧相对放置

        Robot 0
           ↓
    ┌─────────────┐
    │    table    │
    └─────────────┘
           ↑
        Robot 1
```

```text
三臂：桌子周围呈三角形

          Robot 0
             ↓
       ┌─────────┐
Robot 1 → table ← Robot 2
       └─────────┘
```

```text
四臂：桌子四边各一个

          Robot 0
             ↓
Robot 1 → table ← Robot 2
             ↑
          Robot 3
```

这一阶段只做三个测试：

- `num_agents=2` 能启动；
- `num_agents=3` 能启动；
- `num_agents=4` 能启动。

并检查：

- 初始姿态不碰撞；
- 每个机械臂能够独立移动；
- 每个腕部相机都能生成图像；
- 一个机械臂移动时，其他机械臂保持不动。

这就是你的仿真平台最小骨架。

---

# 四、第三步：建立统一的多臂控制接口

不要在任务代码里直接写大量关节控制。

先建立四个基本操作：

```python
move_to_pose(agent_id, target_pose)
open_gripper(agent_id)
close_gripper(agent_id)
hold(agent_id)
```

第一阶段统一使用末端位姿控制，例如：

```text
Δx, Δy, Δz
Δroll, Δpitch, Δyaw
gripper
```

每个机械臂 7 维动作。

因此环境内部动作可以表示为：

```python
actions.shape == [num_agents, 7]
```

传给 robosuite 时再展开成：

```python
flat_action.shape == [num_agents * 7]
```

robosuite 会将整个动作向量分发给对应机器人和控制器；每个机器人分别产生自己的观测，环境再将这些观测组合起来。([robosuite](https://robosuite.ai/docs/modules/robots.html?utm_source=chatgpt.com))

例如双臂任务中的一次仿真步：

```python
actions = np.zeros((2, 7))

actions[0] = robot0_action
actions[1] = robot1_action

obs, reward, done, info = env.step(actions.flatten())
```

三臂和四臂不改变接口：

```python
actions = np.zeros((num_agents, 7))
```

这一步非常重要，因为后面无论是脚本专家、人工遥操作还是 VLA，最终都只需要输出这个统一动作矩阵。

完成标准是：

> 你可以在同一个脚本中指定 Robot 0 向前移动、Robot 1 保持不动，然后交换两者。

---

# 五、第四步：先实现一个最简单的协作任务

第一个任务建议固定为：

> **双臂方块传递任务。**

流程如下：

```text
Robot 0 抓取方块
        ↓
Robot 0 移动到交接区域
        ↓
Robot 1 抓住方块
        ↓
Robot 0 松开
        ↓
Robot 1 将方块放入目标区域
```

这个任务只需要：

- 一个方块；
- 一个目标区域；
- 一个固定交接位置；
- 两个机械臂。

环境中需要实现三个函数。

## 1. 重置任务

```python
def _reset_internal(self):
    # 随机放置方块
    # 重置机器人姿态
    # 设置目标位置
```

第一版甚至不要随机，所有物体位置固定。

## 2. 判断成功

```python
def _check_success(self):
    return cube_inside_target
```

## 3. 返回观测

```python
def get_observation(self):
    return {
        "agent_0": {...},
        "agent_1": {...},
    }
```

第一版不要直接挑战复杂抓取。先把方块设计得稍大、摩擦合适、交接位置固定，保证任务容易成功。

---

# 六、一个人如何控制两个、三个、四个机械臂

关键答案是：

> **你不需要一个人同时手动操作四个机械臂。**

你主要依赖的是**脚本专家自动生成示范**，而不是人工逐条遥操作。

脚本专家可以直接读取仿真中的真实物体位置，并按照状态机执行。

双臂传递专家可以写成：

```text
阶段 0：Robot 0 移动到方块上方
阶段 1：Robot 0 下移
阶段 2：Robot 0 关闭夹爪
阶段 3：Robot 0 抬起
阶段 4：Robot 0 移动到交接点
阶段 5：Robot 1 移动到交接点
阶段 6：Robot 1 关闭夹爪
阶段 7：Robot 0 松开夹爪
阶段 8：Robot 1 移动到目标区域
阶段 9：Robot 1 松开夹爪
```

程序每一个仿真步都同时产生所有机械臂的动作：

```python
actions = np.zeros((num_agents, 7))

actions[0] = expert_for_robot_0()
actions[1] = expert_for_robot_1()
```

没有参与当前阶段的机械臂执行：

```python
actions[i] = hold_action
```

所以并不是你在操作两只手，而是：

> 一个中央脚本按照任务阶段同时控制所有机械臂，产生完整的专家示范。

这与后续训练分布式 CommVLA 并不冲突。专家可以使用完整仿真状态生成数据，而训练出来的模型只能使用你规定的局部视觉、局部状态和模型间通信。

人工遥操作只作为补充。robosuite 的官方遥操作脚本本身也采用“选择当前 active robot，其他机器人保持原动作”的方式，因此一个操作者可以依次切换不同机器人，而不必同时操作全部机械臂。([GitHub](https://github.com/ARISE-Initiative/robosuite/blob/master/robosuite/scripts/collect_human_demonstrations.py?utm_source=chatgpt.com))

---

# 七、第五步：从双臂任务自然扩展到三臂、四臂

不要为双臂、三臂、四臂分别写三个任务。

将任务写成：

```python
NArmRelayTask(num_agents=N)
```

定义一串交接点：

```python
handover_points = [
    point_0_to_1,
    point_1_to_2,
    point_2_to_3,
]
```

任务执行逻辑就是：

```python
for sender in range(num_agents - 1):
    receiver = sender + 1

    sender_pick_or_hold_object()
    sender_move_to_handover()
    receiver_move_to_handover()
    receiver_grasp()
    sender_release()
```

最后一个机械臂将物体放入目标区。

于是：

```text
N=2：Robot 0 → Robot 1 → Target

N=3：Robot 0 → Robot 1 → Robot 2 → Target

N=4：Robot 0 → Robot 1 → Robot 2 → Robot 3 → Target
```

你的平台从一开始就不要出现：

```python
if arm == "left":
if arm == "right":
```

而应该始终使用：

```python
robots[i]
actions[i]
observations[i]
```

这正是 RoboTwin 当前双臂结构需要大量重构的地方，也是使用 robosuite 新建 N-arm 平台的主要理由。

---

# 八、第六步：自动采集数据

当脚本专家能够稳定完成任务后，数据采集就很简单：

```python
for episode_id in range(num_episodes):
    obs = env.reset()

    while not done:
        actions = expert.act(obs)
        next_obs, reward, done, info = env.step(actions)
        recorder.append(obs, actions)
        obs = next_obs

    recorder.finish(success=env.check_success())
```

这里的 `expert.act()` 不是神经网络，而是刚才的状态机。

你一个人只需要：

1. 写一次专家；
2. 运行不同随机种子；
3. 自动筛选成功轨迹；
4. 回放少量轨迹检查。

不是手动完成 1000 次任务。

robosuite 自带的数据记录器主要保存仿真状态和动作，你可以在其基础上增加图像、proprioception 和语言指令。([GitHub](https://github.com/ARISE-Initiative/robosuite/blob/master/robosuite/wrappers/data_collection_wrapper.py?utm_source=chatgpt.com))

---

# 九、你的数据到底记录什么

对于 CommVLA，每条轨迹只需要记录同步的多机械臂数据。

建议结构为：

```text
episode_000001/
├── instruction
├── num_agents
├── agent_mask
├── observations
│   ├── agent_0
│   │   ├── wrist_rgb
│   │   ├── external_rgb
│   │   └── proprio
│   ├── agent_1
│   ├── agent_2
│   └── agent_3
├── actions
│   ├── agent_0
│   ├── agent_1
│   ├── agent_2
│   └── agent_3
├── simulation_states
└── success
```

在数组层面：

```text
wrist_images: [T, N, H, W, 3]
proprio:      [T, N, P]
actions:      [T, N, A]
agent_mask:   [N]
```

其中：

- `T`：轨迹长度；
- `N`：机械臂数量；
- `P`：本体状态维度；
- `A`：动作维度。

例如最多支持四臂：

```text
双臂：agent_mask = [1, 1, 0, 0]
三臂：agent_mask = [1, 1, 1, 0]
四臂：agent_mask = [1, 1, 1, 1]
```

不记录：

```text
communication message
communication label
which hidden state should be used
which layer should communicate
```

这些不是数据集监督目标。

模型训练时，各个 SingleVLA 分支读取各自的图像和 proprioception；CommVLA 架构在 forward 过程中执行 hidden exchange；每个分支最后预测自己的动作。

损失大致是：

```text
所有有效机械臂的动作预测损失之和或平均
```

通过 `agent_mask` 忽略不存在的机械臂。

---

# 十、数据采集后怎么“操作这些数据”

整个数据生命周期只有五个动作：

```text
专家执行
   ↓
保存原始 episode
   ↓
回放并检查成功
   ↓
转换为 VLA 训练格式
   ↓
训练模型
```

## 原始数据

原始数据应尽量完整：

- RGB；
- proprioception；
- action；
- MuJoCo state；
- task instruction；
- success。

## 回放检查

随机抽取 episode，恢复 MuJoCo state 并生成视频，检查：

- 图像和动作是否对齐；
- 有没有突然跳帧；
- 夹爪是否正确；
- 交接是否完成；
- 成功标签是否正确。

## 转换数据

再写一个转换器：

```text
MuJoCo raw episode
        ↓
CommVLA training sample
```

把数据变成你当前 SingleVLA/TwinVLA 训练代码要求的格式。

也就是说，**仿真平台的数据格式和模型的数据格式最好分开**。未来更换 VLA 时，只换转换器，不重新采集数据。

## 小数据过拟合测试

不要一开始生成几万条。

先生成少量固定场景轨迹，检查模型能否在训练集任务上过拟合。如果少量数据都学不会，问题通常在：

- action 定义；
- observation 与 action 时间错位；
- 图像顺序；
- 坐标系；
- 数据转换。

等小规模闭环完全正确，再扩大采集规模。

---

# 十一、你的最小项目其实只需要五个核心文件

```text
multiarm_sim/
├── envs/
│   └── narm_table_env.py
├── tasks/
│   └── relay_task.py
├── experts/
│   └── relay_expert.py
├── data/
│   ├── collect.py
│   └── replay.py
└── adapters/
    └── to_commvla.py
```

它们分别负责：

```text
narm_table_env.py
建立桌子、N 个机器人、相机、物体和 step 接口

relay_task.py
定义方块位置、交接点和成功条件

relay_expert.py
自动控制多个机械臂完成任务

collect.py
执行专家并保存轨迹

replay.py
重新播放轨迹并检查数据

to_commvla.py
转换成你目前模型训练所需格式
```

第一版完全不需要：

- 网络通信模拟；
- hidden state 保存；
- 复杂运动规划；
- 强化学习；
- Blender 自制物体；
- 大规模 domain randomization；
- 多个任务；
- 真机标定。

---

# 最清楚的实施顺序

严格按照下面的顺序推进：

### 第一步

跑通 robosuite 单 Panda 的现成任务，并完成记录和回放。

### 第二步

建立没有物体的 `NArmTableEnv`，确认 2、3、4 个 Panda 都能加载和独立运动。

### 第三步

加入方块，实现单个机械臂在多臂场景中的 pick-and-place，其他机械臂保持不动。

### 第四步

实现双臂 handover 脚本专家。

### 第五步

将双臂 handover 改成参数化的 `NArmRelayTask`。

### 第六步

自动生成同步的多机械臂轨迹，保存图像、proprioception 和动作。

### 第七步

编写转换器，将轨迹转换成 CommVLA 所需格式，先进行小数据过拟合。

你现在在 Codex 中最先应该完成的任务只有一个：

> **安装并运行 robosuite 的单臂 Lift 环境，保存并成功回放一条 Panda 轨迹。**

这一步没有完成之前，不要开始写三臂或四臂代码。

---

**Sources:**

- [robosuite.environments.manipulation package](https://robosuite.ai/docs/source/robosuite.environments.manipulation.html?utm_source=chatgpt.com)
- [RoboTwin/envs/robot/robot.py at main - GitHub](https://github.com/RoboTwin-Platform/RoboTwin/blob/main/envs/robot/robot.py?utm_source=chatgpt.com)

## Prompt:
2026/7/28 21:21:08

我后续想自己去设计一些任务进行，这个要怎么进行呢？之前我看到的LIBERO是桌子上很多物体，然后一个单臂模型去操作的，比如说我想设计几个双臂任务，三臂任务，四臂任务之类的事情，目前大部分的数据集桌子上只有对应的目标，而不是具有多种操作对象。如果是这样的情况我怎么去操作呢？

## Response:
2026/7/28 21:21:10

我会把问题收敛成“怎样把一张桌子上的多物体场景，系统地变成双臂、三臂、四臂任务”。重点不是继续谈平台安装，而是任务模板、物体库、场景生成、成功条件和专家轨迹怎么一起设计。

> **浏览官方文档与资源以设计复杂任务**
>
> [Lifelong-Robot-Learning/LIBERO - GitHub](https://github.com/Lifelong-Robot-Learning/LIBERO)
> [Welcome to robosuite’s documentation! — robosuite 1.5 documentation](https://robosuite.ai/docs/index.html)
> [LIBERO Datasets – LIBERO](https://libero-project.github.io/datasets)
> [模型库 - MuJoCo 文档](https://docs.mujoco.cn/en/stable/models.html)
> [LIBERO Evaluation | starVLA/starVLA | DeepWiki](https://deepwiki.com/starVLA/starVLA/7.3-libero-evaluation)
> [【学习】robosuite安装配置添加自定义机械臂教程](https://www.cnblogs.com/quantoublog/articles/19568250)
> [Model Gallery - MuJoCo Documentation](https://mujoco.readthedocs.io/en/stable/models.html)
> [LIBERO — Open-Source Robotics Datasets | SVRC](https://www.roboticscenter.ai/datasets/libero)
> [[RL robotic 环境] - [Robosuite] (2) - CSDN博客](https://blog.csdn.net/upr_rom/article/details/128374555)
> [hf-libero · PyPI](https://pypi.org/project/hf-libero/)
> [具身智能 | Robosuite使用教程（一） - 知乎](https://zhuanlan.zhihu.com/p/6621264369)
> [LIBERO: Benchmarking Knowledge Transfer for Lifelong Robot Learning](https://arxiv.org/abs/2306.03310)
>
> **已搜索 12 个网站**
>
> 
>
> 思考了 26s

你现在真正需要建立的，不是“每设计一个任务就重新搭一个 MuJoCo 场景”，而是：

> **先搭建一个包含多机械臂、多物体和多个操作区域的通用场景，再通过任务配置决定这一回合要操作哪些物体、由哪些机械臂操作、最终要达到什么状态。**

LIBERO 的思路其实可以借鉴：它把**场景、对象、初始状态、目标条件和语言指令**分开描述，所以同一个厨房桌面可以产生许多不同任务。LIBERO 本身提供了程序化任务生成流程，任务数据也包含视觉、本体状态、语言指令以及 PDDL 场景描述。([GitHub](https://github.com/Lifelong-Robot-Learning/LIBERO?utm_source=chatgpt.com))

---

# 一、先理解：场景和任务不是一回事

假设桌面上有：

```text
红色方块
蓝色方块
黄色方块
杯子
碗
托盘
抽屉
篮子
```

这是一个**场景**。

在同一个场景中，你可以定义不同任务：

```text
任务 1：把红色方块放入篮子
任务 2：把杯子放到托盘上
任务 3：打开抽屉，把蓝色方块放进去
任务 4：把红色和黄色方块分别放进两个容器
任务 5：一只机械臂打开抽屉，另一只机械臂把杯子放进去
```

因此，桌子上有很多物体并不意味着所有物体都必须被操作。

每个物体在当前任务中可以扮演四种角色：

| 角色 | 作用 |
|---|---|
| 目标物体 | 必须操作的物体 |
| 目标容器或设备 | 碗、篮子、抽屉、托盘 |
| 中间工具 | 锤子、勺子、盖子等 |
| 干扰物体 | 不需要操作，但增加视觉和规划难度 |

例如任务：

> “把红色方块放进蓝色碗里。”

桌面上即使有十个物体，真正涉及目标的只有：

```text
红色方块：目标物体
蓝色碗：目标容器
其余八个：干扰物体
```

这正是你需要的数据集设计方式。

---

# 二、第一步：建立一个物体库，而不是一个任务一个 XML

建议你先准备一个小型物体库，第一版不需要很多。

## 可抓取物体

```text
cube_red
cube_blue
cube_yellow
cylinder
mug
bottle
small_box
tool
```

## 容器类

```text
bowl
basket
tray
storage_box
```

## 可交互设备

```text
drawer
cabinet
door
button
rack
```

## 场景物体

```text
table
divider
shelf
conveyor
```

每个物体作为独立 MJCF 文件：

```text
assets/
├── objects/
│   ├── red_cube.xml
│   ├── blue_cube.xml
│   ├── mug.xml
│   ├── bowl.xml
│   ├── basket.xml
│   └── tray.xml
├── fixtures/
│   ├── drawer.xml
│   ├── cabinet.xml
│   └── shelf.xml
└── arenas/
    └── multiarm_table.xml
```

第一版可以大量使用简单几何体：

- 方块；
- 圆柱；
- 长方体；
- 简单碗和托盘。

不要一开始花大量时间寻找漂亮的三维模型。物理属性、抓取稳定性和任务逻辑比外观重要。

robosuite 支持程序化几何物体、组合物体和基于 XML 的自定义物体；LIBERO 也提供了把外部 MJCF 物体注册进自己项目的示例。([robosuite](https://robosuite.ai/docs/modules/objects.html?utm_source=chatgpt.com))

---

# 三、第二步：建立“通用桌面场景”

先不要设计具体任务，建立一个能够容纳多物体和多机械臂的场景。

例如：

```text
                Robot 0
                   ↓
        ┌───────────────────────┐
        │ A区    中央区     B区 │
Robot 1 →                       ← Robot 2
        │ C区    交接区     D区 │
        └───────────────────────┘
                   ↑
                Robot 3
```

桌面应被划分成若干逻辑区域：

```text
spawn_region_0
spawn_region_1
spawn_region_2
handover_region
assembly_region
target_region_0
target_region_1
distractor_region
```

这些区域不一定在图像中显示，它们主要用于：

- 随机放置物体；
- 限制物体生成范围；
- 判断任务成功；
- 给专家控制器提供目标位置。

robosuite 的物体放置系统会在环境 reset 时调用位置采样器，并使用物体定义的顶部、底部和水平半径信息避免物体重叠。([robosuite](https://robosuite.ai/docs/modules/objects.html?utm_source=chatgpt.com))

环境 reset 时可以这样生成：

```python
scene.reset(
    objects=[
        "red_cube",
        "blue_cube",
        "mug",
        "bowl",
        "basket",
        "yellow_cube",
    ],
    fixtures=[
        "drawer",
    ],
)
```

然后分别放置：

```python
red_cube    -> spawn_region_0
blue_cube   -> spawn_region_1
mug         -> spawn_region_2
bowl        -> target_region_0
basket      -> target_region_1
yellow_cube -> distractor_region
```

这样你拥有的是一个**可重复生成的多物体工作台**，而不是一个固定截图。

---

# 四、第三步：把任务写成配置文件

设计任务时，不要每次都写一个完整的 Python 环境。

应该用 YAML、JSON 或类似 LIBERO BDDL 的任务描述。

例如一个双臂任务：

```yaml
task_name: two_arm_drawer_place

instruction: >
  Open the drawer and place the red cube inside it.

num_agents: 2

objects:
  target:
    - red_cube
  fixtures:
    - drawer
  distractors:
    - blue_cube
    - mug
    - yellow_cube
    - bowl

initial_state:
  red_cube:
    region: robot_1_workspace
  drawer:
    state: closed
  blue_cube:
    region: distractor_region
  mug:
    region: distractor_region

agent_roles:
  agent_0:
    responsibility: open_drawer
  agent_1:
    responsibility: place_red_cube

success_conditions:
  - drawer_open
  - red_cube_inside_drawer
```

程序读取配置后自动完成：

```text
加载机器人
加载物体
随机摆放
设置初始状态
生成语言指令
构建成功检测器
启动数据采集
```

LIBERO 的程序化生成流程也是从可用对象和 predicates 出发，定义初始状态分布与任务目标，再生成任务描述文件；其环境模板把 movable objects、fixtures、regions 和 success predicates 分开处理。([GitHub](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/templates/problem_class_template.py?utm_source=chatgpt.com))

---

# 五、多机械臂任务不是“单臂任务加几个机器人”

这是最关键的一点。

假如一只机械臂也能完成，那么即使场景里放了四只机械臂，也不能算真正的四臂任务。

多机械臂任务必须加入至少一种**协作约束**。

## 1. 可达范围约束

物体只能由某个机械臂够到，目标区域只能由另一个机械臂够到。

```text
Robot 0 能抓到物体
Robot 1 能够到目标
两者之间必须交接
```

这是最容易实现的协作任务。

## 2. 同时操作约束

例如：

```text
Robot 0 按住按钮
Robot 1 才能打开柜门
```

或者：

```text
Robot 0 固定物体
Robot 1 插入零件
```

## 3. 角色分工约束

```text
Robot 0 打开抽屉
Robot 1 取出物体
Robot 2 接收物体
Robot 3 完成分类
```

## 4. 视野约束

不同机械臂看到不同信息：

```text
Robot 0 看得到目标标识
Robot 1 看得到候选物体
Robot 2 负责抓取
```

这种设计特别适合后续验证 CommVLA 的信息交换能力。

## 5. 空间容量约束

大物体不能由一个夹爪稳定搬运：

```text
两个机械臂共同搬长盒子
三个机械臂固定柔性物体
四个机械臂搬运大托盘
```

这一类物理难度高，应该后做。

---

# 六、建议先设计“任务原语”

不要直接设计几十个完整任务。先实现少量基础动作：

```text
Reach(object)
Grasp(object)
Lift(object)
Place(object, region)
Insert(object, container)
Open(fixture)
Close(fixture)
Press(button)
Handover(object, sender, receiver)
Hold(object)
Wait(condition)
```

每个完整任务就是原语的组合。

例如双臂任务：

```text
Open(drawer, Robot 0)
Grasp(red_cube, Robot 1)
Place(red_cube, drawer, Robot 1)
```

三臂任务：

```text
Grasp(mug, Robot 0)
Handover(mug, Robot 0, Robot 1)
Open(cabinet, Robot 2)
Place(mug, cabinet, Robot 1)
```

四臂任务：

```text
Open(drawer, Robot 0)
Grasp(red_cube, Robot 1)
Grasp(blue_cube, Robot 2)
Place(red_cube, left_bin, Robot 1)
Place(blue_cube, right_bin, Robot 2)
Close(drawer, Robot 3)
```

这样扩展任务时不需要重写底层控制逻辑。

---

# 七、双臂任务应该怎样设计

第一批双臂任务建议从下面三类开始。

## 双臂任务 A：打开并放入

桌面物体：

```text
抽屉
红色方块
蓝色方块
杯子
碗
```

任务：

> Robot 0 打开抽屉，Robot 1 将红色方块放入抽屉。

为什么需要双臂：

- 抽屉位于 Robot 0 的工作区；
- 方块位于 Robot 1 的工作区；
- 单臂无法同时覆盖两个区域。

执行图：

```text
Robot 0：接近把手 → 抓住 → 拉开 → 保持
Robot 1：抓方块 → 等待抽屉打开 → 放入
```

## 双臂任务 B：物体交接

桌面上放很多物体：

```text
红色方块
蓝色方块
杯子
瓶子
两个碗
篮子
```

任务：

> 将红色方块从 Robot 0 的区域传递给 Robot 1，并放入篮子。

干扰物体不会被操作，但增加视觉识别难度。

## 双臂任务 C：共同整理

任务：

> 将红色方块放入左侧容器，将蓝色方块放入右侧容器。

两只机械臂可以并行工作：

```text
Robot 0 处理红色方块
Robot 1 处理蓝色方块
```

这类任务的协作依赖较弱，适合测试并行执行和任务分工，但不能作为通信必要性的主要证据。

---

# 八、三臂任务应该怎样设计

三臂任务不能只是增加一次交接，否则容易变成机械重复。

可以设计一个三阶段工作链：

## 三臂任务 A：取出-传递-放置

场景：

```text
左侧柜子
中央交接区
右侧分类区
多个物体和多个容器
```

流程：

```text
Robot 0：打开柜子并取出目标物
Robot 1：接收并重新调整物体姿态
Robot 2：将物体放入指定容器
```

例如：

> Take the red mug from the cabinet and place it on the blue tray.

为什么需要三臂：

- Robot 0 能够到柜子内部；
- Robot 2 能够到目标区域；
- 两者工作空间不重叠；
- Robot 1 负责中间交接和方向调整。

## 三臂任务 B：打开-取物-关闭

```text
Robot 0 打开抽屉
Robot 1 取出指定物体
Robot 2 接收物体并关闭抽屉或整理目标区
```

## 三臂任务 C：条件分类

桌面上有：

```text
红杯、蓝杯、黄色杯
左篮、右篮
标识牌
若干干扰物
```

```text
Robot 0 查看或操作标识区域
Robot 1 负责挑选目标物
Robot 2 负责最终分类
```

模型需要在多个 agent 的信息之间形成正确协作。

---

# 九、四臂任务应该怎样设计

四臂更适合设计成“小型工作站”，而不是四次连续 handover。

## 四臂任务 A：装配工作站

```text
Robot 0：打开零件盒
Robot 1：拿底座
Robot 2：拿插入件
Robot 3：完成装配或放入成品区
```

桌面可以放：

```text
两个零件盒
多个不同颜色零件
底座
工具
成品托盘
若干错误零件
```

语言任务：

> Assemble the red connector with the square base and place it in the output tray.

## 四臂任务 B：订单履行

场景类似仓储打包：

```text
多个产品
多个容器
包装盒
订单标识
干扰物
```

角色：

```text
Robot 0：打开包装盒
Robot 1：选取第一个物体
Robot 2：选取第二个物体
Robot 3：检查并关闭包装盒
```

## 四臂任务 C：多阶段厨房整理

```text
Robot 0：打开柜门
Robot 1：取杯子
Robot 2：移开遮挡物
Robot 3：将杯子放到指定架子
```

这一类任务可以明显区别于单臂 LIBERO，也更符合你的“可扩展多 agent VLA”研究目标。

---

# 十、桌面很多物体时，专家程序怎么知道操作哪个

专家不需要像学习模型一样依靠图像判断物体。

在仿真数据生成阶段，专家可以读取 MuJoCo 的真实状态：

```python
cube_pose = env.get_object_pose("red_cube")
drawer_pose = env.get_fixture_pose("drawer")
target_pose = env.get_region_pose("target_region")
```

然后由任务配置告诉它：

```yaml
target_object: red_cube
target_receptacle: drawer
```

专家只操作指定物体。

例如：

```python
target_name = task.target_object
target_pose = env.get_object_pose(target_name)

action = grasp_controller.move_to(target_pose)
```

其他物体只负责：

- 遮挡；
- 制造视觉相似性；
- 占据空间；
- 增加碰撞避障难度。

因此你完全可以在桌面放 10 个物体，而脚本专家只操作其中 2 个。

---

# 十一、一个人如何生成复杂任务的示范

仍然不是靠你同时操作四只机械臂。

你需要一个**中央专家任务调度器**：

```python
class MultiArmExpert:
    def act(self, simulator_state):
        actions = []

        for agent_id in range(num_agents):
            actions.append(
                self.agent_controllers[agent_id].act(simulator_state)
            )

        return np.stack(actions)
```

每个机械臂有自己的状态机：

```text
Robot 0:
WAIT → OPEN_DRAWER → HOLD_DRAWER → RETREAT

Robot 1:
WAIT → GRASP_CUBE → WAIT_DRAWER_OPEN → PLACE → RETREAT
```

中央任务状态则记录：

```text
drawer_is_open
cube_is_grasped
cube_is_inside_drawer
```

每一个仿真步，同时生成所有机械臂动作：

```python
actions = expert.act(env.get_privileged_state())
obs, reward, done, info = env.step(actions)
```

训练数据中保存的是：

```text
每只机械臂的局部图像
每只机械臂的 proprioception
每只机械臂的动作
统一语言指令
```

而不是保存专家使用的物体真值。

---

# 十二、任务成功条件怎么定义

成功条件不要根据执行脚本处于哪个阶段判断，而要根据最终物理状态判断。

例如：

## 放入容器

```python
inside(red_cube, drawer)
```

## 放到托盘上

```python
on(red_mug, blue_tray)
```

## 打开抽屉

```python
drawer_joint_position > threshold
```

## 多物体分类

```python
inside(red_cube, red_bin)
and inside(blue_cube, blue_bin)
```

## 协同搬运

```python
inside(large_box, target_region)
and not dropped(large_box)
```

## 装配

```python
inserted(connector, base)
and orientation_error < threshold
```

LIBERO 采用 predicates 描述对象关系和任务目标，例如物体位于某个区域、容器或设备中，这种思路非常适合你的任务系统。([GitHub](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/templates/problem_class_template.py?utm_source=chatgpt.com))

---

# 十三、怎样从一个任务生成很多数据

一个“任务模板”不等于一个固定场景。

例如任务模板：

```text
双臂打开抽屉并放入物体
```

可以随机化：

```text
目标物体：红方块 / 蓝方块 / 杯子 / 小瓶
抽屉位置：左侧 / 中间
干扰物数量：2-8
目标物初始位置：多个区域
机械臂初始姿态：小范围变化
物体朝向：随机
语言表达：多个同义句
```

于是一个模板能产生许多实例：

```text
把红色方块放入抽屉
把蓝色杯子放入抽屉
打开中间抽屉并放入小瓶
将桌上的红色物体收进抽屉
```

数据组织可以分成：

```text
Task template
    ├── Scene seed 000
    ├── Scene seed 001
    ├── Scene seed 002
    └── ...
```

你真正需要积累的是：

> 少量高质量任务模板 × 大量物体与位置变化

而不是人工写几千个任务。

---

# 十四、建议你采用的任务定义结构

```text
tasks/
├── templates/
│   ├── open_and_place.yaml
│   ├── relay_sort.yaml
│   ├── cooperative_pack.yaml
│   └── multi_stage_assembly.yaml
├── predicates/
│   ├── inside.py
│   ├── on.py
│   ├── open.py
│   ├── grasped.py
│   └── inserted.py
├── primitives/
│   ├── grasp.py
│   ├── place.py
│   ├── open.py
│   ├── handover.py
│   └── hold.py
└── generators/
    ├── scene_generator.py
    ├── task_generator.py
    └── language_generator.py
```

其中：

```text
scene_generator.py
负责选择和摆放物体

task_generator.py
负责指定哪些物体是目标、有哪些 agent、目标状态是什么

language_generator.py
负责生成语言指令

primitives/
负责脚本专家的基本行为

predicates/
负责判断任务是否成功
```

---

# 十五、最合理的落地顺序

你接下来不要马上设计完整的四臂场景。严格按照以下顺序：

## 第一步：多物体单臂任务

建立一个桌面，放：

```text
3 个彩色方块
2 个容器
2 个干扰物
```

完成：

> 把指定颜色的方块放入指定容器。

目的是学会：

- 加载多个物体；
- 随机摆放；
- 从配置中选择目标；
- 判断成功；
- 自动采集数据。

## 第二步：多物体双臂任务

在同一个场景中放两个机械臂：

> Robot 0 打开抽屉，Robot 1 把指定物体放进去。

这是第一个真正值得做的多臂任务。

## 第三步：双臂交接任务

> Robot 0 从自己的区域取出目标物，交给 Robot 1，Robot 1 放入指定容器。

## 第四步：参数化三臂任务

加入 Robot 2：

> 取出 → 交接或调整 → 分类放置。

## 第五步：四臂工作站

使用四种不同角色，而不是简单连续传四次：

> 打开容器 → 选择零件 → 操作第二个零件 → 完成装配或包装。

---

# 你现在最先应该实现的任务

最适合成为你整个平台第一个自定义任务的是：

```text
场景：
两个 Panda
一张桌子
一个抽屉
三个彩色方块
一个杯子
一个碗
两个干扰物

任务：
“Open the drawer and place the red cube inside.”

分工：
Robot 0 打开并保持抽屉
Robot 1 从多个物体中抓取红色方块并放入抽屉

成功条件：
drawer_open == True
inside(red_cube, drawer) == True
```

这个任务一次性覆盖了你需要掌握的核心能力：

- 多物体场景；
- 目标物体和干扰物；
- 双臂独立控制；
- 时间协作；
- 可交互设备；
- 语言指令；
- 状态机专家；
- 多臂同步数据采集；
- 明确成功条件。

完成这个模板以后，换成杯子、瓶子、不同抽屉、不同摆放位置，都是配置变化；扩展成三臂和四臂时，也是在任务图上增加角色，而不是重新搭建整个仿真系统。

---

**Sources:**

- [Lifelong-Robot-Learning/LIBERO - GitHub](https://github.com/Lifelong-Robot-Learning/LIBERO?utm_source=chatgpt.com)
- [Objects — robosuite 1.5 documentation](https://robosuite.ai/docs/modules/objects.html?utm_source=chatgpt.com)

## Prompt:
2026/7/28 21:44:46

我想详细了解一下MuJoCo和Robosuite是什么，怎么用呢？

## Response:
2026/7/28 21:44:48

我会先把两者的关系讲清楚，再用一个最小示例说明：MuJoCo 如何加载世界、robosuite 如何把机器人任务封装成 `reset/step` 环境，以及你真正需要学习哪些文件和接口。

> **Searching official MuJoCo and robosuite documentation**
>
> [Modeling - MuJoCo Documentation](https://mujoco.readthedocs.io/en/latest/modeling.html)
> [Welcome to robosuite’s documentation! — robosuite 1.5 documentation](https://robosuite.ai/docs/index.html)
> [robosuite/robosuite at master · ARISE-Initiative/robosuite · GitHub](https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite)
>
> **已搜索 3 个网站**
>
> 
>
> **解释MuJoCo和Robosuite**
>
> MuJoCo是物理引擎，用于动态计算、传感器、联动等。Robosuite则是构建在其上，提供机器人模型、控制器等。它理解XML, MJCF文件，并用于模拟和控制。
>
> **解释MuJoCo和Robosuite**
>
> 
>
> **正在搜索网页**
>
> [Basic Usage — robosuite 1.5 documentation](https://robosuite.ai/docs/basicusage.html)
>
> **已搜索 1 个网站**
>
> 
>
> 思考了 1m 0s

可以先用一句话区分：

> **MuJoCo 是物理引擎；robosuite 是建立在 MuJoCo 上的机器人任务开发框架。**

你的多机械臂项目中，绝大部分日常开发应该在 **robosuite 层**完成；只有在修改机械臂模型、物体碰撞、关节、执行器和底层仿真状态时，才需要深入 MuJoCo。

---

# 一、MuJoCo 是什么

MuJoCo，全称 **Multi-Joint dynamics with Contact**，主要负责计算：

- 机械臂关节如何运动；
- 电机或力矩如何影响关节；
- 夹爪和物体是否接触；
- 物体是否被抓起、滑落或碰撞；
- 摩擦力、重力和惯性；
- 摄像机渲染；
- 仿真状态推进。

它使用自己的模型描述语言 **MJCF**。MJCF 本质上是 XML，用来描述世界中的刚体、关节、几何体、执行器、传感器和摄像机。MuJoCo 也能读取 URDF，但 MJCF 能表达更多 MuJoCo 特有的物理属性。([MuJoCo](https://mujoco.readthedocs.io/en/latest/modeling.html?utm_source=chatgpt.com))

可以把 MuJoCo 理解成：

```text
场景 XML + 当前状态 + 控制信号
                 ↓
              MuJoCo
                 ↓
下一时刻的关节、物体、碰撞和传感器状态
```

---

# 二、MuJoCo 最核心的两个对象

使用 Python 时，最重要的是：

```python
model
data
```

## `MjModel`

`MjModel` 保存基本不随时间变化的内容：

```text
机械臂结构
关节类型
连杆质量
碰撞几何
执行器
摄像机
仿真时间步长
摩擦参数
```

它可以理解为“这个物理世界的结构”。

```python
model = mujoco.MjModel.from_xml_path("scene.xml")
```

## `MjData`

`MjData` 保存仿真过程中不断变化的状态：

```text
qpos：关节位置和物体位姿
qvel：关节和物体速度
ctrl：执行器控制输入
time：当前仿真时间
contact：当前碰撞接触
传感器值
```

```python
data = mujoco.MjData(model)
```

推进一步仿真：

```python
mujoco.mj_step(model, data)
```

官方 Python API 本身比较底层：用户需要显式维护 `MjModel` 和 `MjData`，并调用 `mj_step`、`mj_resetData` 和 `mj_forward` 等函数。([MuJoCo](https://mujoco.readthedocs.io/en/stable/python.html))

---

# 三、一个最小 MuJoCo 例子

下面先不用机械臂，只模拟一个受电机控制的摆。

## `pendulum.xml`

```xml
<mujoco model="simple_pendulum">
    <option timestep="0.002" gravity="0 0 -9.81"/>

    <worldbody>
        <light pos="0 0 3"/>
        <geom
            name="floor"
            type="plane"
            size="2 2 0.1"
            rgba="0.8 0.8 0.8 1"
        />

        <body name="pendulum" pos="0 0 1">
            <joint
                name="hinge"
                type="hinge"
                axis="0 1 0"
                damping="0.1"
            />

            <geom
                name="rod"
                type="capsule"
                fromto="0 0 0 0 0 -0.5"
                size="0.04"
                density="500"
                rgba="0.2 0.5 0.8 1"
            />
        </body>
    </worldbody>

    <actuator>
        <motor
            name="hinge_motor"
            joint="hinge"
            ctrllimited="true"
            ctrlrange="-1 1"
        />
    </actuator>
</mujoco>
```

## `run_mujoco.py`

```python
import time

import mujoco
import mujoco.viewer

model = mujoco.MjModel.from_xml_path("pendulum.xml")
data = mujoco.MjData(model)

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running() and data.time < 10.0:
        # 给第一个电机施加控制输入
        data.ctrl[0] = 0.2

        # 推进一个物理仿真步
        mujoco.mj_step(model, data)

        # 更新可视化
        viewer.sync()

        # 让显示速度接近真实时间
        time.sleep(model.opt.timestep)
```

安装和运行：

```bash
pip install mujoco
python run_mujoco.py
```

官方 Python 包已经包含 MuJoCo 动态库，一般不需要再单独下载 MuJoCo 二进制文件。([MuJoCo](https://mujoco.readthedocs.io/en/stable/python.html))

这个例子体现了最底层的工作方式：

```text
读取 XML
→ 创建 model
→ 创建 data
→ 写入 data.ctrl
→ 调用 mj_step
→ 读取新的 qpos、qvel 和 contact
```

---

# 四、为什么不建议直接用裸 MuJoCo搭你的平台

理论上，你可以完全用 MuJoCo 实现多机械臂环境。但你需要自己处理：

```text
加载 Panda 机械臂模型
添加夹爪
重命名多个机器人中的所有关节和几何体
实现末端控制器
求雅可比矩阵
做逆运动学
实现抓取判断
建立相机观测
定义 reset 和 step
随机放置物体
设计奖励
保存数据
实现遥操作
```

这不是不能做，而是工作量很大。

所以在 MuJoCo 之上使用 robosuite。

---

# 五、robosuite 是什么

robosuite 是一个基于 MuJoCo 的机器人学习仿真框架。它已经提供了：

- Panda、Sawyer、Jaco 等机器人模型；
- 不同夹爪；
- 桌面、工作区和物体；
- 末端空间控制、关节控制和 IK；
- 相机、深度、分割图和 proprioception；
- 标准化机器人任务；
- 遥操作；
- 演示数据采集和回放；
- 自定义任务开发接口。

官方当前文档是 robosuite 1.5 系列；其主要目标就是将 robot、arena、object、controller 和 environment 模块化组合，以便开发机器人学习任务。([robosuite](https://robosuite.ai/docs/overview.html?utm_source=chatgpt.com))

它和 MuJoCo 的关系是：

```text
你的训练代码 / 专家脚本 / VLA
              ↓
          robosuite 环境
              ↓
机器人 + 夹爪 + 控制器 + 物体 + 桌面
              ↓
          生成并组合 MJCF
              ↓
             MuJoCo
```

robosuite 不会替代 MuJoCo。

最终所有碰撞、动力学和物理推进仍然由 MuJoCo 计算。

---

# 六、robosuite 中的六个主要模块

## 1. Robot

描述机器人本体，例如：

```text
Panda
Sawyer
Jaco
UR5e
```

Robot 对象不仅包含 XML 模型，还关联：

- 机械臂；
- 夹爪；
- 安装底座；
- 控制器；
- 关节状态；
- 末端执行器状态。

环境中的第 `i` 个机器人通常通过下面的方式访问：

```python
env.robots[i]
```

robosuite 环境允许通过 `robots` 参数实例化机器人列表，但具体标准任务可能限制机器人数量。因此，三臂和四臂任务最终需要你编写自己的环境类，而不是直接给某个单臂标准任务传入四个机器人。([robosuite](https://robosuite.ai/docs/modules/environments.html))

## 2. Gripper

夹爪是独立模块，例如：

```text
PandaGripper
Robotiq85Gripper
RethinkGripper
```

它决定：

- 手指关节；
- 碰撞模型；
- 抓取接触；
- 夹爪动作维度。

## 3. Arena

Arena 是工作空间，例如：

```text
TableArena
EmptyArena
MultiTableArena
BinsArena
```

它包含桌子、地面、照明和固定摄像机。

## 4. Object

Object 是可交互物体，例如：

```text
BoxObject
BallObject
CylinderObject
自定义 MJCFObject
```

你前面提到的杯子、抽屉、托盘和多个干扰物，都属于 Object 或 fixture。

## 5. Controller

Controller 将高层动作转成关节力矩。

例如你给出：

```text
末端向右移动 2 厘米
```

控制器会计算机械臂每个关节应该产生什么力矩。

robosuite 提供：

```text
OSC_POSE
OSC_POSITION
JOINT_POSITION
JOINT_VELOCITY
JOINT_TORQUE
IK
```

其中 `OSC_POSE` 最适合你早期的数据生成。它通常接收末端平移和旋转增量，再由控制器生成底层关节力矩。robosuite 的位置类控制器默认将输入解释成相对当前状态的增量。([robosuite](https://robosuite.ai/docs/modules/controllers.html))

单臂 Panda 使用 `OSC_POSE` 时，常见动作是：

```text
dx, dy, dz,
dax, day, daz,
gripper
```

也就是：

```python
action.shape == (7,)
```

前六维控制末端位姿，最后一维控制夹爪。

## 6. Environment

Environment 是你真正操作的主要对象。

它封装：

```text
机器人
场景
物体
控制器
观测
奖励
成功条件
reset
step
```

基本接口为：

```python
obs = env.reset()

obs, reward, done, info = env.step(action)
```

robosuite 的环境接口与 Gym 风格接近，`obs` 通常是一个字典，里面可同时包含图像和低维状态。([robosuite](https://robosuite.ai/docs/basicusage.html))

---

# 七、一个最小 robosuite 程序

## 安装

简单体验可以直接安装：

```bash
conda create -n multiarm python=3.10 -y
conda activate multiarm

pip install mujoco
pip install robosuite
```

测试：

```bash
python -m robosuite.demos.demo_random_action
```

macOS 使用默认交互式 viewer 时，官方建议将 `python` 换成 `mjpython`：

```bash
mjpython -m robosuite.demos.demo_random_action
```

robosuite 官方支持 macOS 和 Linux，并建议使用独立的 Conda 或 virtualenv 环境。([robosuite](https://robosuite.ai/docs/installation.html))

不过，你后面需要修改 robosuite 和编写多臂环境，更适合安装源码版本：

```bash
git clone https://github.com/ARISE-Initiative/robosuite.git
cd robosuite

pip install -r requirements.txt
```

官方建议需要开发自定义功能的用户使用源码安装。([robosuite](https://robosuite.ai/docs/installation.html))

---

## 运行 Panda Lift

保存成 `run_lift.py`：

```python
import numpy as np
import robosuite as suite
from robosuite.controllers import load_composite_controller_config

controller_config = load_composite_controller_config(
    controller="BASIC"
)

env = suite.make(
    env_name="Lift",
    robots="Panda",
    controller_configs=controller_config,

    # 屏幕显示
    has_renderer=True,
    has_offscreen_renderer=False,
    render_camera="frontview",

    # 暂时不用相机图像作为模型输入
    use_camera_obs=False,
    use_object_obs=True,

    control_freq=20,
    horizon=500,
)

obs = env.reset()

print("Action dimension:", env.action_dim)
print("Observation keys:")
for key, value in obs.items():
    print(key, value.shape)

low, high = env.action_spec

for step in range(500):
    # 这里只用于测试环境，随机动作不会完成任务
    action = np.random.uniform(low, high) * 0.1

    obs, reward, done, info = env.step(action)
    env.render()

    if done:
        obs = env.reset()

env.close()
```

macOS 运行：

```bash
mjpython run_lift.py
```

Linux：

```bash
python run_lift.py
```

官方最小示例也是通过 `suite.make()` 创建环境，然后循环执行 `env.step(action)` 和 `env.render()`。([robosuite](https://robosuite.ai/docs/basicusage.html))

---

# 八、运行一次 `env.step()` 时发生了什么

假设你的动作是：

```python
action = [
    0.1, 0.0, 0.0,    # 末端向 x 方向移动
    0.0, 0.0, 0.0,    # 不旋转
    -1.0,              # 夹爪状态
]
```

调用：

```python
obs, reward, done, info = env.step(action)
```

内部大致经过：

```text
1. robosuite 接收 action

2. Controller 将末端动作转换成关节目标

3. Controller 根据当前关节状态计算力矩

4. 力矩写入 MuJoCo actuator

5. MuJoCo 执行多个物理时间步

6. MuJoCo 更新：
   - 关节位置
   - 关节速度
   - 物体位姿
   - 接触关系
   - 传感器

7. robosuite 收集观测

8. 环境计算 reward 和 success

9. 返回 obs、reward、done、info
```

策略频率和物理仿真频率通常不同。例如策略以 20 Hz 提供动作，robosuite 可以在两个策略动作之间执行多个更高频率的 MuJoCo 仿真步。([robosuite](https://robosuite.ai/docs/modules/controllers.html))

---

# 九、robosuite 的观测是什么

打印：

```python
print(obs.keys())
```

可能看到类似：

```text
robot0_joint_pos
robot0_joint_vel
robot0_eef_pos
robot0_eef_quat
robot0_gripper_qpos
robot0_proprio-state
object-state
agentview_image
```

对于两个机器人，会出现：

```text
robot0_proprio-state
robot1_proprio-state
```

相机图像也可以直接加入 observation：

```python
env = suite.make(
    env_name="Lift",
    robots="Panda",

    has_renderer=False,
    has_offscreen_renderer=True,

    use_camera_obs=True,
    use_object_obs=False,

    camera_names="agentview",
    camera_heights=256,
    camera_widths=256,
)
```

随后：

```python
obs = env.reset()
image = obs["agentview_image"]
```

robosuite 的相机、深度图和分割图可以自动加入 observation 字典；proprioception 则包括关节、末端执行器和夹爪等状态。([robosuite](https://robosuite.ai/docs/modules/sensors.html))

对你的 CommVLA，未来主要读取：

```text
每个机器人自己的腕部图像
每个机器人自己的 proprioception
共享或统一的任务语言
```

而 `object-state` 可以提供给脚本专家，但不应该默认提供给训练中的 VLA。

---

# 十、robosuite 的标准任务和自定义任务

robosuite 已提供一些任务：

```text
Lift
Stack
Door
PickPlace
NutAssembly
TwoArmLift
TwoArmHandover
TwoArmTransport
TwoArmPegInHole
```

它们适合：

- 学习 API；
- 测试控制器；
- 检查数据记录；
- 参考环境实现。

但是你的三臂、四臂任务不能只靠配置标准环境完成，最终需要写自定义 Environment。

---

# 十一、自定义环境到底要写什么

一个自定义任务通常包含五个核心部分。

## 1. `_load_model()`

创建场景：

```text
加载多个 Panda
设置机械臂底座位置
创建桌子
创建物体
创建摄像机
组合成 ManipulationTask
```

robosuite 官方自定义环境教程也采用：

```text
创建 world
→ 创建 robot
→ 创建 gripper
→ 创建 arena
→ 创建 object
→ 合并模型
→ 交给 MuJoCo
```

的流程。([robosuite](https://robosuite.ai/docs/tutorials/add_environment.html))

## 2. `_setup_references()`

找到重要物体在 MuJoCo 中的索引，例如：

```python
self.red_cube_body_id
self.drawer_joint_id
self.target_site_id
```

之后才能快速读取：

```text
方块位置
抽屉开合程度
目标区域位置
```

## 3. `_setup_observables()`

决定返回哪些观测：

```text
Robot 0 腕部图像
Robot 1 腕部图像
每个机器人 proprioception
目标物体是否被抓住
```

训练时和专家时可以使用不同观测。

## 4. `_reset_internal()`

每次 episode 开始时：

```text
重置机器人
随机放置物体
关闭抽屉
清除任务阶段
采样目标物体
```

robosuite 提供 `placement_initializer` 和位置采样器，用于在 reset 时生成无碰撞物体位置。([robosuite](https://robosuite.ai/docs/modules/environments.html))

## 5. `reward()` 和 `_check_success()`

例如：

```python
def _check_success(self):
    return self.red_cube_inside_drawer()
```

这就是任务定义。

环境并不需要知道模型采用 CommVLA 还是普通 VLA；它只负责提供观测、接收动作并判断任务结果。

---

# 十二、robosuite 怎样组合多个机器人

标准双臂任务可以这样创建：

```python
env = suite.make(
    env_name="TwoArmLift",
    robots=["Panda", "Panda"],
    env_configuration="opposed",
)
```

动作是两个机器人的动作拼接：

```text
Robot 0 action | Robot 1 action
```

可以检查：

```python
print(env.action_dim)

for i, robot in enumerate(env.robots):
    print(i, robot.action_dim)
    robot.print_action_info()
```

当前版本还提供 `create_action_vector()` 等帮助接口，用来根据各个机器人部件的动作构造正确的完整动作向量。([robosuite](https://robosuite.ai/docs/simulation/controller?utm_source=chatgpt.com))

对于你自己的三臂环境，理想接口是：

```python
env = NArmWorkspaceEnv(
    robots=["Panda", "Panda", "Panda"],
)
```

内部保存：

```python
env.robots[0]
env.robots[1]
env.robots[2]
```

但机械臂在桌子周围的具体位置、朝向、工作空间和动作分割，需要你在自定义环境中定义。

---

# 十三、robosuite 怎样采集数据

robosuite 提供遥操作设备和数据采集工具，包括：

```text
键盘
SpaceMouse
DualSense
MuJoCo GUI
```

也提供演示回放脚本和 HDF5 演示数据结构。([robosuite](https://robosuite.ai/docs/algorithms/demonstrations.html?utm_source=chatgpt.com))

对于自动专家，你也可以直接记录：

```python
trajectory = []

obs = env.reset()

while not done:
    action = expert.act(env)

    next_obs, reward, done, info = env.step(action)

    trajectory.append(
        {
            "obs": obs,
            "action": action,
            "reward": reward,
            "done": done,
        }
    )

    obs = next_obs
```

robosuite 的 `DataCollectionWrapper` 可以保存 rollout 中的 MuJoCo 状态和动作，并提供状态回放示例。([robosuite](https://robosuite.ai/docs/demos.html?utm_source=chatgpt.com))

你的项目后面应当在此基础上额外保存：

```text
每个 agent 的 RGB
每个 agent 的 proprioception
每个 agent 的 action
任务语言
num_agents
success
MuJoCo state
```

---

# 十四、对你的项目来说，应该学到什么程度

你不需要先完整学习 MuJoCo 再学习 robosuite。

正确顺序是：

## 第一阶段：理解 MuJoCo 基础

只需要掌握：

```text
MJCF XML 的基本结构
body / joint / geom / actuator / camera
MjModel 和 MjData
qpos / qvel / ctrl
mj_step
接触和物体位姿读取
```

目标不是自己写 Panda，而是看懂 robosuite 最后生成的物理模型。

## 第二阶段：熟悉 robosuite 标准环境

依次运行：

```text
Lift
PickPlace
Door
TwoArmLift
TwoArmHandover
```

每次都打印：

```python
env.action_spec
env.action_dim
obs.keys()
env.robots
```

这样你会逐渐理解动作和观测。

## 第三阶段：阅读三个源码文件

重点阅读：

```text
lift.py
two_arm_handover.py
two_arm_lift.py
```

不要从整个代码库开始读。

观察它们如何实现：

```text
_load_model
_setup_references
_setup_observables
_reset_internal
reward
_check_success
```

官方也建议开发自定义环境时参考已有标准环境源码。([robosuite](https://robosuite.ai/docs/tutorials/add_environment.html))

## 第四阶段：复制 Lift 创建自己的环境

先创建：

```text
MultiObjectLift
```

变化只包括：

```text
桌面放三个方块
每回合指定一个目标方块
其他方块是干扰物
```

先不要加第二个机器人。

## 第五阶段：改成双臂

创建：

```text
TwoArmOpenAndPlace
```

再逐步扩展成：

```text
NArmWorkspaceEnv
```

---

# 十五、你现在最适合做的第一个实践

在 Codex 中按照下面三个小任务推进。

### 任务一：运行标准环境

建立源码版 robosuite，运行：

```bash
mjpython -m robosuite.demos.demo_random_action
```

选择 Panda 和 Lift。

### 任务二：检查接口

写一个 `inspect_lift.py`，打印：

```python
print(env.action_dim)
print(env.action_spec)
print(obs.keys())
print(env.robots)
print(env.robots[0].action_dim)
env.robots[0].print_action_info()
```

### 任务三：查看底层 MuJoCo

在 robosuite 环境中访问：

```python
model = env.sim.model
data = env.sim.data

print(data.qpos)
print(data.qvel)
print(data.ctrl)
print(data.time)
```

这样你会真正看到两层之间的关系：

```text
robosuite:
    obs、action、robot、task、controller

MuJoCo:
    qpos、qvel、ctrl、contact、body pose
```

理解这三个程序以后，再进入自定义双臂任务开发会清楚很多。

---

**Sources:**

- [Modeling - MuJoCo Documentation](https://mujoco.readthedocs.io/en/latest/modeling.html?utm_source=chatgpt.com)
- [Overview — robosuite 1.5 documentation](https://robosuite.ai/docs/overview.html?utm_source=chatgpt.com)



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)