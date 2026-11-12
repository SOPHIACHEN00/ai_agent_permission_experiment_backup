"""Public authorization-footprint features, not an actual-disclosure metric."""
from __future__ import annotations
from ..contracts.permission import AuthorizationStatus
from ..contracts.task import GrantView


def effective(grant: GrantView, step: int) -> bool:
    return (grant.status == AuthorizationStatus.ACTIVE and grant.remaining_uses != 0
            and grant.expires_at_step >= step)


def footprint(grants: tuple[GrantView, ...], step: int) -> int:
    return sum(len(grant.scope.data_attributes) for grant in grants if effective(grant, step))
