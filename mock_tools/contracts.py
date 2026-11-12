"""Minimal read/write semantics using the independent Agent's exact I/O schema."""
from personal_assistant.contracts.permission import Scope
from personal_assistant.contracts.tool_call import ToolIOContract

SIMULATION = 'wu_minimal_read_write_v1'


class ReadWriteContract(ToolIOContract):
    """Typed opt-in; legacy business mocks do not enter the minimal executor."""

    def validate(self, scope: Scope, arguments) -> None:
        super().validate(scope, arguments)
        if self.parameters.get('simulation') != SIMULATION:
            raise ValueError('minimal calls require their declared simulation version')
        inputs, outputs = self.selected(scope)
        if scope.operation == 'read':
            valid = bool(outputs) and not inputs and scope.recipient == 'mira'
        elif scope.operation == 'update':
            # Keep the existing operation vocabulary; update is just WRITE here.
            valid = bool(inputs) and not outputs and scope.recipient == scope.tool
        elif scope.operation == 'control':
            valid = not inputs and not outputs and not scope.data_attributes
        else:
            valid = False
        if not valid:
            raise ValueError('minimal operation does not match its data-flow direction')
