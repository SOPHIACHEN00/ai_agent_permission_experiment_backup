"""Result contract shared by the four-action task dispatcher."""
from dataclasses import dataclass
@dataclass(frozen=True)
class DispatchResult:
    kind: str
    events: tuple = ()
    pending_human: object = None
