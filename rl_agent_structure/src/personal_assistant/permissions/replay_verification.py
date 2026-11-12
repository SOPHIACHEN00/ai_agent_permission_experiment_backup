"""Memoize full replay verification, not permission decisions.

Assumptions: the replay implementation and its manifest dependencies are stable
within one single-threaded run. This cache does not defend against arbitrary
Python code replacement or mutation of the verifier itself. Every event value
is serialized on every check; every current record is still compared. No
length-only or last-hash-only fast path is used.
"""
from copy import deepcopy
from dataclasses import replace
from types import MappingProxyType

from ..contracts.permission import canonical_json, contract_json_round_trip, freeze_value
from .ledger_events import LedgerEvent


class ReplayVerificationCache:
    """One-entry cache of independently reconstructed, detached records."""

    def __init__(self, replay, *, enabled=True):
        if not callable(replay) or type(enabled) is not bool:
            raise ValueError('replay callable and boolean enabled flag required')
        self._replay = replay
        self.enabled = enabled
        self._events_json = None
        self._expected_events = None
        self._expected_records = None
        self._cache_hits = self._full_calls = self._failures = 0

    @property
    def stats(self):
        """Read-only snapshot; counters do not participate in authorization."""
        return MappingProxyType({'cache_hits': self._cache_hits,
                                 'full_calls': self._full_calls,
                                 'verification_failures': self._failures})

    def verify(self, events, records, *, cache=None):
        """Return False on malformed/tampered input or any replay failure.

        cache=False always runs the unchanged full replay baseline. With None,
        the instance's enabled flag applies. Cache values never alias live
        ledger events/records; an unchanged sequence alone cannot validate
        modified current records.
        """
        try:
            use_cache = self.enabled if cache is None else cache
            if type(use_cache) is not bool:
                raise ValueError('boolean cache switch required')
            events, records = tuple(events), tuple(records)
            if not events or any(type(event) is not LedgerEvent for event in events):
                raise ValueError('typed complete ledger events required')
            # An immutable full value snapshot also detects prefix modifications
            # when the length and the untouched final event hash are unchanged.
            events_json = canonical_json(events)
            if use_cache and self._events_json == events_json and self._expected_events == events:
                self._cache_hits += 1
                expected = self._expected_records
            else:
                self._full_calls += 1
                expected = tuple(self._replay(events).records())
                if use_cache:
                    self._events_json = events_json
                    # JSON alone conflates tuple/list and stringified mapping
                    # keys; preserve full-replay equality semantics as well.
                    self._expected_events = tuple(replace(event, payload=freeze_value(
                        contract_json_round_trip(event.payload))) for event in events)
                    self._expected_records = deepcopy(expected)
                    expected = self._expected_records
            verified = expected == records
            if not verified:
                self._failures += 1
            return bool(verified)
        except TimeoutError:
            # A run deadline is not evidence of ledger corruption. Let the
            # experiment controller stop promptly and record its real cause.
            raise
        except Exception:
            # Never return cached success when parsing or replay fails.
            self._failures += 1
            self._events_json = self._expected_events = self._expected_records = None
            return False
