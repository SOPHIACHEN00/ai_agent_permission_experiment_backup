"""One query is one reward episode; personal state persists outside it."""
from ..contracts.task import ControlView
from ..contracts.permission import canonical_hash
from .transitions import DecisionBoundary, PublicEpisodeContext, HumanWait, EpisodeEnd, ClosedTransition
from .outcomes import task_metrics, metric_delta


class LearningDriver:
    def __init__(self, session, policy, reward_fn, training=False, *, episode_mode='query'):
        if type(training) is not bool or not callable(reward_fn):
            raise ValueError('explicit training flag and reward function required')
        if episode_mode != 'query':
            raise ValueError('four-action protocol supports explicitly query-local episodes')
        self.session, self.policy, self.reward_fn, self.training = session, policy, reward_fn, training
        self.episode_mode, self.user_id = episode_mode, session.user_id
        self.pending_transition = None
        self.last_transition = None
        self._delivered = set()
        self._finished = False
        self._unresolved = False
        self._unresolved_task_id = None
        self.unresolved_transition = None

    @property
    def active(self):
        return self.session._sessions[self.session.position.task_id]

    def _boundary(self, s, view):
        snap = s.adapter.task_engine.snapshot()
        c = PublicEpisodeContext(
            view.logical_step + max(0, s.max_total_control_steps - s._logical_step) + 1,
            s.max_planner_turns, s._turns, len(s.task.steps), len(snap.committed_effect_ids),
            snap.primary_complete, snap.has_unknown_effect, s._escalations,
            len(s.store.snapshot().get('data_flows', ())), s.limits.max_permission_messages,
            s.limits.max_read_instances + s.limits.max_write_instances,
            control_steps_used=s._logical_step, control_step_limit=s.max_control_steps,
            release_steps_used=s._release_steps, release_step_limit=s.limits.max_release_steps)
        token = canonical_hash((self.user_id, self.session.run_id, view.position.task_id,
                                view.position.decision_index))
        return DecisionBoundary(view, c, token)

    def _end(self, s, result, reward=0., terminated=False, integrity=()):
        m = task_metrics(s)
        return EpisodeEnd(result, reward, terminated, bool(integrity),
                          m['extra_read_instances'] + m['extra_write_instances'],
                          m['active_gate_items_before_cleanup'] or 0, tuple(integrity))

    def advance(self):
        if self._finished:
            raise ValueError('learning sequence already closed')
        if self.session.user_id != self.user_id:
            raise ValueError('foreign user stream')
        s = self.active
        if self._unresolved and self.session.position.task_id != self._unresolved_task_id:
            raise ValueError('unresolved query cannot be followed by another query in the same driver')
        view = s.advance()
        if isinstance(view, ControlView):
            boundary = self._boundary(s, view)
            metrics = task_metrics(s)
            if (metrics['unknown_effect'] or not metrics['authorization_evidence_complete']
                    or metrics['unauthorized_executed_field_instances']):
                self._unresolved = True
                self._unresolved_task_id = self.session.position.task_id
                if self.pending_transition is not None:
                    self.unresolved_transition = self.pending_transition
                    self.pending_transition = None
            elif self.pending_transition is not None:
                if self.pending_transition[3] is not s:
                    raise ValueError('previous query must settle before starting a new one')
                self._close(boundary)
            return boundary
        if view.status == 'awaiting_human':
            return HumanWait(view)
        metrics = task_metrics(s)
        if (metrics['unknown_effect'] or not metrics['authorization_evidence_complete']
                or metrics['unauthorized_executed_field_instances']):
            # Preserve the result for reporting, but never invent an exact
            # exposure reward/terminal training sample for unknown effects.
            self._unresolved = True
            self._unresolved_task_id = self.session.position.task_id
            return self._end(s, view, integrity=('unresolved_execution_evidence',))
        if self.pending_transition is not None:
            self._close(terminate=True)
        reward = (self.last_transition.reward
                  if self.last_transition and self.last_transition.done
                  and self.last_transition.pre_decision.view.position.task_id == s.user_context.position.task_id
                  else 0.)
        return self._end(s, view, reward, terminated=True)

    def step(self, candidate_id):
        boundary = self.advance()
        if not isinstance(boundary, DecisionBoundary) or self.pending_transition is not None:
            raise ValueError('no actionable boundary')
        s = self.active
        s.validate_control(candidate_id)
        if not self._unresolved:
            self.pending_transition = (boundary, candidate_id, task_metrics(s), s)
        s.dispatch_control(candidate_id)
        result = self.advance()
        return self.last_transition if isinstance(result, DecisionBoundary) and not self._unresolved else result

    def _close(self, successor=None, *, terminate=False):
        pre, action, before, s = self.pending_transition
        if successor is None and not terminate:
            raise ValueError('no observed successor')
        if successor is not None and successor.view.position.task_id != pre.view.position.task_id:
            raise ValueError('query boundaries must not bootstrap into another query')
        metrics = task_metrics(s)
        if (metrics['unknown_effect'] or not metrics['authorization_evidence_complete']
                or metrics['unauthorized_executed_field_instances']):
            raise ValueError('unresolved effects cannot enter replay as exact reward')
        reward = self.reward_fn(metric_delta(before, metrics))
        result = s._result(s._terminal or 'running')
        end = self._end(s, result, reward, True) if terminate else None
        transition = ClosedTransition(pre.token, pre, action, reward, successor, terminate, False, end,
                                      task_ended=s._closed,
                                      task_outcome=result.oracle_result if s._closed else None)
        if transition.transition_id in self._delivered:
            raise ValueError('duplicate learning delivery')
        if self.training:
            self.policy.observe(transition)
        self._delivered.add(transition.transition_id)
        self.last_transition = transition
        self.pending_transition = None
        return transition

    def finish_sequence(self):
        if self._unresolved:
            raise ValueError('unresolved execution is recorded, not a terminal learning sample')
        if not self.active._closed:
            raise ValueError('finish only a completed query; waiting is not terminal')
        if self.pending_transition is not None:
            self._close(terminate=True)
        self._finished = True
        return self.last_transition
