"""Shared task plumbing; authority decisions live in UserTaskSession."""
from ..contracts.task import AgentResult

class AgentRuntimeBase:
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
        # Bindings duplicate public resource/recipient handles, never values or
        # argument keys from step.arguments. They are not consent/observations.
        return tuple({'tool': s.tool, 'operation': s.operation, 'resource': s.resource,
                      'requested_fields': list(s.data_attributes), 'recipient': s.recipient,
                      **step.io_contract.public_contract(s),
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

    def run(self):
        """Policy loop using the same explicit decision/dispatch boundary."""
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
