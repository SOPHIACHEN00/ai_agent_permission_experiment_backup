"""Compile the Wu survey scenarios into small, explicitly authored flow fixtures.

Original positive/incorrect items define narrow/broad options, NOT a particular
user's permission answers or a proven semantic necessity oracle. No extra tasks.
"""
from __future__ import annotations

from personal_assistant.contracts.permission import Scope
from personal_assistant.contracts.task import TaskDefinition, TaskStepSpec
from .contracts import ReadWriteContract, SIMULATION
from .oracle import DataflowOracle
from .sources import data_items, query_ids, source_queries


def synthetic_value(query_id: int, field: str) -> str:
    return f'SYNTHETIC:q{query_id}:{field}'


def _read_sources(row: dict) -> dict[str, tuple[str, ...]]:
    fields = data_items(row['data_MIRA'])
    if not fields or row['id'] in {63, 64}:
        return {}
    if row['id'] == 59:
        return {'Security Camera': ('Garage video recording',), 'Smart Lock': ('Garage access log',)}
    if row['id'] == 54:
        return {'Cloud Drive': ('Photos',), 'mira': ('Instagram post content',)}
    return {row['tool1']: fields}


def build_wu_task(query_id: int) -> TaskDefinition:
    if type(query_id) is not int or query_id not in range(65):
        raise ValueError('query ID must be an integer from 0 through 64')
    row = source_queries()[query_id]
    outputs = _read_sources(row)
    steps, records, private, models, expectations, observed = [], {}, {}, {}, {}, {}
    extensions = [
        'Synthetic values, step order, source-tool assignments and scope handles are authored, not Wu API specifications.',
        'write means disclosure to a named tool; its operation alias is update, not a real vendor update API.',
        'Original incorrect items are optional broad-scope probes, not user answers; original source rows are unchanged.',
    ]
    omitted = data_items(row['data_MIRA']) if query_id in {63, 64} else ()
    if omitted:
        extensions.append('User-approved setup only: source history fields retained in metadata but not read; no future authority.')
    if query_id == 54:
        extensions.append('User-approved Instagram caption disclosure is separate from the original data_tool2 label.')

    def add(tool, direction, required=(), negatives=(), settings=None):
        negative = tuple(f for f in negatives if f not in required)
        all_fields = tuple(required) + negative
        step_id = f'q{query_id:02d}_{len(steps) + 1:02d}_{direction}'
        resource = f'wu_q{query_id:02d}_{tool}'
        refs = {}
        if direction == 'write':
            for field in all_fields:
                ref = f'wu:q{query_id}:{tool}:{field}'
                descriptor = ({'source': observed[field]} if field in observed
                              else {'value': synthetic_value(query_id, field)})
                descriptor['source_kind'] = ('approved_execution_extension'
                    if query_id == 54 and tool == 'Instagram' and field == 'Instagram post content'
                    else 'wu_source_data')
                private[ref] = descriptor
                refs[field] = ref
        parameters = {'simulation': SIMULATION, **(settings or {})}
        io = ReadWriteContract(refs, all_fields if direction == 'read' else (), parameters)
        operation = {'read': 'read', 'write': 'update', 'setup': 'control'}[direction]
        recipient = tool if direction == 'write' else 'mira'
        base = dict(domain=row['domain'], tool=tool, resource=resource, operation=operation,
                    purpose=f'wu:{query_id}:{direction}', recipient=recipient, retention='session')
        scopes = (Scope(**base, data_attributes=tuple(required)),)
        if negative:
            scopes += (Scope(**base, data_attributes=all_fields),)
        arguments = io.public_contract(scopes[-1])['argument_bindings']
        steps.append(TaskStepSpec(step_id, scopes, scopes, arguments, io_contract=io))
        record = records.setdefault(tool, {}).setdefault(resource, {})
        if direction == 'read':
            record.update({f: synthetic_value(query_id, f) for f in all_fields})
            for field in all_fields:
                observed[field] = (tool, resource, field)
        models[step_id] = {'operation_scopes': scopes, 'io_contract': io, 'direction': direction,
                          'source_negative_fields': negative}
        expectations[step_id] = {'tool': tool, 'operation': operation, 'resource': resource,
                                'direction': direction, 'recipient': recipient,
                                'required_fields': tuple(required), 'negative_fields': negative,
                                'values': {f: synthetic_value(query_id, f) for f in all_fields},
                                'parameters': parameters}

    for index in (1, 2):
        tool = row[f'tool{index}']
        if not tool:
            continue
        if query_id in {63, 64}:
            # Preserve the previously approved setup rule, not a sensor/timer.
            settings = ({'start_hour': 20, 'end_hour': 6, 'repeat': 'nightly'} if query_id == 63
                        else {'no_motion_seconds': 60, 'target': 'all_doors'})
            add(tool, 'setup', settings=settings)
            continue
        incoming = data_items(row[f'data_tool{index}'])
        if query_id == 54 and tool == 'Instagram':
            incoming += ('Instagram post content',)
        if incoming:
            add(tool, 'write', incoming, data_items(row[f'data_tool{index}_incorrect']))
        if tool in outputs:
            # MIRA source assignment is an implementation assumption. For Q59,
            # unsupported negative-source attribution is limited to tool1.
            negatives = data_items(row['data_MIRA_incorrect']) if index == 1 else ()
            add(tool, 'read', outputs[tool], negatives)
        if query_id == 54 and tool == 'Cloud Drive':
            add('mira', 'read', outputs['mira'])
    oracle = DataflowOracle(query_id, expectations, row, tuple(extensions), omitted)
    return TaskDefinition(f'wu_minimal_q{query_id:02d}', row['query'], tuple(steps), records, oracle,
                          private_inputs=private, tool_models=models)
