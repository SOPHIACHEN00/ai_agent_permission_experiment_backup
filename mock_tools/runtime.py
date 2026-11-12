"""Prepare only projected reads/writes; the existing monitor owns commit authority."""
from __future__ import annotations

from collections.abc import Mapping
from personal_assistant.contracts.permission import contract_json_round_trip as copy_json
from personal_assistant.contracts.tool_call import CompiledCall
from .contracts import ReadWriteContract, SIMULATION
from .sources import source_queries


class ReadWriteRuntime:
    """Explicit backend for the new Agent; only Wu labels and minimal I/O."""

    def __init__(self):
        self.tool_names = tuple(sorted({'mira'} | {
            row[key] for row in source_queries().values() for key in ('tool1', 'tool2') if row[key]
        }))

    def validate_call(self, call: CompiledCall) -> None:
        if not isinstance(call, CompiledCall) or not isinstance(call.io_contract, ReadWriteContract):
            raise ValueError('minimal calls require a typed read/write contract')
        if call.scope.tool not in self.tool_names:
            raise ValueError('unknown Wu tool label')
        call.io_contract.validate(call.scope, call.arguments)

    def prepare_io_effect(self, call, records, outbox, reads, read_values, private_inputs, models):
        return prepare_io_effect(call, records, outbox, reads, read_values, private_inputs, models)


def prepare_io_effect(call, records, outbox, reads, read_values, private_inputs, models):
    scope, io = call.scope, call.io_contract
    if not isinstance(io, ReadWriteContract):
        raise ValueError('minimal executor requires a ReadWriteContract')
    io.validate(scope, call.arguments)
    model = models.get(call.step_id)
    if (not isinstance(model, Mapping) or scope not in model['operation_scopes']
            or model['io_contract'] != io):
        raise ValueError('call is not bound to the trusted minimal task manifest')
    inputs, outputs = io.selected(scope)
    values, flows = {}, []
    rows = records[scope.tool]
    if scope.resource not in rows:
        raise ValueError('minimal record does not exist')
    result = {'id': scope.resource, 'synthetic': True}

    def log(field, value, kind):
        flows.append({'step_id': call.step_id, 'tool': scope.tool, 'resource': scope.resource,
                      'direction': model['direction'], 'field': field, 'recipient': scope.recipient,
                      'value': value, 'source_kind': kind,
                      'source_negative': field in model['source_negative_fields']})

    for field in outputs:
        if field not in rows[scope.resource]:
            raise ValueError('requested synthetic field does not exist')
        value = copy_json(rows[scope.resource][field])
        key = (scope.tool, scope.resource, field)
        reads.add(key)
        read_values[key] = value
        result[field] = value
        log(field, value, 'wu_source_data')
    for field, ref in inputs.items():
        descriptor = private_inputs.get(ref)
        if not isinstance(descriptor, Mapping):
            raise ValueError('unknown private data handle')
        if 'source' in descriptor:
            source = tuple(descriptor['source'])
            if source not in reads or source not in read_values:
                raise ValueError('forwarded data must first be observed under authorization')
            source_row = records.get(source[0], {}).get(source[1], {})
            if source[2] not in source_row or source_row[source[2]] != read_values[source]:
                raise ValueError('forwarded data changed since its authorized read')
            value = copy_json(read_values[source])
        elif 'value' in descriptor:
            value = copy_json(descriptor['value'])
        else:
            raise ValueError('private handle has no value or authorized observation')
        values[field] = value
        log(field, value, descriptor['source_kind'])
    if model['direction'] == 'write':
        # One uniform recipient receipt, not a simulated email/payment/booking.
        receipt = {'step_id': call.step_id, 'tool': scope.tool, 'resource': scope.resource,
                   'simulation': SIMULATION, 'data': values}
        outbox.append(receipt)
        rows[scope.resource]['received'] = values
        result.update(status='recorded_locally', outbox_index=len(outbox) - 1)
    elif model['direction'] == 'setup':
        rows[scope.resource]['settings'] = copy_json(io.parameters)
        result.update(status='setup_recorded_locally')
    return result, flows
