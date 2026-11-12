"""Protocol versions for the independent personal assistant package."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeLimits:
    max_control_steps: int
    max_planner_turns: int
    max_permission_messages: int
    max_active_gates: int
    max_checkpoints: int
    max_read_instances: int
    max_write_instances: int
    max_release_steps: int
    max_candidates: int

    def __post_init__(self):
        from dataclasses import fields
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or value < 1:
                raise ValueError('runtime limits must be explicit positive integers')
        if self.max_candidates < 2:
            raise ValueError('candidate capacity must leave room for RELEASE and END')


# Functional fixture only; not a research/deployment default.
FUNCTIONAL_LIMITS = RuntimeLimits(256, 32, 128, 128, 64, 256, 256, 128, 512)


@dataclass(frozen=True)
class EnvironmentConfig:
    environment_version: str = "personal_assistant_v1"
    contract_version: str = "permission_contracts_v1"
    authorization_policy: str = "permission_policy_v1"


DEFAULT_CONFIG = EnvironmentConfig()


PERMISSION_SCHEMA = 'four_action_consent_gate_v1'


@dataclass(frozen=True)
class PermissionConfig:
    persist_rounds: int

    def __post_init__(self):
        if type(self.persist_rounds) is not int or self.persist_rounds < 1:
            raise ValueError('persist_rounds must be a positive integer (not bool)')
