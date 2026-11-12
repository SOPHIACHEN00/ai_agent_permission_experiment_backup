"""Approved execution assumptions applied outside the read-only mock package."""
from __future__ import annotations

from dataclasses import dataclass, replace

from ..contracts.permission import freeze_value
from .task_semantics import CONTACT_FIELDS


H55_1 = ('H55-1: common ten profile fields plus either Email address or Phone number '
         'complete this mock task; original Wu query and source labels are unchanged.')


@dataclass(frozen=True)
class AlternativeDataflowOracle:
    """Use the existing receipt checker with independently fixed alternatives.

    This changes the approved execution requirement, not the raw questionnaire
    labels. All ordinary value/receipt/unknown-effect checks remain delegated to
    the original DataflowOracle.
    """

    base: object
    expectations: object

    def __post_init__(self):
        object.__setattr__(self, 'expectations', freeze_value(self.expectations))

    @property
    def query_id(self): return self.base.query_id

    @property
    def source(self): return self.base.source

    @property
    def extensions(self): return self.base.extensions + (H55_1,)

    @property
    def omitted_source_data(self): return self.base.omitted_source_data

    def evaluate(self, snapshot, task_snapshot, answer, answer_status):
        changed = [(sid, spec) for sid, spec in self.expectations.items()
                   if spec.get('alternative_required_fields')]
        if len(changed) != 1:
            raise ValueError('H55-1 requires exactly one alternative step')
        step_id, spec = changed[0]
        results = []
        for needed in spec['alternative_required_fields']:
            expectations = {sid: dict(item) for sid, item in self.expectations.items()}
            expectations[step_id]['required_fields'] = needed
            oracle = replace(self.base, expectations=expectations, extensions=self.extensions)
            results.append(oracle.evaluate(snapshot, task_snapshot, answer, answer_status))
        # Preserve valid per-step receipts even when the whole task is still
        # incomplete (for example the final answer has not been submitted).
        result = max(results, key=lambda item: (item['success'], sum(item['step_checks'].values())))
        result['evaluation_kind'] = 'wu_minimal_dataflow_completion_h55_1'
        result['execution_assumptions'] = ['H55-1']
        return result


def apply_execution_assumptions(task, query_id):
    """Adapt Q55 scopes/model/oracle without editing mock tools or source rows."""
    if query_id != 55:
        return task
    steps = []
    models = {sid: dict(model) for sid, model in task.tool_models.items()}
    expectations = {sid: dict(spec) for sid, spec in task.oracle.expectations.items()}
    changed = 0
    for step in task.steps:
        spec = expectations[step.step_id]
        required = frozenset(spec['required_fields'])
        if spec['direction'] != 'write' or not CONTACT_FIELDS <= required:
            steps.append(step)
            continue
        common = required - CONTACT_FIELDS
        if len(common) != 10 or spec['tool'] != 'Tinder':
            raise ValueError('Q55 source changed; H55-1 requires revalidation')
        groups = (tuple(sorted(common | {'Email address'})),
                  tuple(sorted(common | {'Phone number'})))
        scopes = tuple(replace(step.operation_scopes[0], data_attributes=fields) for fields in groups)
        scopes += tuple(scope for scope in step.operation_scopes if scope not in scopes)
        # Keep the broad original scope last, so existing scripted proposals
        # can be safely projected to either approved alternative.
        steps.append(replace(step, operation_scopes=scopes, request_scopes=scopes))
        models[step.step_id]['operation_scopes'] = scopes
        expectations[step.step_id]['alternative_required_fields'] = groups
        expectations[step.step_id]['execution_assumption'] = 'H55-1'
        changed += 1
    if changed != 1:
        raise ValueError('Q55 no longer has its expected one contact-disclosure step')
    return replace(task, steps=tuple(steps), tool_models=models,
                   oracle=AlternativeDataflowOracle(task.oracle, expectations))
