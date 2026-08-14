# Public GitHub Repository Design

Date: 2026-08-14

## Objective

Publish the current multi-arm MuJoCo simulation project as a public GitHub repository
at `NEBULIS-Lab/MuJoCo-sim`. The repository must preserve the implemented tasks,
collection and conversion code, engineering history, complete ChatGPT discussion,
sample trajectory data, and generated teaching artifacts so that another researcher can
clone it and follow the documented workflow.

## Repository Identity

- Owner: `NEBULIS-Lab`.
- Name: `MuJoCo-sim`.
- Visibility: public.
- Default branch: `main`.
- Initial publication: one direct initial commit to `main`, with no bootstrap pull
  request.
- License: MIT, copyright `NEBULIS-Lab`.
- GitHub account used for creation and push: the currently active `clzJY` CLI account.

The repository description will identify it as a MuJoCo and robosuite platform for
multi-arm teleoperation, demonstration collection, replay, and VLA dataset preparation.
Topics will include `mujoco`, `robosuite`, `robotics`, `multi-arm`, `teleoperation`, and
`vla`.

## Published Content

The initial commit includes all current portable project content:

- Python package code in `src/`;
- executable and preparation scripts in `scripts/`;
- regression and integration tests in `tests/`;
- user documentation plus design and implementation records in `docs/`;
- `ChatGPT-MuJoCo 多机械臂仿真.md` as part of the project record;
- `pyproject.toml`, Conda and pip dependency files;
- the current three-trajectory scripted Lift example
  `datasets/lift_scripted_test_3.h5` (approximately 17 MB);
- all current files under `artifacts/`, including render checks, replay media, and
  generated COMMVLA metadata;
- the detailed root `README.md`, `.gitignore`, and MIT `LICENSE`.

The initial repository does not use Git LFS because its only HDF5 file is well below
GitHub's 100 MB per-file limit and direct Git storage gives learners a complete clone.
Future large or human-collected datasets will require explicit review and should use
Git LFS or GitHub Releases instead of silently entering normal Git history.

## Excluded Machine State

The following content stays on the server but is not version-controlled because it is
generated, non-portable, or potentially sensitive:

- `.venv/` and `.conda/` environments;
- Python bytecode, pytest caches, packaging `.egg-info/`, logs, editor, and operating
  system cache files;
- `.env` files, private keys, and credential files;
- future datasets and artifacts unless they are deliberately added to the teaching
  allowlist.

The ignore rules will allow the existing sample HDF5 and current artifacts while
protecting against accidental publication of newly collected data.

## README Content

The README will be Chinese-first and self-contained. It will cover:

1. project purpose, status, and the Panda-versus-Piper scope;
2. implemented single-arm Lift and dual-arm colored-cube handover tasks;
3. architecture, directory layout, and component responsibilities;
4. tested Linux, Python, MuJoCo, robosuite, CUDA-driver, and EGL assumptions;
5. Conda, venv, dependency-lock, and offline-install guidance;
6. headless runtime, EGL/OSMesa smoke tests, and complete pytest verification;
7. web teleoperation startup, Mac SSH tunnels, alternate local ports, and the shared
   single-session limitation for multiple computers;
8. keyboard controls, staged single-operator dual-arm handover, event-gated 20 Hz
   capture, review, confirmation, deletion, and recovery;
9. included sample dataset and artifacts, HDF5 schema, replay commands, and COMMVLA
   preparation;
10. current limitations, data-publication policy, development workflow, and the planned
    three-arm and four-arm extensions.

README commands must match the current CLI arguments and must not imply that a GPU is
required for every path when OSMesa is available.

## Safety and Validation

Before the public push:

1. scan tracked candidates for credentials, private keys, and obvious secrets;
2. inspect the complete staged path list and file sizes;
3. confirm ignored virtual environments and caches are absent from the Git index;
4. verify the sample HDF5 structure and generated teaching artifacts;
5. run the complete EGL pytest suite and Python syntax compilation;
6. render-check the README and validate internal relative links;
7. confirm `gh` is authenticated as `clzJY` and the target repository does not already
   exist.

Repository creation is attempted only under `NEBULIS-Lab`. If organization permissions
prevent `clzJY` from creating a public repository, publication stops and reports that
specific permission blocker; it must not fall back to a personal-account repository.

## Ongoing Workflow

The initial direct push establishes `main`. Subsequent task development should use
feature branches and pull requests so new simulation environments, data formats, and
large-data publication decisions receive review. Each future public dataset must be
checked for size, provenance, privacy, and licensing before it is added.
