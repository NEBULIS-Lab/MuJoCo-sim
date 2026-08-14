"""Two-Panda colored-cube handover task with matching open boxes."""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import robosuite.utils.transform_utils as T
from robosuite.environments.manipulation.two_arm_env import TwoArmEnv
from robosuite.models.arenas import TableArena
from robosuite.models.objects import BoxObject, CompositeObject
from robosuite.models.tasks import ManipulationTask
from robosuite.utils.mjcf_utils import array_to_string
from robosuite.utils.observables import Observable, sensor

GLOBAL_CAMERA = "agentview"
LOCAL_CAMERAS = ("robot0_eye_in_hand", "robot1_eye_in_hand")
CONTROL_FREQUENCY = 20
GLOBAL_CAMERA_POSITION = (1.22, 0.0, 1.58)
GLOBAL_CAMERA_QUATERNION = (0.638, 0.304, 0.304, 0.638)
GLOBAL_CAMERA_FOVY = 52.0

COLORS = OrderedDict(
    [
        ("red", (0.88, 0.12, 0.10, 1.0)),
        ("green", (0.10, 0.70, 0.20, 1.0)),
        ("blue", (0.10, 0.28, 0.90, 1.0)),
    ]
)


def _open_box(name: str, rgba: tuple[float, ...]) -> CompositeObject:
    """Create a fixed, open-top box from a floor and four walls."""
    outer = 0.15
    height = 0.075
    wall = 0.009
    floor = 0.008
    half = outer / 2
    # CompositeObject locations are relative to its center when requested.
    return CompositeObject(
        name=name,
        total_size=[half, half, height / 2],
        geom_types=["box"] * 5,
        geom_sizes=[
            [half, half, floor / 2],
            [wall / 2, half, height / 2],
            [wall / 2, half, height / 2],
            [(outer - 2 * wall) / 2, wall / 2, height / 2],
            [(outer - 2 * wall) / 2, wall / 2, height / 2],
        ],
        geom_locations=[
            [0, 0, -height / 2 + floor / 2],
            [-half + wall / 2, 0, 0],
            [half - wall / 2, 0, 0],
            [0, -half + wall / 2, 0],
            [0, half - wall / 2, 0],
        ],
        geom_names=["floor", "left_wall", "right_wall", "front_wall", "back_wall"],
        geom_rgbas=[rgba] * 5,
        locations_relative_to_center=True,
        joints=None,
        density=500.0,
        duplicate_collision_geoms=True,
    )


