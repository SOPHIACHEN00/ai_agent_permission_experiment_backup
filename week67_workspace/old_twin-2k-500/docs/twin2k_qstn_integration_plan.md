# Task Plan: Integrating Twin-2K-500 with QSTN

## Goal

Specify a technically implementable, reviewer-defensible way to use Twin-2K-500
personae in the QSTN-based permission-response simulator without overstating
privacy-behaviour validity.

## Phases

- [x] Phase 1: Establish the integration question and research constraints.
- [x] Phase 2: Verify Twin-2K-500 data contract and official simulation flow.
- [x] Phase 3: Inspect the available QSTN/project interface and map components.
- [x] Phase 4: Design a minimal API-based integration and validation protocol.
- [x] Phase 5: Deliver implementation guidance and research positioning.

## Key Questions

1. Which Twin persona representation should enter QSTN, and at what cost/fidelity trade-off?
2. Which layer of the permission simulator can Twin support without claiming unavailable ground truth?
3. What is the smallest pilot that establishes engineering and methodological readiness?

## Decisions Made

- API-based inference is acceptable; local vLLM/GPU execution is not required.
- The permission agent, rather than general human digital-twin simulation, remains
  the paper's main contribution.

## Errors Encountered

- None.

## Status

**Complete** — the integration guide defines the separate Twin lane, protected
target-domain calibration lane, and bounded pilot.
