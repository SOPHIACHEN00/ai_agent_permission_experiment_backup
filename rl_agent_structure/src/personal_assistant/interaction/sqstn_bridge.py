"""Read-only S-QSTN adapter. Compiles prompts; never loads keys or dispatches APIs."""
from dataclasses import dataclass
from pathlib import Path
import inspect
import json
import sys
from ..config import PermissionConfig
from ..contracts.permission import PermissionChoice as C, canonical_hash, contract_json_round_trip
from .history import UserHistory, ObservedAnswer


LABEL_TO_CHOICE = {'No, never share': C.DENY_PERSIST, 'No, but ask me next time': C.DENY_REASK,
                   'Yes, but ask me next time': C.ALLOW_ONCE, 'Yes, always share': C.ALLOW_REUSE}


@dataclass(frozen=True)
class PromptEnvelope:
    status: str
    messages: tuple
    public_request: dict
    simulator_private_audit: dict
    request_id: str


class SQSTNBridge:
    def __init__(self, root: Path, user_id: str, profile_id: str, history: UserHistory):
        self.root = Path(root).resolve()
        if history.user_id != user_id: raise ValueError('foreign history')
        self.user_id, self.profile_id, self.history = user_id, profile_id, history
        # Only this dependency's package; no run.py, provider client or .env.
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(self.root))
        from sqstn.retrieval.simulator import RetrievalSimulator
        self.simulator = RetrievalSimulator(self.root)
        self._pending, self._parsed = {}, {}

    def compile_request(self, binding, key, position, persist_rounds, *, before_event_index=None, request_id=None):
        PermissionConfig(persist_rounds)
        if position.user_id != self.user_id or key.user_id != self.user_id:
            raise ValueError('foreign request')
        if key not in binding.keys_for(self.user_id, position.task_id): raise ValueError('unknown task key')
        boundary = self.history.next_event_index if before_event_index is None else before_event_index
        question = binding.questionnaire_key(key)
        public = {'query_id': binding.query_id, 'key': contract_json_round_trip(key),
                  'round': position.round_index, 'persist_rounds': persist_rounds}
        request_id = request_id or 'sqstn_' + canonical_hash((position, key, boundary))[:24]
        if question is None:
            return PromptEnvelope('manual_confirmation_required', (), public, {'reason': 'not_original_questionnaire_item'}, request_id)
        from sqstn.core.memory import PublicMemory
        from sqstn.core.runtime import SQSTNWrapper
        signature = inspect.signature(SQSTNWrapper._messages_for_persona)
        if not {'memory', 'current_turn', 'retrieval', 'retrieval_mode'} <= set(signature.parameters):
            raise RuntimeError('S-QSTN internal memory interface changed')
        memory = PublicMemory(self.root / 'sqstn', self.user_id, horizon_turns=16)
        labels = {v: k for k, v in LABEL_TO_CHOICE.items()}
        for a in self.history.view(boundary):
            memory.append({'event_id': a.response_id, 'subject_id': self.user_id,
                'event_type': 'permission_response_recorded', 'turn_index': a.event_index,
                'event_time': f'observed:{a.event_index}', 'source': 'runner_derived',
                'verification_status': 'verified', 'respondent_visible': True,
                'evidence_ref': 'received_answer:' + a.response_id,
                'scope': {'tool': a.key.tool, 'data_type': getattr(a.key, 'data_item', 'task_setup')},
                'metadata': {'answer': labels[a.choice]}})
        user_id = self.user_id

        class MemoryWrapper(SQSTNWrapper):
            def _messages_for_persona(self, pid, persona, row, **kwargs):
                kwargs['memory'], kwargs['current_turn'] = memory, boundary - 1
                return super()._messages_for_persona(user_id, persona, row, **kwargs)

        # Per-adapter wrapper, not a global monkey-patch. Retrieval/calibration stays intact.
        self.simulator.wrapper = MemoryWrapper(self.root / 'sqstn')
        compiled = self.simulator.compile(self.profile_id, question[0], question[1], question[2], sample_id=self.user_id)
        base_hash = compiled['prompt_sha256']
        protocol = (f'\n\nAgent protocol B: Always/Never apply to this exact user, Wu domain, backend tool, '
                    f'recipient, original data item and read/write direction across queries for {persist_rounds} task rounds '
                    f'including this task (expires before round {position.round_index + persist_rounds}). '
                    'Reusing consent does not renew it. Once applies to this explicitly requested access only. '
                    'Revoked or expired consent must be requested again. Never suppresses repeated requests. '
                    'This is a category-level synthetic protocol, not unrestricted real-world resource access. '
                    f'Public request: {json.dumps(public, ensure_ascii=False, sort_keys=True)}')
        messages = [dict(m) for m in compiled['messages']]
        messages[0]['content'] += protocol
        audit = {k: v for k, v in compiled.items() if k != 'messages'}
        audit.update(base_prompt_sha256=base_hash, b_prompt_sha256=canonical_hash(messages),
                     memory_event_ids=[e['event_id'] for e in memory.events], protocol='wu_category_rounds_v2')
        fingerprint = (binding.query_id, key, position, boundary)
        if request_id in self._pending and self._pending[request_id] != fingerprint:
            raise ValueError('request ID reused for different context')
        self._pending[request_id] = fingerprint
        return PromptEnvelope('ready', tuple(messages), public, audit, request_id)

    def parse_reply(self, response, request_id):
        if request_id not in self._pending: raise ValueError('unknown request')
        def unique(pairs):
            data = {}
            for key, value in pairs:
                if key in data: raise ValueError('duplicate JSON key')
                data[key] = value
            return data
        try: data = json.loads(response, object_pairs_hook=unique) if isinstance(response, str) else response
        except (ValueError, TypeError): raise ValueError('invalid answer JSON') from None
        if not isinstance(data, dict) or set(data) != {'answer'} or data['answer'] not in LABEL_TO_CHOICE:
            raise ValueError('expected original four-option answer, not a clarification')
        choice = LABEL_TO_CHOICE[data['answer']]
        q, key, position, boundary = self._pending[request_id]
        if request_id in self._parsed:
            if self._parsed[request_id].choice != choice: raise ValueError('conflicting duplicate answer')
            return self._parsed[request_id]
        answer = ObservedAnswer(self.user_id, q, key, choice, request_id, self.history.next_event_index, 'sqstn')
        self._parsed[request_id] = answer
        return answer


