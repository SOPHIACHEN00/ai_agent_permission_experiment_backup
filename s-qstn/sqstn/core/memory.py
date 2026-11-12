"""Public-event boundary around the frozen bounded-memory implementation."""
from copy import deepcopy
import json
from .engine import StateStoreV2


class PublicMemory:
    def __init__(self, root, subject_id, horizon_turns=16):
        if type(horizon_turns) is not int or horizon_turns < 0:
            raise ValueError('A nonnegative explicit memory horizon is required')
        self.subject_id = str(subject_id)
        self.horizon = horizon_turns
        config = root.parent / 'config/memory'
        self.assets = [json.loads((config / name).read_text(encoding='utf-8')) for name in
                       ('event_schema.json', 'state_schema.json', 'retention_policy.json')]
        self.events = []
        self.event_ids = set()

    def _store(self):
        return StateStoreV2(*self.assets, memory_horizon_turns=self.horizon,
                            memory_horizon_source='explicit_wrapper_configuration_not_human_calibrated')

    def append(self, event):
        allowed = {'event_id', 'subject_id', 'event_type', 'turn_index', 'event_time', 'source',
                   'verification_status', 'respondent_visible', 'evidence_ref', 'scope', 'metadata'}
        if set(event) - allowed:
            raise ValueError('Unsupported event fields')
        if event.get('subject_id') != self.subject_id:
            raise ValueError('Cross-user memory is forbidden')
        if event.get('source') not in {'external_verified', 'runner_derived'}:
            raise ValueError('Hidden synthetic/oracle events are forbidden')
        if event.get('verification_status') != 'verified' or event.get('respondent_visible') is not True:
            raise ValueError('Only verified, publicly observed events may enter memory')
        if not isinstance(event.get('evidence_ref'), str) or not event['evidence_ref'].strip():
            raise ValueError('Public event evidence reference required')
        if type(event.get('turn_index')) is not int or event['turn_index'] < 0:
            raise ValueError('turn_index must be a nonnegative integer, not a boolean')
        metadata = event.get('metadata', {})
        if not isinstance(metadata, dict) or set(metadata) - {'trust_dimension', 'burden_bucket', 'answer'}:
            raise ValueError('Unsupported event metadata; oracle payloads are forbidden')
        if 'trust_dimension' in metadata and metadata['trust_dimension'] not in {'competence', 'integrity', 'benevolence', 'unknown'}:
            raise ValueError('Invalid trust dimension')
        if 'burden_bucket' in metadata and metadata['burden_bucket'] not in {
            'unknown', 'none_explicit', 'low_explicit', 'medium_explicit', 'high_explicit', 'bounded_recent_history'}:
            raise ValueError('Invalid burden bucket')
        if 'answer' in metadata:
            from .runtime import LABELS
            if event.get('event_type') != 'permission_response_recorded' or metadata['answer'] not in LABELS:
                raise ValueError('An answer is allowed only as an already observed permission response')
        if event.get('event_id') in self.event_ids:
            raise ValueError('Duplicate event id')
        # Validate before changing this wrapper's ledger.
        sanitized = {k: deepcopy(v) for k, v in event.items() if k not in {'evidence_ref', 'respondent_visible'}}
        self._store().append_event(sanitized)
        self.events.append(deepcopy(event))
        self.event_ids.add(event['event_id'])

    def view(self, current_turn):
        if type(current_turn) is not int or current_turn < 0:
            raise ValueError('current_turn must be a nonnegative integer')
        store = self._store()
        # Replay only past/current events. Legacy snapshots otherwise include future-state updates.
        events = sorted((e for e in self.events if e['turn_index'] <= current_turn),
                        key=lambda e: (e['turn_index'], e['event_id']))
        for event in events:
            store.append_event({k: v for k, v in event.items() if k not in {'evidence_ref', 'respondent_visible'}})
        audits = store.transition_audit(self.subject_id)
        for audit, event in zip(audits, events):
            audit['evidence_ref'] = event['evidence_ref']
            audit['respondent_visible'] = True
        return store.memory_view(self.subject_id, current_turn), audits
