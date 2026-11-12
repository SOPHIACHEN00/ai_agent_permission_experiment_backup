"""Four-action runner with distinct consent, task gates and bounded checkpoints."""
from .base import AgentRuntimeBase
from .adapter import ExecutionAdapter
from .store import LocalToolStore
from ..contracts.task import ControlView, AgentResult
from ..contracts.permission import ControllerAction as A, PublicEvent, contract_json_round_trip, canonical_hash
from ..planning.compiler import compile_intent
from ..permissions.ledger import UserAuthorizationLedger
from ..permissions.user_candidates import build_user_candidates
from ..permissions.user_dispatch import UserDispatcher
from ..permissions.gates import CapabilityGates
from ..interaction.human_channel import LocalHumanChannel
from ..integration.task_semantics import needed_keys

class UserTaskSession(AgentRuntimeBase):
    def __init__(self, binding, planner, user_context, channel, *, tools):
        self.binding, self.task, self.planner = binding, binding.task, planner
        self.user_context, self.policy = user_context, user_context.policy
        self.limits = user_context.runtime_limits
        self.max_planner_turns, self.max_control_steps = self.limits.max_planner_turns, self.limits.max_control_steps
        self.max_total_control_steps = self.max_control_steps + self.limits.max_release_steps + 1
        self.channel = channel if channel is not None else LocalHumanChannel()
        self.ledger = user_context.ledger
        self.gate = CapabilityGates(user_context.position.task_id, self.limits.max_active_gates)
        self.store = LocalToolStore(self.task.records, backend=tools,
            private_inputs=self.task.private_inputs, tool_models=self.task.tool_models)
        self.adapter = ExecutionAdapter(self.task, self.store, self.ledger, gate=self.gate)
        self.dispatcher = UserDispatcher(self)
        self._history, self._trace = [], []
        self._pending = self._waiting = self._ready = None
        self._turns = self._logical_step = self._prompts = self._escalations = self._release_steps = 0
        self._terminal = self._answer = self._answer_status = self._error = None
        self._closed = False
        self.permission_items = self.reused_allow_items = self.extra_permission_messages = 0
        self.idle_gate_key_checkpoints = self.suppressed_reask_items = 0
        self.terminal_active_gate_keys = None
        self.checkpoint_events, self.message_cost_events = [], []
        self._checkpoint_pending = None
        self._asked_needs, self._suppressed_seen = {}, set()
        self.answer_source = 'human'

    def _view(self):
        task_end = self._terminal is not None
        pending = None if task_end else self._pending
        candidates = build_user_candidates(pending, self._current_step(), self.ledger,
            self.user_context.position, gate=self.gate, task_end=task_end,
            end_reason=self._terminal, max_candidates=self.limits.max_candidates,
            allow_release=self._release_steps < self.limits.max_release_steps)
        records = tuple(r for r in self.ledger.records() if self.ledger._latest.get(r.key) == r.record_id)
        return ControlView(pending, (), candidates, tuple(self._history),
            self.user_context.position.decision_index, self._prompts,
            'task_end' if task_end else ('checkpoint' if self._checkpoint_pending else 'task'),
            self.user_context.position, records, self.user_context.history.view(),
            tuple(sorted(self.gate.active_keys(self.ledger, self.user_context.position), key=canonical_hash)))

    def _accept(self, result):
        super()._accept(result)
        if result.kind == 'limit':
            self._terminal = 'runtime_limit'

    def advance(self):
        if self._closed:
            return self._result(self._terminal)
        if self._ready is not None:
            self._ready = self._view()
            return self._ready
        while self._terminal is None:
            if self._waiting is not None:
                before = self._waiting
                try:
                    outcome = self.dispatcher.resolve(before, self._logical_step)
                except Exception as error:
                    self._terminal, self._error, self._waiting = 'human_error', type(error).__name__, None
                    break
                self._accept(outcome)
                if outcome.kind == 'waiting':
                    if outcome.pending_human == before:
                        return self._result('awaiting_human')
                    continue
                if self._terminal is not None:
                    break
            if self._logical_step >= self.max_control_steps:
                self._terminal = 'controller_limit'
                break
            # Reserve room for terminal accounting instead of clipping its value.
            if len(self.checkpoint_events) >= self.limits.max_checkpoints - 1 and self.checkpoint_events:
                self._terminal = 'checkpoint_limit'
                break
            if self._pending is None:
                if self._turns >= self.max_planner_turns:
                    self._terminal = 'planner_limit'
                    break
                step = self._current_step()
                self._turns += 1
                try:
                    decision = self.planner.next_decision(self.task.goal, tuple(self._history), self._available_calls(step))
                except Exception as error:
                    self._terminal, self._error = 'planner_error', type(error).__name__
                    break
                if getattr(decision, 'kind', None) == 'finish':
                    self._answer, self._answer_status = decision.answer, decision.answer_status
                    self._terminal = 'completed' if decision.answer_status == 'completed' else 'incomplete'
                    break
                try:
                    if step is None:
                        raise ValueError('all declared steps finished')
                    self._pending = compile_intent(decision, step, self._observed_ids(decision.tool),
                                                   validate_call=self.store.validate_call)
                except (ValueError, TypeError, AttributeError):
                    self._history.append(PublicEvent('intent_rejected', {'reason_code': 'invalid_task_intent'}))
                    continue
            break
        if (self._terminal is None and self._checkpoint_pending is not None
                and self._current_step() is not None
                and len(self.checkpoint_events) >= self.limits.max_checkpoints - 1):
            self._terminal = 'checkpoint_limit'
        try:
            self._ready = self._view()
        except ValueError as error:
            self._terminal, self._error = 'candidate_limit', str(error)
            self._ready = self._view()
        if self._ready.pending is not None:
            p = self.user_context.position
            for key in self.ledger.call_keys(self._ready.pending, p):
                record = self.ledger.decision(key, p, need_id=self._ready.pending.step_id)
                marker = (self._ready.pending.step_id, key)
                if record is not None and not record.allows and marker not in self._suppressed_seen:
                    self._suppressed_seen.add(marker)
                    self.suppressed_reask_items += 1
        return self._ready

    def validate_control(self, selected_id):
        if self._ready is None or self._waiting is not None or self._closed:
            raise ValueError('not at a controller boundary')
        if self._ready != self._view():
            raise ValueError('authority changed since observation')
        selected = next((c for c in self._ready.candidates if c.candidate_id == selected_id and c.valid), None)
        if selected is None:
            raise ValueError('unknown or masked candidate')
        return selected

    def _checkpoint(self, next_scope=None, *, terminal=False, opportunity=True):
        if not terminal and self._checkpoint_pending is None:
            return
        checkpoint_id = self._checkpoint_pending or 'terminal_without_tool'
        if any(e['checkpoint_id'] == checkpoint_id for e in self.checkpoint_events):
            return
        p = self.user_context.position
        active = self.gate.active_keys(self.ledger, p)
        step = None if terminal else self._current_step()
        needed = frozenset() if step is None else needed_keys(self.binding, step.step_id, next_scope, p.user_id, p.task_id)
        idle = active - needed
        if len(self.checkpoint_events) >= self.limits.max_checkpoints:
            raise RuntimeError('checkpoint budget accounting invariant violated')
        self.idle_gate_key_checkpoints += len(idle)
        self.checkpoint_events.append({'checkpoint_id': checkpoint_id, 'terminal': terminal,
            'release_opportunity': opportunity, 'active': [canonical_hash(k) for k in sorted(active, key=canonical_hash)],
            'needed': [canonical_hash(k) for k in sorted(needed, key=canonical_hash)],
            'idle': [canonical_hash(k) for k in sorted(idle, key=canonical_hash)], 'idle_count': len(idle)})
        self._checkpoint_pending = None

    def _finish(self, *, opportunity=True):
        self._checkpoint(terminal=True, opportunity=opportunity)
        self.terminal_active_gate_keys = tuple(sorted(
            self.gate.active_keys(self.ledger, self.user_context.position), key=canonical_hash))
        self.gate.clear()
        self.ledger.finish_task(self.user_context.position)
        self._closed = True

    def dispatch_control(self, selected_id, *, budget_stop=False):
        selected = self.validate_control(selected_id)
        view, self._ready = self._ready, None
        self._trace.append({'logical_step': view.logical_step, 'phase': view.phase,
            'selected': contract_json_round_trip(selected), 'intent': contract_json_round_trip(view.pending),
            'candidate_ids': [c.candidate_id for c in view.candidates],
            'valid_mask': [c.valid for c in view.candidates], 'dispatched': not budget_stop})
        self._logical_step += 1
        self.ledger.advance_decision(self.user_context.position)
        if budget_stop:
            self._terminal = 'budget_exhausted'
            return
        if selected.action == A.RELEASE:
            self._release_steps += 1
            self._accept(self.dispatcher.dispatch(selected, self._pending, self._logical_step))
            return
        if selected.action == A.END:
            if self._terminal is None:
                self._terminal = selected.reason_code
            self._finish()
            return
        self._checkpoint(selected.operation_scope or selected.request_scope)
        try:
            self._accept(self.dispatcher.dispatch(selected, self._pending, self._logical_step))
        except Exception as error:
            self._terminal, self._error = 'dispatch_error', type(error).__name__

    def reject_control(self, reason):
        self._terminal, self._error, self._ready, self._waiting = 'policy_error', reason, None, None
        self._history.append(PublicEvent('controller_integrity_failure', {'reason_code': reason}))
        self._finish(opportunity=False)

    def _result(self, status):
        snapshot, task_snapshot = self.store.snapshot(), self.adapter.task_engine.snapshot()
        oracle = self.task.oracle.evaluate(snapshot, task_snapshot, self._answer, self._answer_status)
        if status == 'completed' and not oracle['success']:
            status = 'oracle_failed'
        events = self.ledger.events()
        try:
            verified = self.ledger.verify_replay()
        except (ValueError, KeyError):
            verified = False
        audit = self.adapter.monitor.audit_events()
        return AgentResult(status, self._answer, self._answer_status, self._turns, self._logical_step,
            self._prompts, self._escalations, None if self._waiting is None else self._waiting.message_id,
            tuple(self._history), tuple(self._trace), events, audit, snapshot, self.channel.snapshot(),
            oracle, verified, self.adapter.monitor.verify_audit_chain(audit), self._error)
