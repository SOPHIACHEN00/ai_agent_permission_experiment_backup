"""Check actual flow receipts; never claim business answer quality or RL benefit."""
from dataclasses import dataclass
from typing import Mapping
from personal_assistant.contracts.permission import contract_json_round_trip as copy_json, freeze_value


@dataclass(frozen=True)
class DataflowOracle:
    query_id: int
    expectations: Mapping
    source: Mapping
    extensions: tuple[str, ...]
    omitted_source_data: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, 'expectations', freeze_value(self.expectations))
        object.__setattr__(self, 'source', freeze_value(self.source))

    def evaluate(self, snapshot, task_snapshot, answer, answer_status):
        events = {event['step_id']: event for event in snapshot['events']}
        flows = snapshot.get('data_flows', [])
        checked = {}
        for step_id, spec in self.expectations.items():
            event = events.get(step_id)
            valid = bool(event and all(event.get(k) == spec[k] for k in ('tool', 'operation', 'resource', 'recipient')))
            if valid:
                if spec['direction'] == 'read':
                    values = event['result']
                elif spec['direction'] == 'write':
                    index = event['result'].get('outbox_index')
                    receipt = snapshot['outbox'][index] if type(index) is int and 0 <= index < len(snapshot['outbox']) else {}
                    valid = all(receipt.get(k) == spec[k] for k in ('tool', 'resource')) and receipt.get('step_id') == step_id
                    values = receipt.get('data', {})
                else:
                    values = {}
                    valid = snapshot['records'][spec['tool']][spec['resource']].get('settings') == copy_json(spec['parameters'])
                selected = set(event['fields'])
                actual_fields = set(values) - {'id', 'synthetic'} if spec['direction'] == 'read' else set(values)
                step_flows = [f for f in flows if f.get('step_id') == step_id]
                valid = (valid and selected <= set(spec['values']) and actual_fields == selected
                         and len(step_flows) == len(selected)
                         and {f.get('field') for f in step_flows} == selected
                         and all(all(f.get(k) == spec[k] for k in ('direction', 'tool', 'resource', 'recipient'))
                                 and f.get('value') == spec['values'].get(f.get('field'))
                                 for f in step_flows))
                for field in spec['required_fields']:
                    valid = valid and values.get(field) == spec['values'][field] and any(
                        f.get('step_id') == step_id and f.get('field') == field
                        and f.get('value') == spec['values'][field]
                        and all(f.get(k) == spec[k] for k in ('direction', 'tool', 'resource', 'recipient'))
                        for f in flows)
            checked[step_id] = bool(valid)
        undeclared = sum(
            f.get('step_id') not in self.expectations or
            f.get('field') not in self.expectations[f['step_id']]['values']
            for f in flows)
        receipts_match = len(snapshot['outbox']) == sum(e['operation'] == 'update' for e in snapshot['events'])
        complete = bool(task_snapshot.primary_complete and not task_snapshot.has_unknown_effect
                        and all(checked.values()) and not undeclared
                        and receipts_match and set(events) <= set(self.expectations)
                        and answer_status == 'completed' and answer)
        return {'success': complete, 'dataflow_complete': complete,
                'evaluation_kind': 'wu_minimal_dataflow_completion', 'query_id': self.query_id,
                'step_checks': checked, 'business_answer_quality_evaluated': False,
                'task_facts': {'primary_complete': task_snapshot.primary_complete,
                               'dataflow_complete': complete, 'has_unknown_effect': task_snapshot.has_unknown_effect},
                'privacy_proxy': {'read_field_instances': sum(f['direction'] == 'read' for f in flows),
                                  'write_field_instances': sum(f['direction'] == 'write' for f in flows),
                                  'source_negative_field_instances': sum(bool(f['source_negative']) for f in flows),
                                  'undeclared_flow_field_instances': undeclared},
                'omitted_source_data': list(self.omitted_source_data), 'extensions': list(self.extensions),
                'evidence_boundary': 'Source-aligned flow fixture only; no business quality, learned policy, or full necessity/lifetime privacy claim.'}
