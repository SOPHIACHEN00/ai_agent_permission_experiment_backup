"""Authority-safe wrapper: public policy frame is separate from auditor artifacts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .adapter import AdapterFault, PublicAnswer, SqstnAdapter
from .common import plain
from .fixtures import Case
from pa_rl.environment import PermissionEnvironment
from pa_rl.execution import ReferenceMonitor
from pa_rl.policy_interface import EnvironmentObservation
from pa_rl.public_events import verify_public_event_chain


@dataclass(frozen=True)
class PolicyFrame:
    observation: EnvironmentObservation
    answers: tuple[PublicAnswer, ...]

    def as_mapping(self) -> dict:
        return {'observation': plain(self.observation.as_mapping()),
                'permission_answers': plain(self.answers)}


@dataclass(frozen=True)
class StepResult:
    frame: PolicyFrame
    reward: int
    done: bool
    terminated: bool
    truncated: bool


class Episode:
    def __init__(self, case: Case, *, cache: dict | None = None, mode: str = 'fixture',
                 live_call=None, live_config: Mapping | None = None) -> None:
        if not isinstance(case, Case):
            raise TypeError('Episode requires a synthetic Case')
        self._case = case
        self._adapter = SqstnAdapter(case.replies, cache=cache, mode=mode,
                                     live_call=live_call, live_config=live_config)
        self._environment = PermissionEnvironment(case.manifest, adapter_factory=lambda _: self._adapter)
        self._ready = False

    def reset(self, seed: int) -> PolicyFrame:
        observation, self._info = self._environment.reset(seed=seed)
        self._frame = PolicyFrame(observation, ())
        self._done = False
        self._ready = True
        self._reward = 0
        self._invalid_actions = 0
        self._adapter_faults = 0
        self._fault = None
        self._actions: list[str] = []
        return self._frame

    def step(self, index: int) -> StepResult:
        if not self._ready or self._done:
            raise AdapterFault('episode_not_live')
        observation = self._frame.observation
        if type(index) is not int or not 0 <= index < len(observation.action_mask) or not observation.action_mask[index]:
            self._invalid_actions += 1
            self._done, self._fault = True, 'invalid_action_before_dispatch'
            raise AdapterFault(self._fault)
        self._actions.append(observation.candidate_catalog[index]['action'])
        next_observation, reward, terminated, truncated, info = self._environment.step(index)
        self._info = info
        self._done, self._reward = terminated or truncated, reward
        reason = info['public']['terminal_reason']
        if reason in ('adapter_protocol_failure', 'environment_invariant_failure',
                      'finalization_semantic_change', 'masked_action'):
            self._adapter_faults += int(reason == 'adapter_protocol_failure')
            self._fault = reason
            raise AdapterFault(reason)
        public_count = next_observation.interaction_history['counts']['permission_choice']
        if public_count != len(self._adapter.public_answers):
            self._done, self._fault = True, 'uncommitted_public_answer'
            raise AdapterFault(self._fault)
        self._frame = PolicyFrame(next_observation, self._adapter.public_answers)
        audit = info['audit']
        verify_public_event_chain(audit['public_records'], expected_head=info['public']['public_event_head_hash'])
        if not ReferenceMonitor.verify_audit_chain(audit['execution_audits']):
            self._done, self._fault = True, 'execution_audit_chain_failure'
            raise AdapterFault(self._fault)
        if self.summary()['unauthorized_effects']:
            self._done, self._fault = True, 'unauthorized_effect'
            raise AdapterFault(self._fault)
        return StepResult(self._frame, reward, self._done, terminated, truncated)

    def summary(self) -> dict:
        if not self._ready:
            raise AdapterFault('episode_not_reset')
        audit = self._info['audit']
        committed = [event.payload for event in audit['execution_audits'] if event.payload['disposition'] == 'committed']
        required = {'explicit_authorization', 'active_authorization', 'unexpired_authorization',
                    'authorization_policy', 'scope_coverage', 'cas_reservation', 'candidate_binding',
                    'authoritative_task_step', 'execute_action', 'environment_version', 'policy_version'}
        invalid = sum(not required.issubset(row['checks']) or not all(row['checks'].values()) for row in committed)
        effects = tuple(audit['tool_committed_effect_ids'])
        proof_ids = tuple(row['tool_effect_id'] for row in committed)
        invalid += int(set(effects) != set(proof_ids) or len(effects) != len(proof_ids))
        return {'scenario_id': self._case.manifest.scenario_id, 'done': self._done,
                'task_success': self._reward == 1 and self._fault is None,
                'reward': self._reward, 'steps': len(self._actions),
                'requests': len(self._adapter.public_answers), 'committed_effects': len(effects),
                'fallback': bool(self._actions and self._actions[-1] in ('DENY_WITH_REASON', 'ESCALATE')),
                'invalid_actions': self._invalid_actions, 'unauthorized_effects': invalid,
                'adapter_faults': self._adapter_faults, 'fault': self._fault,
                'terminal_reason': self._info['public']['terminal_reason'],
                'truncation_reason': self._info['public']['truncation_reason']}

    def private_artifacts(self) -> dict:
        return {**self._adapter.private_artifacts(), 'environment_audit': plain(self._info['audit']),
                'actions': list(self._actions)}
