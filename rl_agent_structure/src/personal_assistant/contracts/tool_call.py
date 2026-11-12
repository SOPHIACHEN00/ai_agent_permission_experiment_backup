"""Task-bound private input references, output fields and public parameters.

References are handles, not values or authorizations. The trusted executor must
resolve them only after the reference monitor has admitted the exact call.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .validation import validate_json_value
from .permission import Scope, contract_json_round_trip, freeze_value


@dataclass(frozen=True)
class ToolIOContract:
    input_refs: Mapping[str, str]
    output_fields: tuple[str, ...]
    parameters: Mapping

    def __post_init__(self) -> None:
        if not isinstance(self.input_refs, Mapping) or any(
            not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
            for k, v in self.input_refs.items()
        ):
            raise ValueError('private inputs require nonempty field names and reference handles')
        if (not isinstance(self.output_fields, tuple)
                or any(not isinstance(f, str) or not f.strip() for f in self.output_fields)
                or len(set(self.output_fields)) != len(self.output_fields)):
            raise ValueError('output fields must be a tuple of unique nonempty names')
        if set(self.input_refs) & set(self.output_fields):
            raise ValueError('a field cannot silently represent both input and output; use separate calls')
        if not isinstance(self.parameters, Mapping):
            raise ValueError('operation parameters must be a declared mapping')
        validate_json_value(self.parameters)
        if set(self.parameters) & (set(self.input_refs) | set(self.output_fields)):
            raise ValueError('protected fields must not be disguised as operation parameters')
        object.__setattr__(self, 'input_refs', freeze_value(self.input_refs))
        object.__setattr__(self, 'parameters', freeze_value(self.parameters))

    def selected(self, scope: Scope) -> tuple[dict[str, str], tuple[str, ...]]:
        fields = set(scope.data_attributes)
        if fields - (set(self.input_refs) | set(self.output_fields)):
            raise ValueError('scope contains a protected field with no declared data-flow direction')
        return ({f: ref for f, ref in self.input_refs.items() if f in fields},
                tuple(f for f in self.output_fields if f in fields))

    def public_contract(self, scope: Scope) -> dict:
        inputs, _ = self.selected(scope)
        bindings = {'record_id': scope.resource,
                    'inputs': {f: {'ref': ref} for f, ref in inputs.items()},
                    'parameters': contract_json_round_trip(self.parameters)}
        def exact_object(properties: dict) -> dict:
            return {'type': 'object', 'properties': properties,
                    'required': list(properties), 'additionalProperties': False}
        schema = exact_object({
            'record_id': {'type': 'string', 'const': scope.resource},
            'inputs': exact_object({f: exact_object({'ref': {'type': 'string', 'const': ref}})
                                    for f, ref in inputs.items()}),
            'parameters': exact_object({k: {'const': v} for k, v in bindings['parameters'].items()}),
        })
        return {'argument_schema': schema, 'argument_bindings': bindings}

    def validate(self, scope: Scope, arguments: Mapping) -> None:
        validate_json_value(arguments)
        expected = self.public_contract(scope)['argument_bindings']
        # The schema is also exposed to the planner, but actual execution repeats
        # validation independently; JSON bool/number distinctions are preserved.
        from jsonschema import Draft202012Validator, ValidationError
        try:
            Draft202012Validator(self.public_contract(scope)['argument_schema']).validate(
                contract_json_round_trip(arguments))
        except ValidationError as error:
            raise ValueError('tool arguments differ from the task-bound I/O contract') from error
        if contract_json_round_trip(arguments) != expected:
            raise ValueError('tool arguments differ from the task-bound I/O contract')


@dataclass(frozen=True)
class CompiledCall:
    step_id: str
    scope: Scope
    arguments: Mapping
    io_contract: ToolIOContract | None = None

    def __post_init__(self):
        if not self.step_id or not isinstance(self.scope, Scope):
            raise ValueError('compiled call needs step ID and Scope')
        validate_json_value(self.arguments)
        if self.io_contract is not None and not isinstance(self.io_contract, ToolIOContract):
            raise ValueError('call I/O contract must be typed')
        object.__setattr__(self, 'arguments', freeze_value(self.arguments))