class ColoredHandoverBox(TwoArmEnv):
    """Pass a requested colored cube from Panda 0 to Panda 1 and sort it."""

    def __init__(
        self,
        robots=("Panda", "Panda"),
        env_configuration="opposed",
        controller_configs=None,
        base_types="NullMount",
        gripper_types="default",
        initialization_noise=None,
        table_full_size=(1.10, 1.50, 0.05),
        table_friction=(1.0, 5e-3, 1e-4),
        use_camera_obs=True,
        use_object_obs=True,
        reward_scale=1.0,
        reward_shaping=True,
        has_renderer=False,
        has_offscreen_renderer=True,
        render_camera=GLOBAL_CAMERA,
        render_collision_mesh=False,
        render_visual_mesh=True,
        render_gpu_device_id=-1,
        control_freq=CONTROL_FREQUENCY,
        lite_physics=True,
        horizon=1200,
        ignore_done=True,
        hard_reset=True,
        camera_names=(GLOBAL_CAMERA, *LOCAL_CAMERAS),
        camera_heights=256,
        camera_widths=256,
        camera_depths=False,
        camera_segmentations=None,
        renderer="mjviewer",
        renderer_config=None,
        seed=None,
    ):
        self.table_full_size = np.asarray(table_full_size, dtype=float)
        self.table_friction = table_friction
        self.table_offset = np.array([0.0, 0.0, 0.80])
        self.use_object_obs = use_object_obs
        self.reward_scale = reward_scale
        self.reward_shaping = reward_shaping

        self.cube_half_size = 0.025
        self.box_outer_size = 0.15
        self.box_height = 0.075
        self.cube_positions = {
            "red": np.array([-0.22, -0.23, self.table_offset[2] + self.cube_half_size + 0.002]),
            "green": np.array([0.00, -0.23, self.table_offset[2] + self.cube_half_size + 0.002]),
            "blue": np.array([0.22, -0.23, self.table_offset[2] + self.cube_half_size + 0.002]),
        }
        self.box_positions = {
            "red": np.array([-0.22, 0.28, self.table_offset[2] + self.box_height / 2]),
            "green": np.array([0.00, 0.28, self.table_offset[2] + self.box_height / 2]),
            "blue": np.array([0.22, 0.28, self.table_offset[2] + self.box_height / 2]),
        }
        self.target_color = "red"
        self.sender_has_grasped = False
        self.receiver_has_grasped = False
        self.handover_completed = False

        super().__init__(
            robots=robots,
            env_configuration=env_configuration,
            controller_configs=controller_configs,
            base_types=base_types,
            gripper_types=gripper_types,
            initialization_noise=initialization_noise,
            use_camera_obs=use_camera_obs,
            has_renderer=has_renderer,
            has_offscreen_renderer=has_offscreen_renderer,
            render_camera=render_camera,
            render_collision_mesh=render_collision_mesh,
            render_visual_mesh=render_visual_mesh,
            render_gpu_device_id=render_gpu_device_id,
            control_freq=control_freq,
            lite_physics=lite_physics,
            horizon=horizon,
            ignore_done=ignore_done,
            hard_reset=hard_reset,
            camera_names=camera_names,
            camera_heights=camera_heights,
            camera_widths=camera_widths,
            camera_depths=camera_depths,
            camera_segmentations=camera_segmentations,
            renderer=renderer,
            renderer_config=renderer_config,
            seed=seed,
        )

    @property
    def instruction(self) -> str:
        return (
            f"Pass the {self.target_color} cube from the sender arm to the receiver arm, "
            f"then place it in the open {self.target_color} box."
        )

    def _load_model(self):
        super()._load_model()

        # The two bases are bolted directly to the tabletop, not placed on
        # robosuite's default floor-standing Rethink mounts. A 1.24 m base
        # separation leaves a shared handover region without starting in
        # self-collision.
        for robot, rotation, side in zip(self.robots, (np.pi / 2, -np.pi / 2), (-1.0, 1.0)):
            orientation = np.array([0.0, 0.0, rotation])
            xpos = np.array([0.0, side * 0.62, self.table_offset[2]])
            robot.robot_model.set_base_xpos(xpos)
            robot.robot_model.set_base_ori(orientation)

        arena = TableArena(
            table_full_size=self.table_full_size,
            table_friction=self.table_friction,
            table_offset=self.table_offset,
        )
        arena.set_origin([0, 0, 0])
        # Camera looks along +x -> origin; the -y/+y robot sides appear left/right.
        arena.set_camera(
            camera_name=GLOBAL_CAMERA,
            pos=GLOBAL_CAMERA_POSITION,
            quat=GLOBAL_CAMERA_QUATERNION,
        )
        arena.worldbody.find(f".//camera[@name='{GLOBAL_CAMERA}']").set(
            "fovy", str(GLOBAL_CAMERA_FOVY)
        )

        self.cubes = OrderedDict()
        self.boxes = OrderedDict()
        for color, rgba in COLORS.items():
            cube = BoxObject(
                name=f"{color}_cube",
                size=[self.cube_half_size] * 3,
                rgba=rgba,
                density=350.0,
                friction=[1.0, 0.005, 0.0001],
                rng=self.rng,
            )
            box = _open_box(f"{color}_box", rgba)
            # CompositeObject is generated MJCF (rather than MujocoXMLObject),
            # so its fixed root pose is assigned on the generated root body.
            box._obj.set("pos", array_to_string(self.box_positions[color]))
            self.cubes[color] = cube
            self.boxes[color] = box

        self.model = ManipulationTask(
            mujoco_arena=arena,
            mujoco_robots=[robot.robot_model for robot in self.robots],
            mujoco_objects=[*self.cubes.values(), *self.boxes.values()],
        )

    def _setup_references(self):
        super()._setup_references()
        self.cube_body_ids = {
            color: self.sim.model.body_name2id(cube.root_body) for color, cube in self.cubes.items()
        }

    def _setup_observables(self):
        observables = super()._setup_observables()
        if not self.use_object_obs:
            return observables

        for color in COLORS:
            body_id = self.cube_body_ids[color]

            def position(obs_cache, body_id=body_id):
                return np.asarray(self.sim.data.body_xpos[body_id]).copy()

            position.__name__ = f"{color}_cube_pos"
            observables[position.__name__] = Observable(
                name=position.__name__,
                sensor=sensor(modality="object")(position),
                sampling_rate=self.control_freq,
            )

        @sensor(modality="object")
        def target_color_one_hot(obs_cache):
            return np.array([float(color == self.target_color) for color in COLORS], dtype=np.float32)

        observables[target_color_one_hot.__name__] = Observable(
            name=target_color_one_hot.__name__,
            sensor=target_color_one_hot,
            sampling_rate=self.control_freq,
        )
        return observables

    def _reset_internal(self):
        super()._reset_internal()
        if not self.deterministic_reset:
            # Slight jitter improves diversity while keeping the three colors easy to identify.
            for color, cube in self.cubes.items():
                position = self.cube_positions[color].copy()
                position[:2] += self.rng.uniform(-0.012, 0.012, size=2)
                yaw = self.rng.uniform(-np.pi / 8, np.pi / 8)
                quat = T.axisangle2quat(np.array([0.0, 0.0, yaw]))
                self.sim.data.set_joint_qpos(cube.joints[0], np.concatenate([position, quat]))

        self.target_color = str(self.rng.choice(list(COLORS)))
        self.sender_has_grasped = False
        self.receiver_has_grasped = False
        self.handover_completed = False

    def _task_state(self) -> dict[str, bool]:
        cube = self.cubes[self.target_color]
        sender_grasp = bool(self._check_grasp(self.robots[0].gripper, cube))
        receiver_grasp = bool(self._check_grasp(self.robots[1].gripper, cube))
        self.sender_has_grasped |= sender_grasp
        self.receiver_has_grasped |= receiver_grasp
        # Require evidence that the receiver held the cube after the sender had held it.
        if self.sender_has_grasped and receiver_grasp and not sender_grasp:
            self.handover_completed = True

        cube_pos = np.asarray(self.sim.data.body_xpos[self.cube_body_ids[self.target_color]])
        box_pos = self.box_positions[self.target_color]
        half_inner = self.box_outer_size / 2 - 0.012 - self.cube_half_size
        inside_xy = bool(np.all(np.abs(cube_pos[:2] - box_pos[:2]) < half_inner))
        inside_z = bool(
            self.table_offset[2] + 0.005
            < cube_pos[2]
            < self.table_offset[2] + self.box_height + self.cube_half_size
        )
        return {
            "sender_grasp": sender_grasp,
            "receiver_grasp": receiver_grasp,
            "handover_completed": self.handover_completed,
            "inside_target_box": inside_xy and inside_z,
        }

    def _check_success(self):
        state = self._task_state()
        return bool(state["handover_completed"] and state["inside_target_box"])

    def reward(self, action=None):
        state = self._task_state()
        if state["handover_completed"] and state["inside_target_box"]:
            reward = 1.0
        elif self.reward_shaping:
            target_pos = np.asarray(self.sim.data.body_xpos[self.cube_body_ids[self.target_color]])
            if self.handover_completed:
                distance = np.linalg.norm(target_pos - self.box_positions[self.target_color])
                reward = 0.75 + 0.20 * (1.0 - np.tanh(5.0 * distance))
            elif state["receiver_grasp"]:
                reward = 0.70
            elif self.sender_has_grasped:
                distance = np.linalg.norm(target_pos - self._eef1_xpos)
                reward = 0.35 + 0.25 * (1.0 - np.tanh(4.0 * distance))
            else:
                distance = np.linalg.norm(target_pos - self._eef0_xpos)
                reward = 0.25 * (1.0 - np.tanh(5.0 * distance))
        else:
            reward = 0.0
        return reward if self.reward_scale is None else reward * self.reward_scale

    def task_status(self) -> dict[str, object]:
        return {"target_color": self.target_color, **self._task_state()}


def make_handover_box_env(
    *,
    image_size: int = 256,
    horizon: int = 1200,
    seed: int | None = None,
):
    """Construct the exact dual-Panda environment used by collection and replay."""
    if seed is not None:
        np.random.seed(seed)
    return ColoredHandoverBox(
        robots=("Panda", "Panda"),
        has_renderer=False,
        has_offscreen_renderer=True,
        use_camera_obs=True,
        camera_names=(GLOBAL_CAMERA, *LOCAL_CAMERAS),
        camera_heights=[image_size] * 3,
        camera_widths=[image_size] * 3,
        reward_shaping=True,
        control_freq=CONTROL_FREQUENCY,
        horizon=horizon,
        ignore_done=True,
        seed=seed,
    )


def top_left_rgb(image: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(np.flipud(image))


def frame_from_observation(observation: dict, camera: str) -> np.ndarray:
    return top_left_rgb(observation[f"{camera}_image"])


def proprio_from_observation(observation: dict, robot_index: int) -> np.ndarray:
    return np.concatenate(
        [
            observation[f"robot{robot_index}_joint_pos"],
            observation[f"robot{robot_index}_gripper_qpos"],
        ]
    ).astype(np.float32)
