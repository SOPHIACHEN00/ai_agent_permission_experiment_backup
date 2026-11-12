"""Immutable, hash-chained commands; replay runs the same state transitions."""
from dataclasses import dataclass
from ..contracts.permission import canonical_hash, freeze_value, contract_json_round_trip
from ..contracts.persistence import PermissionKey, SetupPermissionKey


@dataclass(frozen=True)
class LedgerEvent:
    sequence: int
    kind: str
    payload: object
    previous_hash: str | None
    event_hash: str


def event_for(events, kind, payload):
    sequence = len(events) + 1
    previous = events[-1].event_hash if events else None
    payload = freeze_value(contract_json_round_trip(payload))
    digest = canonical_hash((sequence, kind, payload, previous))
    return LedgerEvent(sequence, kind, payload, previous, digest)


def key_data(key):
    return {'kind': 'setup' if isinstance(key, SetupPermissionKey) else 'data',
            'value': contract_json_round_trip(key)}


def key_from(data):
    cls = SetupPermissionKey if data['kind'] == 'setup' else PermissionKey
    return cls(**data['value'])
