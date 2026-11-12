"""Reserved semantic safety review; no model, authorization or bypass implementation.

Future position: review the finalized call before the reference monitor. A PASS
only means the semantic checker found no objection; it never grants permission.
The caller must still use the ledger and monitor. This interface is not wired to
an agent loop yet, and an unconfigured checker never silently returns PASS.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from ..contracts.tool_call import CompiledCall


class SafetyVerdict(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class SafetyDecision:
    verdict: SafetyVerdict
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.verdict, SafetyVerdict):
            raise ValueError("safety verdict must be typed")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("safety decision requires a reason")


class SafetyChecker(Protocol):
    def review(self, call: CompiledCall) -> SafetyDecision:
        """Inspect only the necessary call information; never mutate authority."""
        ...


class UnconfiguredSafetyChecker:
    def review(self, call: CompiledCall) -> SafetyDecision:
        raise NotImplementedError("No safety model is configured; no safety approval was produced")
