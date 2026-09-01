"""Pure terminal outcome evaluation for Increment 8 lifecycle episodes.

The evaluator consumes only environment-owned aggregate evidence.  It has no
access to action traces, graph/family identities, dynamic-programming values,
or oracle policies.  Only :attr:`LifecycleOutcomeResult.reward` may enter a
learning transition; every other result field is audit-only evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


OUTCOME_EVALUATOR_VERSION = "budgeted_lifecycle_v0"


class LifecycleTerminationKind(str, Enum):
    """Publicly meaningful lifecycle closure kinds in the frozen v0 study."""

    IN_PROGRESS = "in_progress"
    NATURAL_COMPLETION = "natural_completion"
    HORIZON_EXHAUSTION = "horizon_exhaustion"
    GRAPH_EXHAUSTION = "graph_exhaustion"
    DENY_WITH_REASON = "deny_with_reason"
    ESCALATE = "escalate"
    IRREVERSIBLE_FAILURE = "irreversible_failure"


class LifecycleOutcomeConstraint(str, Enum):
    """Frozen terminal constraints, ordered as they are evaluated."""

    UTILITY_TARGET = "utility_target"
    NO_PENDING_REQUIRED_TASK = "no_pending_required_task"
    ACCEPTED_TERMINATION = "accepted_termination"
    PROMPT_BUDGET = "prompt_budget"
    EXPOSURE_BUDGET = "exposure_budget"
    DIRECTIVE_COMPLIANCE = "directive_compliance"
    UNIQUE_TASK_UTILITY_CREDIT = "unique_task_utility_credit"
    ZERO_MASK_VIOLATIONS = "zero_mask_violations"
    ZERO_UNAUTHORIZED_COMMITTED_EFFECTS = "zero_unauthorized_committed_effects"
    ZERO_MONITOR_BLOCKED_EXECUTION_ATTEMPTS = (
        "zero_monitor_blocked_execution_attempts"
    )


class LifecycleOutcomeReason(str, Enum):
    """Coarse audit-only result reason; never a policy or replay feature."""

    IN_PROGRESS = "in_progress"
    CONSTRAINTS_SATISFIED = "constraints_satisfied"
    CONSTRAINTS_FAILED = "constraints_failed"


_ACCEPTED_TERMINATIONS = frozenset(
    {
        LifecycleTerminationKind.NATURAL_COMPLETION,
        LifecycleTerminationKind.HORIZON_EXHAUSTION,
        LifecycleTerminationKind.GRAPH_EXHAUSTION,
    }
)

_CONSTRAINT_ORDER = tuple(LifecycleOutcomeConstraint)


def _require_nonnegative_exact_int(value: object, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative exact integer")


@dataclass(frozen=True, slots=True)
class LifecycleOutcomeEvidence:
    """Frozen environment-owned facts sufficient for binary evaluation.

    Counts are aggregate trusted facts rather than reconstructed traces.  The
    duplicate-credit counter enforces the separate v0 invariant that one
    public task instance contributes utility at most once.
    """

    closed: bool
    termination_kind: LifecycleTerminationKind
    accumulated_task_utility: int
    utility_target: int
    pending_required_task_count: int
    prompts_used: int
    prompt_budget: int
    exposure_used: int
    exposure_budget: int
    disable_required_directives_issued: int
    disable_required_directives_obeyed: int
    duplicate_task_utility_credits: int
    mask_violations: int
    unauthorized_committed_effects: int
    monitor_blocked_execution_attempts: int

    def __post_init__(self) -> None:
        if type(self.closed) is not bool:
            raise ValueError("closed must be an exact boolean")
        if not isinstance(self.termination_kind, LifecycleTerminationKind):
            raise ValueError("termination_kind must be typed")
        if self.closed == (self.termination_kind is LifecycleTerminationKind.IN_PROGRESS):
            raise ValueError("closed and termination_kind disagree")

        for field_name in (
            "accumulated_task_utility",
            "utility_target",
            "pending_required_task_count",
            "prompts_used",
            "prompt_budget",
            "exposure_used",
            "exposure_budget",
            "disable_required_directives_issued",
            "disable_required_directives_obeyed",
            "duplicate_task_utility_credits",
            "mask_violations",
            "unauthorized_committed_effects",
            "monitor_blocked_execution_attempts",
        ):
            _require_nonnegative_exact_int(getattr(self, field_name), field_name)
        if self.utility_target < 1:
            raise ValueError("utility_target must be positive")
        if (
            self.disable_required_directives_obeyed
            > self.disable_required_directives_issued
        ):
            raise ValueError("obeyed directives cannot exceed issued directives")


@dataclass(frozen=True, slots=True)
class LifecycleOutcomeResult:
    """Immutable binary outcome plus audit-only constraint diagnostics."""

    terminal: bool
    reward: int
    success: bool
    reason_code: LifecycleOutcomeReason
    failed_constraints: tuple[LifecycleOutcomeConstraint, ...]
    evaluator_version: str = OUTCOME_EVALUATOR_VERSION

    def __post_init__(self) -> None:
        if type(self.terminal) is not bool or type(self.success) is not bool:
            raise ValueError("terminal and success must be exact booleans")
        if type(self.reward) is not int or self.reward not in {0, 1}:
            raise ValueError("reward must be the exact integer 0 or 1")
        if not isinstance(self.reason_code, LifecycleOutcomeReason):
            raise ValueError("reason_code must be typed")
        if not isinstance(self.failed_constraints, tuple) or any(
            not isinstance(item, LifecycleOutcomeConstraint)
            for item in self.failed_constraints
        ):
            raise ValueError("failed_constraints must be a typed tuple")
        if len(set(self.failed_constraints)) != len(self.failed_constraints):
            raise ValueError("failed_constraints must not contain duplicates")
        canonical_failures = tuple(
            constraint
            for constraint in _CONSTRAINT_ORDER
            if constraint in self.failed_constraints
        )
        if self.failed_constraints != canonical_failures:
            raise ValueError("failed_constraints must use frozen evaluation order")
        if self.evaluator_version != OUTCOME_EVALUATOR_VERSION:
            raise ValueError("outcome evaluator version is frozen")

        if self.reason_code is LifecycleOutcomeReason.IN_PROGRESS:
            if self.terminal or self.reward != 0 or self.success or self.failed_constraints:
                raise ValueError("in-progress outcome metadata disagrees")
        elif self.reason_code is LifecycleOutcomeReason.CONSTRAINTS_SATISFIED:
            if not self.terminal or self.reward != 1 or not self.success or self.failed_constraints:
                raise ValueError("successful outcome metadata disagrees")
        elif (
            not self.terminal
            or self.reward != 0
            or self.success
            or not self.failed_constraints
        ):
            raise ValueError("failed outcome metadata disagrees")


class BudgetedLifecycleOutcomeEvaluator:
    """Evaluate the frozen v0 terminal conjunction without path matching."""

    @staticmethod
    def evaluate(evidence: LifecycleOutcomeEvidence) -> LifecycleOutcomeResult:
        if not isinstance(evidence, LifecycleOutcomeEvidence):
            raise ValueError("evidence must be LifecycleOutcomeEvidence")
        if not evidence.closed:
            return LifecycleOutcomeResult(
                terminal=False,
                reward=0,
                success=False,
                reason_code=LifecycleOutcomeReason.IN_PROGRESS,
                failed_constraints=(),
            )

        checks = (
            (
                LifecycleOutcomeConstraint.UTILITY_TARGET,
                evidence.accumulated_task_utility >= evidence.utility_target,
            ),
            (
                LifecycleOutcomeConstraint.NO_PENDING_REQUIRED_TASK,
                evidence.pending_required_task_count == 0,
            ),
            (
                LifecycleOutcomeConstraint.ACCEPTED_TERMINATION,
                evidence.termination_kind in _ACCEPTED_TERMINATIONS,
            ),
            (
                LifecycleOutcomeConstraint.PROMPT_BUDGET,
                evidence.prompts_used <= evidence.prompt_budget,
            ),
            (
                LifecycleOutcomeConstraint.EXPOSURE_BUDGET,
                evidence.exposure_used <= evidence.exposure_budget,
            ),
            (
                LifecycleOutcomeConstraint.DIRECTIVE_COMPLIANCE,
                evidence.disable_required_directives_obeyed
                == evidence.disable_required_directives_issued,
            ),
            (
                LifecycleOutcomeConstraint.UNIQUE_TASK_UTILITY_CREDIT,
                evidence.duplicate_task_utility_credits == 0,
            ),
            (
                LifecycleOutcomeConstraint.ZERO_MASK_VIOLATIONS,
                evidence.mask_violations == 0,
            ),
            (
                LifecycleOutcomeConstraint.ZERO_UNAUTHORIZED_COMMITTED_EFFECTS,
                evidence.unauthorized_committed_effects == 0,
            ),
            (
                LifecycleOutcomeConstraint.ZERO_MONITOR_BLOCKED_EXECUTION_ATTEMPTS,
                evidence.monitor_blocked_execution_attempts == 0,
            ),
        )
        failed_constraints = tuple(
            constraint for constraint, satisfied in checks if not satisfied
        )
        success = not failed_constraints
        return LifecycleOutcomeResult(
            terminal=True,
            reward=int(success),
            success=success,
            reason_code=(
                LifecycleOutcomeReason.CONSTRAINTS_SATISFIED
                if success
                else LifecycleOutcomeReason.CONSTRAINTS_FAILED
            ),
            failed_constraints=failed_constraints,
        )


def evaluate_lifecycle_outcome(
    evidence: LifecycleOutcomeEvidence,
) -> LifecycleOutcomeResult:
    """Functional entry point for the frozen Increment 8 outcome evaluator."""

    return BudgetedLifecycleOutcomeEvaluator.evaluate(evidence)


__all__ = [
    "OUTCOME_EVALUATOR_VERSION",
    "BudgetedLifecycleOutcomeEvaluator",
    "LifecycleOutcomeConstraint",
    "LifecycleOutcomeEvidence",
    "LifecycleOutcomeReason",
    "LifecycleOutcomeResult",
    "LifecycleTerminationKind",
    "evaluate_lifecycle_outcome",
]
