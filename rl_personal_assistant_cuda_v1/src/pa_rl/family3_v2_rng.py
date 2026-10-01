"""Exact counter-based denominator-five continuation branch draws."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterator

from .contracts import canonical_json
from .family3_v2_contracts import ContinuationModeV2


_UINT64_LIMIT = 2**64
_ACCEPTANCE_LIMIT = _UINT64_LIMIT - (_UINT64_LIMIT % 5)


@dataclass(frozen=True, slots=True)
class Family3V2BranchResidue:
    residue: int
    attempt: int
    accepted_uint64: int
    payload: str
    payload_sha256: str

    def __post_init__(self) -> None:
        if type(self.residue) is not int or not 0 <= self.residue < 5:
            raise ValueError("residue must be an exact integer in [0, 4]")
        if type(self.attempt) is not int or self.attempt < 0:
            raise ValueError("attempt must be a nonnegative exact integer")
        if type(self.accepted_uint64) is not int or not 0 <= self.accepted_uint64 < _ACCEPTANCE_LIMIT:
            raise ValueError("accepted draw must be an accepted exact uint64")
        if self.residue != self.accepted_uint64 % 5:
            raise ValueError("residue does not match the accepted uint64")
        if type(self.payload) is not str or not self.payload:
            raise ValueError("payload must be a non-empty string")
        if self.payload_sha256 != hashlib.sha256(self.payload.encode("utf-8")).hexdigest():
            raise ValueError("payload SHA-256 does not match payload")


def residue_from_uint64s(values: Iterator[int]) -> int:
    """Return the first accepted unbiased residue from an exact uint64 iterator."""
    limit = 2**64 - (2**64 % 5)
    for value in values:
        if type(value) is not int or not 0 <= value < 2**64:
            raise ValueError("draw must be an exact uint64")
        if value < limit:
            return value % 5
    raise ValueError("draw source ended before an accepted residue")


def _validate_uint64(name: str, value: object) -> int:
    if type(value) is not int or not 0 <= value < _UINT64_LIMIT:
        raise ValueError(f"{name} must be an exact uint64")
    return value


def _validate_uid(branch_coupling_uid: object) -> str:
    if type(branch_coupling_uid) is not str or len(branch_coupling_uid) != 64:
        raise ValueError("branch coupling UID must be a SHA-256 hex string")
    if any(character not in "0123456789abcdef" for character in branch_coupling_uid):
        raise ValueError("branch coupling UID must be lowercase hexadecimal")
    return branch_coupling_uid


def draw_family3_v2_branch_residue(
    root_seed: int,
    branch_coupling_uid: str,
    episode_ordinal: int,
) -> Family3V2BranchResidue:
    """Hash counter-indexed frozen payloads until an unbiased residue is accepted."""
    _validate_uint64("root seed", root_seed)
    _validate_uid(branch_coupling_uid)
    if type(episode_ordinal) is not int or episode_ordinal < 0:
        raise ValueError("episode ordinal must be a nonnegative exact integer")
    for attempt in range(_UINT64_LIMIT):
        payload = canonical_json([
            "i8_f3v2_branch_rng_v0", root_seed, branch_coupling_uid,
            episode_ordinal, "continuation_branch", 0, attempt,
        ])
        digest = hashlib.sha256(payload.encode("utf-8")).digest()
        value = int.from_bytes(digest[:8], byteorder="big", signed=False)
        if value < _ACCEPTANCE_LIMIT:
            return Family3V2BranchResidue(
                residue=value % 5,
                attempt=attempt,
                accepted_uint64=value,
                payload=payload,
                payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            )
    raise RuntimeError("counter-based branch RNG exhausted the uint64 attempt space")


def continuation_from_residue(
    forecast_exact_probability: Fraction,
    forecast_broader_probability: Fraction,
    residue: int,
) -> ContinuationModeV2:
    """Apply one of the two fixed forecast thresholds to an accepted residue."""
    if type(forecast_exact_probability) is not Fraction or type(forecast_broader_probability) is not Fraction:
        raise ValueError("forecast probabilities must be exact Fraction values")
    if (forecast_exact_probability, forecast_broader_probability) not in {
        (Fraction(4, 5), Fraction(1, 5)),
        (Fraction(1, 5), Fraction(4, 5)),
    }:
        raise ValueError("forecast probabilities must be the frozen denominator-five pair")
    if type(residue) is not int or not 0 <= residue < 5:
        raise ValueError("residue must be an exact integer in [0, 4]")
    return ContinuationModeV2.EXACT if residue < forecast_exact_probability.numerator else ContinuationModeV2.BROADER


__all__ = [
    "Family3V2BranchResidue",
    "continuation_from_residue",
    "draw_family3_v2_branch_residue",
    "residue_from_uint64s",
]
