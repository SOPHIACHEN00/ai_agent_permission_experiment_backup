"""Authorization grant-field/control-step proxy; distinct from actual disclosure."""
from __future__ import annotations

from pa_rl.contracts import AuthorizationStatus, contract_json_round_trip
from .contracts import GrantView

EXPOSURE_SCHEMA = 'authorization_grant_field_steps_v1'


def effective(grant: GrantView, step: int) -> bool:
    return (grant.status == AuthorizationStatus.ACTIVE and grant.remaining_uses != 0
            and grant.expires_at_step >= step)


def footprint(grants: tuple[GrantView, ...], step: int) -> int:
    return sum(len(grant.scope.data_attributes) for grant in grants if effective(grant, step))


class ExposureAccount:
    def __init__(self) -> None:
        self.used = 0
        self._events: list[dict] = []
        self._tokens: set[str] = set()

    def charge(self, token: str, grants: tuple[GrantView, ...], step: int) -> None:
        if token in self._tokens:
            raise ValueError('controller decision exposure already charged')
        self._tokens.add(token)
        value = footprint(grants, step)
        self.used += value
        self._events.append({'decision_token': token, 'logical_step': step, 'footprint': value,
                             'cumulative': self.used, 'before': contract_json_round_trip(grants), 'after': None})

    def settle(self, token: str, grants: tuple[GrantView, ...]) -> None:
        if not self._events or self._events[-1]['decision_token'] != token or self._events[-1]['after'] is not None:
            raise ValueError('exposure settlement does not match pending decision')
        self._events[-1]['after'] = contract_json_round_trip(grants)

    def snapshot(self) -> list[dict]:
        return contract_json_round_trip(self._events)
