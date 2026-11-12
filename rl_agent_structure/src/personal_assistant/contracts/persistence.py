"""Category authority is separate from the concrete compiled tool call."""
from dataclasses import dataclass
from .permission import _non_empty


@dataclass(frozen=True)
class RoundPosition:
    user_id: str
    task_id: str
    round_index: int
    decision_index: int = 0

    def __post_init__(self):
        _non_empty(self.user_id, 'user_id')
        _non_empty(self.task_id, 'task_id')
        if type(self.round_index) is not int or self.round_index < 1:
            raise ValueError('round_index must be positive')
        if type(self.decision_index) is not int or self.decision_index < 0:
            raise ValueError('decision_index must be nonnegative')


@dataclass(frozen=True)
class PermissionKey:
    user_id: str
    domain: str
    tool: str
    recipient: str
    data_item: str
    direction: str

    def __post_init__(self):
        for name in ('user_id', 'domain', 'tool', 'recipient', 'data_item'):
            _non_empty(getattr(self, name), name)
        if self.direction not in ('read', 'write'):
            raise ValueError('invalid dataflow direction')


@dataclass(frozen=True)
class SetupPermissionKey:
    user_id: str
    task_id: str
    query_id: int
    tool: str
    parameters_hash: str

    def __post_init__(self):
        for name in ('user_id', 'task_id', 'tool', 'parameters_hash'):
            _non_empty(getattr(self, name), name)
        if type(self.query_id) is not int or self.query_id not in range(65):
            raise ValueError('invalid Wu query')


AuthorityKey = PermissionKey | SetupPermissionKey


@dataclass(frozen=True)
class AuthorizationBundle:
    call_hash: str
    user_id: str
    task_id: str
    record_revisions: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class BundleReservation:
    reservation_id: str
    call_hash: str
    user_id: str
    task_id: str
    record_revisions: tuple[tuple[str, int], ...]
