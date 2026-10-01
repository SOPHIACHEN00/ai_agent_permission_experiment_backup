"""Single-writer, role-isolated cost journal. Amounts are integer nanodollars."""
from __future__ import annotations
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re

ROLES = frozenset({'human', 'task'})
USAGE_KEYS = frozenset({'prompt_tokens', 'completion_tokens', 'cached_tokens'})

def _integer(value, *, positive=False):
    if type(value) is not int or value < int(positive):
        raise ValueError('invalid_budget_integer')

class OnlineBudget:
    def __init__(self, directory: Path, *, caps_nusd: dict[str,int],
                 call_caps: dict[str,int], resume: bool=False):
        if type(resume) is not bool or set(caps_nusd) != ROLES or set(call_caps) != ROLES:
            raise ValueError('invalid_budget_configuration')
        for value in (*caps_nusd.values(), *call_caps.values()):
            _integer(value, positive=True)
        self.caps = dict(caps_nusd)
        self.call_caps = dict(call_caps)
        self.records = {}
        self.stopped = False
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.journal = self.directory / 'attempts.jsonl'
        self._stream = None
        header = {'event':'header', 'schema':'role_budget_v1',
                  'caps_nusd':self.caps, 'call_caps':self.call_caps}
        try:
            flags = os.O_RDWR | (0 if resume else os.O_CREAT | os.O_EXCL)
            fd = os.open(self.journal, flags, 0o600)
            self._stream = os.fdopen(fd, 'r+', encoding='utf-8')
            fcntl.flock(self._stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            if resume:
                lines = self._stream.readlines()
                if not lines or any(not line.endswith('\n') for line in lines):
                    raise ValueError('incomplete_journal')
                if json.loads(lines[0]) != header:
                    raise ValueError('budget_configuration_changed')
                for line in lines[1:]:
                    event = json.loads(line)
                    self._validate(event)
                    self._apply(event)
                self.assert_resumable()
            else:
                self._append(header)
        except Exception:
            self.close()
            raise RuntimeError('budget_journal_unavailable_or_not_resumable') from None

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    def _append(self, event: dict) -> None:
        if self._stream is None:
            raise RuntimeError('budget_closed')
        self._stream.seek(0, os.SEEK_END)
        self._stream.write(json.dumps(event, sort_keys=True, separators=(',', ':')) + '\n')
        self._stream.flush()
        os.fsync(self._stream.fileno())

    def _validate(self, event: dict) -> None:
        kind = event.get('event')
        expected = {
            'reserve': {'event','role','request_id','upper_nusd','prompt_sha256'},
            'settle': {'event','role','request_id','cost_upper_nusd','usage'},
            'fail': {'event','role','request_id','stage','error_type'},
        }
        if kind not in expected or set(event) != expected[kind] or event['role'] not in ROLES:
            raise ValueError('invalid_budget_event')
        rid = event['request_id']
        if not isinstance(rid,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',rid):
            raise ValueError('invalid_request_id')
        key = (event['role'],rid)
        if kind == 'reserve':
            _integer(event['upper_nusd'],positive=True)
            if not isinstance(event['prompt_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',event['prompt_sha256']):
                raise ValueError('invalid_prompt_hash')
            if key in self.records:
                raise ValueError('duplicate_request')
            if self.stopped:
                raise RuntimeError('run_stopped')
            totals = self.summary()[event['role']]
            if (totals['attempts'] >= self.call_caps[event['role']] or
                totals['settled_upper_nusd'] + totals['reserved_unknown_nusd'] +
                event['upper_nusd'] > self.caps[event['role']]):
                raise RuntimeError('budget_exhausted_before_send')
        else:
            if key not in self.records:
                raise ValueError('unknown_request')
            record = self.records[key]
            if kind == 'settle':
                _integer(event['cost_upper_nusd'])
                if record['cost'] is not None or event['cost_upper_nusd'] > record['reserved']:
                    raise ValueError('invalid_settlement')
                usage = event['usage']
                if type(usage) is not dict or not set(usage) <= USAGE_KEYS:
                    raise ValueError('invalid_usage_metadata')
                for value in usage.values():
                    _integer(value)
            else:
                if record['failed']:
                    raise ValueError('duplicate_failure')
                for field in ('stage','error_type'):
                    if not isinstance(event[field],str) or not re.fullmatch(r'[A-Za-z_]{1,80}',event[field]):
                        raise ValueError('invalid_failure_metadata')

    def _apply(self, event: dict) -> None:
        key = (event['role'],event['request_id'])
        if event['event'] == 'reserve':
            self.records[key] = {'reserved':event['upper_nusd'],'cost':None,'failed':False}
        elif event['event'] == 'settle':
            self.records[key]['cost'] = event['cost_upper_nusd']
        else:
            self.records[key]['failed'] = True
            self.stopped = True

    def _record(self, event: dict) -> None:
        self._validate(event)
        self._append(event)
        self._apply(event)

    def reserve(self, role: str, request_id: str, upper_nusd: int, prompt_sha256: str) -> None:
        self._record(dict(event='reserve',role=role,request_id=request_id,
                          upper_nusd=upper_nusd,prompt_sha256=prompt_sha256))

    def settle(self, role: str, request_id: str, cost_upper_nusd: int, usage: dict) -> None:
        self._record(dict(event='settle',role=role,request_id=request_id,
                          cost_upper_nusd=cost_upper_nusd,usage=dict(usage)))

    def fail(self, role: str, request_id: str, stage: str, error_type: str) -> None:
        self._record(dict(event='fail',role=role,request_id=request_id,
                          stage=stage,error_type=error_type))

    def summary(self) -> dict:
        result = {}
        for role in sorted(ROLES):
            rows = [row for (r,_),row in self.records.items() if r == role]
            result[role] = {'attempts':len(rows), 'cap_nusd':self.caps[role],
                'call_cap':self.call_caps[role], 'stopped':self.stopped,
                'settled_upper_nusd':sum(row['cost'] or 0 for row in rows),
                'reserved_unknown_nusd':sum(row['reserved'] for row in rows if row['cost'] is None)}
        return result

    def assert_resumable(self) -> None:
        if self.stopped or any(row['cost'] is None for row in self.records.values()):
            raise RuntimeError('unresolved_or_failed_call_requires_manual_review')

    def marker(self) -> str:
        return hashlib.sha256(self.journal.read_bytes()).hexdigest()
