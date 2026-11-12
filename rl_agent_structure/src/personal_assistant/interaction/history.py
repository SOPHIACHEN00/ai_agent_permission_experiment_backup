"""Observed responses only; never an authority cache."""
from dataclasses import dataclass
from ..contracts.permission import PermissionChoice
from ..contracts.persistence import PermissionKey, SetupPermissionKey


@dataclass(frozen=True)
class ObservedAnswer:
    user_id: str
    query_id: int
    key: PermissionKey | SetupPermissionKey
    choice: PermissionChoice
    response_id: str
    event_index: int
    source: str = 'human'

    def __post_init__(self):
        if self.key.user_id != self.user_id or not isinstance(self.choice, PermissionChoice):
            raise ValueError('answer user/choice mismatch')
        if type(self.event_index) is not int or self.event_index < 1:
            raise ValueError('positive observed event index required')


class UserHistory:
    def __init__(self, user_id):
        self.user_id, self._answers = user_id, []

    def append(self, answer):
        if not isinstance(answer, ObservedAnswer) or answer.user_id != self.user_id:
            raise ValueError('history is user local')
        duplicate = next((a for a in self._answers if a.response_id == answer.response_id), None)
        if duplicate:
            if duplicate != answer: raise ValueError('conflicting historical response')
            return
        if self._answers and answer.event_index <= self._answers[-1].event_index:
            raise ValueError('history must be appended in observed order')
        self._answers.append(answer)

    def view(self, before_event_index=None):
        return tuple(a for a in self._answers if before_event_index is None or a.event_index < before_event_index)

    @property
    def next_event_index(self):
        return 1 if not self._answers else self._answers[-1].event_index + 1
