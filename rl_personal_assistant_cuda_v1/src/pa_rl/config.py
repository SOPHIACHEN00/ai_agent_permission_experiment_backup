"""Versioned configuration for the v0.10 contract layer."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentConfig:
    environment_version: str = "pa_env_v0.10"
    contract_version: str = "contracts_v0.1"
    authorization_policy: str = "authorization_policy_v0"
    candidate_limit: int = 16
    public_event_history_length: int = 4
    response_rate_smoothing_alpha: float = 1.0

    def __post_init__(self) -> None:
        if self.candidate_limit != 16:
            raise ValueError("v0 candidate_limit must be 16")
        if self.public_event_history_length != 4:
            raise ValueError("v0 public_event_history_length must be 4")
        if self.response_rate_smoothing_alpha != 1.0:
            raise ValueError("v0 response_rate_smoothing_alpha must be 1.0")


DEFAULT_CONFIG = EnvironmentConfig()
