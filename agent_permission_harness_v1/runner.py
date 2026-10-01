"""Resumable single task-Agent: planner turns and permission steps are distinct."""
from __future__ import annotations

from pa_rl.authorization import AuthorizationService
from pa_rl.contracts import ControllerAction as A, PublicEvent, contract_json_round_trip
from .candidates import build_candidates, grants_from_ledger
from .compiler import compile_intent
from .contracts import AgentResult, ControlView
from .human_channel import LocalHumanChannel
from .ledger_dispatch import LedgerDispatcher
from .monitor_adapter import ExecutionAdapter
from .policy import LeastScopeRulePolicy
from .tools import LocalToolStore


class AgentSession:
    """Only public results/manifest affordances reach the injected task planner.

    A waiting session is kept in memory; run() resumes it without re-sending or
    repeating any completed tool effect. This is not a durable process checkpoint.
    """
    def __init__(self, task, planner, policy=None, channel=None, *, max_planner_turns=8, max_control_steps=30):
        if type(max_planner_turns) is not int or max_planner_turns < 1:
            raise ValueError('planner turn limit must be positive')
        if type(max_control_steps) is not int or max_control_steps < 1:
            raise ValueError('controller step limit must be positive')
        self.task, self.planner = task, planner
        self.policy = policy if policy is not None else LeastScopeRulePolicy()
        self.channel = channel if channel is not None else LocalHumanChannel()
        self.max_planner_turns, self.max_control_steps = max_planner_turns, max_control_steps
        self.ledger = AuthorizationService(task.scenario_id, max_control_steps + 2)
        self.store = LocalToolStore(task.records)
        self.adapter = ExecutionAdapter(task, self.store, self.ledger)
        self.dispatcher = LedgerDispatcher(task, self.ledger, self.adapter, self.channel)
        self._history, self._trace = [], []
        self._pending, self._waiting = None, None
        self._turns, self._logical_step, self._prompts, self._escalations = 0, 0, 0, 0
        self._terminal, self._answer, self._answer_status, self._error = None, None, None, None
        self._ready = None

    def _current_step(self):
        next_id = self.adapter.task_engine.snapshot().next_required_step_id
        return next((s for s in self.task.steps if s.step_id == next_id), None)

    def _observed_ids(self, tool):
        ids = set()
        for event in self._history:
            if event.event_type != 'tool_result' or event.payload['tool'] != tool:
                continue
            result = event.payload['result']
            if isinstance(result.get('id'), str):
                ids.add(result['id'])
            ids.update(row['id'] for row in result.get('matches', ()) if isinstance(row.get('id'), str))
        return frozenset(ids)

    def _available_calls(self, step):
        if step is None:
            return ()
        # Expected payload VALUES and hidden business conditions are not given
        # to the planner; only tool interfaces and current declared projections.
        return tuple({'tool': s.tool, 'operation': s.operation, 'resource': s.resource,
                      'requested_fields': list(s.data_attributes), 'recipient': s.recipient,
                      'argument_keys': list(step.arguments),
                      'require_observed_record': step.require_observed_record}
                     for s in step.operation_scopes)

    def _accept(self, result):
        self._history.extend(result.events)
        self._waiting = result.pending_human
        if result.kind in {'executed', 'replan'}:
            self._pending = None
        elif result.kind == 'stop':
            self._terminal = 'human_stopped'
        elif result.kind == 'fault':
            self._terminal = 'execution_fault'

    def advance(self):
        """Advance planner/replies, never a controller action; polling is idempotent."""
        if self._terminal is not None:
            return self._result(self._terminal)
        if self._ready is not None:
            return self._ready
        while self._terminal is None:
            if self._waiting is not None:
                try:
                    result = self.dispatcher.resolve(self._waiting, self._logical_step)
                except Exception as error:
                    self._terminal, self._error = 'human_error', type(error).__name__
                    break
                self._accept(result)
                if result.kind == 'waiting':
                    return self._result('awaiting_human')
                if self._terminal is not None:
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
                    # No hidden automatic retry of a paid or failed planner call.
                    self._terminal, self._error = 'planner_error', type(error).__name__
                    break
                if getattr(decision, 'kind', None) == 'finish':
                    self._answer, self._answer_status = decision.answer, decision.answer_status
                    self._terminal = 'completed' if decision.answer_status == 'completed' else 'incomplete'
                    break
                try:
                    if step is None:
                        raise ValueError('all declared task steps are finished')
                    self._pending = compile_intent(decision, step, self._observed_ids(decision.tool))
                except (ValueError, TypeError, AttributeError):
                    self._history.append(PublicEvent('intent_rejected', {'reason_code': 'invalid_task_intent'}))
                    continue
            if self._logical_step >= self.max_control_steps:
                self._terminal = 'controller_limit'
                break
            step = self._current_step()
            candidates = build_candidates(self._pending, step, self.ledger, self._logical_step)
            self._ready = ControlView(self._pending, grants_from_ledger(self.ledger), candidates,
                                      tuple(self._history), self._logical_step, self._prompts)
            return self._ready
        return self._result(self._terminal)

    def validate_control(self, selected_id):
        """Recheck factual authority before accepting a selected candidate ID."""
        if self._ready is None or self._terminal is not None or self._waiting is not None:
            raise ValueError('session is not at a controller decision')
        candidates = build_candidates(self._pending, self._current_step(), self.ledger, self._logical_step)
        fresh = ControlView(self._pending, grants_from_ledger(self.ledger), candidates,
                            tuple(self._history), self._logical_step, self._prompts)
        if fresh != self._ready:
            raise ValueError('authority changed since the controller observation')
        selected = next((c for c in candidates if c.candidate_id == selected_id and c.valid), None)
        if selected is None:
            raise ValueError('policy selected unknown or masked candidate')
        return selected

    def dispatch_control(self, selected_id, *, budget_stop=False):
        """One accepted decision, at most one dispatch. Budget stops have no effects."""
        if type(budget_stop) is not bool:
            raise ValueError('budget_stop must be boolean')
        selected = self.validate_control(selected_id)
        view, self._ready = self._ready, None
        self._trace.append({'logical_step': self._logical_step, 'step_id': self._pending.step_id,
            'selected': contract_json_round_trip(selected), 'intent': contract_json_round_trip(self._pending),
            'candidate_ids': [c.candidate_id for c in view.candidates],
            'valid_mask': [c.valid for c in view.candidates], 'dispatched': not budget_stop})
        step = self._logical_step
        self._logical_step += 1
        if budget_stop:
            self._terminal = 'budget_exhausted'
            return
        if selected.action in {A.REQUEST_AUTHORIZATION, A.REQUEST_REFRESH}:
            self._prompts += 1
        if selected.action == A.ESCALATE:
            self._escalations += 1
        try:
            outcome = self.dispatcher.dispatch(selected, self._pending, step)
        except Exception as error:
            self._terminal, self._error = 'dispatch_error', type(error).__name__
            return
        self._accept(outcome)

    def reject_control(self, reason):
        """An invalid selection ends this episode without dispatch or a fake action."""
        self._terminal, self._error, self._ready = 'policy_error', reason, None
        self._history.append(PublicEvent('controller_integrity_failure', {'reason_code': reason}))

    def run(self):
        """Legacy policy loop using exactly the same decision/dispatch boundary."""
        while True:
            view = self.advance()
            if isinstance(view, AgentResult):
                return view
            try:
                selected_id = self.policy.choose(view)
                self.validate_control(selected_id)
            except Exception as error:
                self.reject_control(type(error).__name__)
                return self._result(self._terminal)
            self.dispatch_control(selected_id)

    def _result(self, status):
        snapshot, task_snapshot = self.store.snapshot(), self.adapter.task_engine.snapshot()
        if self.task.oracle is None:
            oracle = {'success': bool(task_snapshot.primary_complete and not task_snapshot.has_unknown_effect
                       and self._answer_status == 'completed'), 'kind': 'structural_completion_only'}
        else:
            oracle = self.task.oracle.evaluate(snapshot, task_snapshot, self._answer, self._answer_status)
        if status == 'completed' and not oracle['success']:
            status = self._terminal = 'oracle_failed'
        events = self.ledger.events()
        try:
            replay = AuthorizationService.replay(self.task.scenario_id, events)
            verified = replay.records() == self.ledger.records()
        except ValueError:
            verified = False
        audit = self.adapter.monitor.audit_events()
        return AgentResult(status, self._answer, self._answer_status, self._turns, self._logical_step,
            self._prompts, self._escalations, None if self._waiting is None else self._waiting.message_id,
            tuple(self._history), tuple(self._trace), events, audit, snapshot, self.channel.snapshot(),
            oracle, verified, self.adapter.monitor.verify_audit_chain(audit), self._error)
