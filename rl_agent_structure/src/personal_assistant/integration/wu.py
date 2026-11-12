"""Bind original questionnaire metadata to the trusted minimal-tool manifest."""
from dataclasses import dataclass
from functools import lru_cache
from ..contracts.persistence import PermissionKey, SetupPermissionKey
from ..contracts.permission import canonical_hash
from ..contracts.task import TaskDefinition


@dataclass(frozen=True)
class WuBinding:
    query_id: int
    task: TaskDefinition
    questionnaire_keys: tuple
    permission_keys: tuple
    extensions: tuple

    def keys_for_scope(self, scope, user_id, task_id):
        step = next((s for s in self.task.steps if scope in s.operation_scopes), None)
        if step is None:
            raise ValueError('scope is not in trusted Wu manifest')
        if scope.operation == 'control':
            return (SetupPermissionKey(user_id, task_id, self.query_id, scope.tool,
                                       canonical_hash(step.arguments)),)
        direction = 'read' if scope.operation == 'read' else 'write'
        return tuple(PermissionKey(user_id, scope.domain, scope.tool, scope.recipient, f, direction)
                     for f in scope.data_attributes)

    def keys_for(self, user_id, task_id):
        return tuple(dict.fromkeys(k for s in self.task.steps for scope in s.operation_scopes
                                   for k in self.keys_for_scope(scope, user_id, task_id)))

    def questionnaire_key(self, key):
        if not isinstance(key, PermissionKey):
            return None
        candidate = (self.query_id, key.recipient, key.data_item)
        return candidate if candidate in self.questionnaire_keys else None


@lru_cache(maxsize=65)
def load_wu_binding(query_id: int) -> WuBinding:
    from mock_tools.tasks import build_wu_task
    from mock_tools.sources import source_queries, data_items
    from .execution_assumptions import apply_execution_assumptions
    task = apply_execution_assumptions(build_wu_task(query_id), query_id)
    row = source_queries()[query_id]
    questionnaire = []
    for suffix, recipient in (('MIRA', 'mira'), ('tool1', row['tool1']), ('tool2', row['tool2'])):
        if recipient:
            for field in data_items(row['data_' + suffix]) + data_items(row['data_' + suffix + '_incorrect']):
                questionnaire.append((query_id, recipient, field))
    provisional = WuBinding(query_id, task, tuple(questionnaire), (), ())
    keys = provisional.keys_for('__binding__', task.scenario_id)
    extensions = tuple(k for k in keys if provisional.questionnaire_key(k) is None)
    return WuBinding(query_id, task, tuple(questionnaire), keys, extensions)


@lru_cache(maxsize=1)
def catalog_limits():
    keys = set()
    max_scopes = 0
    for q in range(65):
        b = load_wu_binding(q)
        keys.update(b.permission_keys)
        max_scopes = max(max_scopes, *(len(s.operation_scopes) for s in b.task.steps))
    # Task-bound setup keys from completed tasks are never active candidates.
    return len(keys), max_scopes, max(64, len(keys) + 3 * max_scopes + 2)
