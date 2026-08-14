# Teleoperation camera layout design

Date: 2026-08-14

## Objective

Make the task window more balanced without changing simulation, camera rendering,
recording, review, or dataset behavior. Reduce the visual dominance of the global
camera, keep both wrist views immediately visible, and move trajectory management
below the task controls.

## Desktop layout

The task workspace becomes a single-column page containing two rows:

1. A task panel with status, cameras, controls, stage selection and keyboard help.
2. A data-management section containing pending review, saved episodes and trash.

Inside the task panel, the camera region uses a 60/40 two-column grid:

- The left column contains the global camera.
- The right column contains the sender and receiver wrist cameras stacked vertically.
- In the single-arm task, the receiver view remains hidden and the sender wrist view
  stays at the top of the right column.

On desktop, the global-camera column determines the complete camera-row height. The
right column uses a non-size-contributing slot that stretches to exactly that height.
For a dual-arm task, the sender and receiver wrist views divide the slot into two equal
rows. For a single-arm task, the sender wrist view occupies the complete slot.

Wrist images use proportional `object-fit: contain` rendering. No part of a wrist image
is cropped or distorted; unused horizontal space uses the existing dark image
background. Camera titles and inter-view spacing are included inside the matched-height
right column, so the bottom of the receiver view does not extend below the global view.

The control buttons and instructions span the full task-panel width below the camera
grid. No camera endpoint, polling rate, JPEG settings or image resolution changes.

## Data-management layout

The pending-review panel moves below the task panel and spans the full available width
when visible. The saved-episode panel and recoverable-trash panel appear beneath it in
a two-column grid. If pending review is hidden, saved episodes and trash move up without
leaving an empty placeholder.

All existing element IDs and JavaScript behavior remain stable so start, finish,
review, confirm, discard, replay, delete and restore continue to work without API
changes.

## Responsive behavior

At viewport widths below 850 pixels, the camera grid becomes one column in this order:
global, sender wrist, receiver wrist. At this breakpoint the desktop equal-height slot
is disabled and all images return to their natural full-width aspect ratio. The
saved/trash grid also becomes one column. The page must not create horizontal scrolling
at supported widths.

## Verification

Automated HTTP/HTML tests verify that the response contains the camera grid, equal-height
wrist slot, stacked wrist column and lower data-management section while preserving all
existing control and review element IDs. The complete existing test suite must remain
green. A live server screenshot or browser inspection confirms the desktop 60/40
equal-height layout, uncropped wrist views and responsive one-column ordering.