class SQSTNResponder:
    """Injectable human-side transport. None/unknown items remain waiting, not allowed."""
    def __init__(self, bridge, user_context, transport=None, *, response_source='sqstn'):
        if bridge.user_id != user_context.user_id or bridge.history is not user_context.history:
            raise ValueError('responder must share exactly this user history')
        if response_source not in ('sqstn', 'explicit_fixture'): raise ValueError('explicit simulator provenance required')
        self.bridge, self.context, self.transport = bridge, user_context, transport
        self.response_source, self.envelopes = response_source, {}

    def __call__(self, message):
        from .human_channel import HumanReply
        if message.kind != 'permission': return None
        session = self.context._sessions[self.context.position.task_id]
        step = next((s for s in session.task.steps if s.step_id == message.step_id), None)
        scope = message.requested_scope
        if step is None or scope is None: raise ValueError('permission message is not a current task need')
        declared = next((s for s in step.operation_scopes if all(getattr(s, name) == getattr(scope, name)
            for name in ('domain', 'tool', 'resource', 'operation', 'purpose', 'recipient', 'retention'))
            and set(scope.data_attributes) <= set(s.data_attributes)), None)
        if declared is None: raise ValueError('message scope differs from manifest')
        keys = session.binding.keys_for_scope(declared, self.context.user_id, self.context.position.task_id)
        keys = tuple(k for k in keys if not scope.data_attributes or getattr(k, 'data_item', None) in scope.data_attributes)
        if len(keys) != 1: raise ValueError('one original questionnaire item per message required')
        envelope = self.bridge.compile_request(session.binding, keys[0], self.context.position,
            self.context.ledger.config.persist_rounds, request_id=message.message_id)
        self.envelopes[message.message_id] = envelope
        if envelope.status != 'ready' or self.transport is None: return None
        raw = self.transport(envelope)
        if raw is None: return None
        answer = self.bridge.parse_reply(raw, envelope.request_id)
        return HumanReply(message.message_id, 'permission', answer.choice, source=self.response_source)
