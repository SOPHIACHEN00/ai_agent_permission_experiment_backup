"""Task-local execution capabilities G; factual consent C stays in the ledger."""
from dataclasses import dataclass
from ..contracts.permission import canonical_hash

@dataclass(frozen=True)
class Gate:
    key: object
    record_id: str
    need_id: str

class CapabilityGates:
    def __init__(self, task_id, max_active):
        self.task_id, self.max_active = task_id, max_active
        self._items = {}
        self.events = []

    def active_keys(self, ledger, position):
        if position.task_id != self.task_id:
            raise ValueError('foreign task gate')
        for key, g in tuple(self._items.items()):
            record = ledger.decision(key, position, need_id=g.need_id)
            if record is None or not record.allows or record.record_id != g.record_id:
                del self._items[key]
                self.events.append(('invalidate', key))
        return frozenset(self._items)

    def activate(self, keys, ledger, position, need_id):
        keys = frozenset(keys)
        current = self.active_keys(ledger, position)
        records = {k: ledger.decision(k, position, need_id=need_id) for k in keys}
        if not keys or any(r is None or not r.allows for r in records.values()):
            raise ValueError('activation requires actual valid consent')
        if len(current | keys) > self.max_active:
            raise ValueError('gate limit exceeded')
        for k, r in records.items():
            self._items[k] = Gate(k, r.record_id, need_id)
        self.events.append(('activate', tuple(sorted(keys, key=canonical_hash))))

    def covers(self, keys, ledger, position, need_id):
        active = self.active_keys(ledger, position)
        for k in keys:
            if k not in active:
                return False
            r = ledger.decision(k, position, need_id=need_id)
            if r is None or not r.allows or r.record_id != self._items[k].record_id:
                return False
        return True

    def release(self, keys, ledger, position):
        keys = frozenset(keys)
        if not keys or not keys <= self.active_keys(ledger, position):
            raise ValueError('release requires enabled task-local gates')
        for k in keys:
            del self._items[k]
        self.events.append(('release', tuple(sorted(keys, key=canonical_hash))))

    def clear(self):
        self.events.append(('cleanup', tuple(self._items)))
        self._items.clear()
