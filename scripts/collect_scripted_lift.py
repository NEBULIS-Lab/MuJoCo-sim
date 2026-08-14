#!/usr/bin/env python3
"""Collect a few privileged-state Lift episodes to validate the data pipeline."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("datasets/lift_test.h5"))
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--max-steps", type=int, default=300)
    parser.add_argument("--image-size", type=int, default=256)
    parser.add_argument("--backend", choices=("egl", "osmesa"), default="egl")
    parser.add_argument("--egl-device", type=int, default=None)
    return parser.parse_args()


class OracleLiftPolicy:
    """A deliberately small state machine; not intended as the final dataset expert."""

    APPROACH = 0
    DESCEND = 1
    CLOSE = 2
    LIFT = 3

    def __init__(self) -> None:
        self.stage = self.APPROACH
        self.close_steps = 0
        self.cube_start = None

    @staticmethod
    def _move(current: np.ndarray, target: np.ndarray, gripper: float) -> np.ndarray:
        action = np.zeros(7, dtype=np.float32)
        action[:3] = np.clip((target - current) * 10.0, -0.6, 0.6)
        action[-1] = gripper
        return action

    def act(self, observation: dict) -> np.ndarray:
        eef = observation["robot0_eef_pos"]
        cube = observation["cube_pos"]
        if self.cube_start is None:
            self.cube_start = cube.copy()

        if self.stage == self.APPROACH:
            target = cube + np.array([0.0, 0.0, 0.15])
            if np.linalg.norm(target - eef) < 0.012:
                self.stage = self.DESCEND
            return self._move(eef, target, -1.0)

        if self.stage == self.DESCEND:
            # In robosuite's Panda model, robot0_eef_pos is the grip site
            # between the finger pads (not the wrist flange), so it should
            # converge to the cube center for a side grasp.
            target = cube.copy()
            if np.linalg.norm(target - eef) < 0.006:
                self.stage = self.CLOSE
            return self._move(eef, target, -1.0)

        if self.stage == self.CLOSE:
            self.close_steps += 1
            if self.close_steps >= 18:
                self.stage = self.LIFT
            action = np.zeros(7, dtype=np.float32)
            action[-1] = 1.0
            return action

        target = np.array(
            [self.cube_start[0], self.cube_start[1], self.cube_start[2] + 0.28]
        )
        return self._move(eef, target, 1.0)


def main() -> None:
    args = parse_args()
    os.environ["MUJOCO_GL"] = args.backend
    if args.egl_device is not None:
        os.environ["MUJOCO_EGL_DEVICE_ID"] = str(args.egl_device)

    from multiarm_sim.dataset import EpisodeBuffer, append_episode
    from multiarm_sim.lift import make_lift_env

    saved = []
    for episode_index in range(args.episodes):
        seed = args.seed + episode_index
        env = make_lift_env(image_size=args.image_size, horizon=args.max_steps + 1, seed=seed)
        policy = OracleLiftPolicy()
        buffer = EpisodeBuffer(seed=seed, source="scripted_oracle")
        try:
            observation = env.reset()
            success = False
            for _ in range(args.max_steps):
                action = policy.act(observation)
                state = env.sim.get_state().flatten().copy()
                next_observation, reward, done, _ = env.step(action)
                success = bool(env._check_success())
                buffer.append(
                    observation=observation,
                    sim_state=state,
                    action=action,
                    reward=reward,
                    done=done,
                    success=success,
                    stage=policy.stage,
                )
                observation = next_observation
                if success:
                    # Retain a few stable post-success frames.
                    for _ in range(5):
                        hold = np.zeros(7, dtype=np.float32)
                        hold[-1] = 1.0
                        state = env.sim.get_state().flatten().copy()
                        next_observation, reward, done, _ = env.step(hold)
                        buffer.append(
                            observation=observation,
                            sim_state=state,
                            action=hold,
                            reward=reward,
                            done=done,
                            success=True,
                            stage=policy.stage,
                        )
                        observation = next_observation
                    break
            name = append_episode(
                args.output,
                buffer,
                final_sim_state=env.sim.get_state().flatten(),
                success=success,
            )
            saved.append((name, len(buffer), success))
            print(f"{name}: steps={len(buffer)} success={success}")
        finally:
            env.close()
    if not all(item[2] for item in saved):
        raise RuntimeError(f"At least one scripted smoke episode failed: {saved}")
    print(f"dataset={args.output.resolve()}")


if __name__ == "__main__":
    main()
