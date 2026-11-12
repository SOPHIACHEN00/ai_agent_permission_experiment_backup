"""Transparent tracing for either native exploration mode; never chooses actions."""
from __future__ import annotations

import random

from .control_trace import _score_candidates
from .records import RunLog


class ExplorationLog(RunLog):
    def __init__(self, config, output=None):
        super().__init__(config, output)
        self.action_scores = []

    def report(self, summary=None):
        result = super().report(summary)
        result['action_scores'] = self.action_scores
        return result


class ExplorationTrace:
    def __init__(self, policy, log):
        self.base_policy, self.log = policy, log

    def __getattr__(self, name):
        return getattr(self.base_policy, name)

    def observe(self, transition):
        return self.base_policy.observe(transition)

    def select(self, boundary, *, epsilon=0.):
        from personal_assistant.learning.user_features import state_feature_names
        base = self.base_policy
        encoded = base.encoder.encode(boundary)
        encoded.validate()
        if encoded.candidate_ids != tuple(c.candidate_id for c in boundary.view.candidates):
            raise ValueError('candidate identity mismatch')
        mask = tuple(encoded.mask.tolist())
        if mask != tuple(c.valid for c in boundary.view.candidates):
            raise ValueError('trace disagrees with actual authorization mask')
        scores = _score_candidates(base, encoded)
        shadow = random.Random()
        shadow.setstate(base.learner._rng.getstate())
        explored = base.training and shadow.random() < epsilon
        selected = base.select(boundary, epsilon=epsilon)
        index = encoded.candidate_ids.index(selected)
        if not mask[index]:
            raise ValueError('native DDQN selected an invalid action')
        candidates = [{'candidate_id':c.candidate_id, 'action':c.action.value,
                       'valid':c.valid, 'q':q,
                       'request_field_count':0 if c.request_scope is None else len(c.request_scope.data_attributes),
                       'operation_field_count':0 if c.operation_scope is None else len(c.operation_scope.data_attributes),
                       'release_key_count':len(c.release_keys)}
                      for c, q in zip(boundary.view.candidates, scores)]
        best = max(q for q, valid in zip(scores, mask) if valid)
        row = {'token':boundary.token, 'task_id':boundary.view.position.task_id,
               'global_decision':boundary.view.logical_step, 'phase':boundary.view.phase,
               'epsilon':epsilon, 'explored':explored,
               'exploration_mode':base.enhancements.exploration,
               'selected_candidate_id':selected, 'selected_action':candidates[index]['action'],
               'selected_q':scores[index], 'selected_is_greedy':scores[index] == best,
               'execute_legal':any(c['valid'] and c['action']=='EXECUTE' for c in candidates),
               'candidates':candidates,
               'runtime_budgets':{k:getattr(boundary.context,k) for k in
                    ('control_steps_used','control_step_limit','release_steps_used','release_step_limit')},
               'state_features':dict(zip(state_feature_names(base.budget_representation), encoded.state.tolist()))}
        self.log.action_scores.append(row)
        self.log.event('action_scores', row)
        return selected


def summarize_task(row, traces, *, index=None):
    selected = [t for t in traces if t['task_id'] == row['task_id']]
    executions = [t for t in selected if t['selected_action'] == 'EXECUTE']
    committed = any(e.get('tool_effect_status') == 'committed' for e in row['execution_checks'])
    m = row['metrics']
    timely = bool(m['task_success'] and committed and executions and all(
        t['runtime_budgets']['release_steps_used'] < t['runtime_budgets']['release_step_limit']
        for t in executions))
    result = {'query_id':row['query_id'], 'return':row['return'],
              'task_success':m['task_success'], 'control_steps':len(selected), 'timely':timely,
              'ER':m['extra_read_instances'], 'ED':m['extra_write_instances'],
              'M':m['extra_permission_messages'], 'K':m['idle_gate_key_checkpoints'],
              'PB':m['permission_messages'],
              'terminal_G':m['active_gate_items_before_cleanup'],
              'legal_execute_opportunities':sum(t['execute_legal'] for t in selected),
              'executed_before_release_limit':sum(
                  t['runtime_budgets']['release_steps_used'] < t['runtime_budgets']['release_step_limit']
                  for t in executions),
              'controller_limit':row['status']=='controller_limit'}
    if index is not None:
        result['index'] = index
    return result
