"""Deterministic scope ontology and structural coverage rules."""

from __future__ import annotations

from enum import Enum

from ..contracts.permission import Scope


SCOPE_ONTOLOGY_VERSION = "scope_ontology_v1"
_RETENTION_ORDER = {"none": 0, "transient": 1, "episode": 2, "session": 3}
_CATEGORICAL_RETENTIONS = frozenset({"external"})
_VALID_RETENTIONS = frozenset(_RETENTION_ORDER) | _CATEGORICAL_RETENTIONS


class ScopeRelation(str, Enum):
    EXACT = "exact"
    NARROWER = "narrower"
    BROADER = "broader"
    DISJOINT = "disjoint"


def _resource_covers(grant_resource: str, operation_resource: str) -> bool:
    """Return whether a grant resource structurally covers an operation resource."""
    if "*" in operation_resource:
        return False
    if "*" not in grant_resource:
        return grant_resource == operation_resource
    if not grant_resource.endswith("/*") or grant_resource.count("*") != 1:
        return False
    prefix = grant_resource[:-1]
    return operation_resource.startswith(prefix) and len(operation_resource) > len(prefix)


def _validate_retentions(grant_retention: str, operation_retention: str) -> None:
    if grant_retention not in _VALID_RETENTIONS or operation_retention not in _VALID_RETENTIONS:
        raise ValueError("retention must be one of none, transient, episode, session, external")


def _retention_covers(grant_retention: str, operation_retention: str) -> bool:
    if grant_retention in _CATEGORICAL_RETENTIONS or operation_retention in _CATEGORICAL_RETENTIONS:
        return grant_retention == operation_retention
    return _RETENTION_ORDER[operation_retention] <= _RETENTION_ORDER[grant_retention]


def covers(grant_scope: Scope, operation_scope: Scope) -> bool:
    """Return whether a grant authorizes the complete operation scope."""
    if not isinstance(grant_scope, Scope) or not isinstance(operation_scope, Scope):
        raise ValueError("grant_scope and operation_scope must be Scope values")
    _validate_retentions(grant_scope.retention, operation_scope.retention)
    if any("*" in value for value in (operation_scope.resource,)):
        return False
    if any(
        getattr(grant_scope, field) != getattr(operation_scope, field)
        for field in ("domain", "tool", "operation", "purpose", "recipient")
    ):
        return False
    return (
        _resource_covers(grant_scope.resource, operation_scope.resource)
        and set(grant_scope.data_attributes).issuperset(operation_scope.data_attributes)
        and _retention_covers(grant_scope.retention, operation_scope.retention)
    )


def relation(grant_scope: Scope, operation_scope: Scope) -> ScopeRelation:
    """Describe an operation scope relative to a grant scope without semantic matching."""
    if not isinstance(grant_scope, Scope) or not isinstance(operation_scope, Scope):
        raise ValueError("grant_scope and operation_scope must be Scope values")
    _validate_retentions(grant_scope.retention, operation_scope.retention)
    if grant_scope == operation_scope:
        return ScopeRelation.EXACT
    if "*" in operation_scope.resource:
        return ScopeRelation.DISJOINT
    if covers(grant_scope, operation_scope):
        return ScopeRelation.NARROWER
    if covers(operation_scope, grant_scope):
        return ScopeRelation.BROADER
    return ScopeRelation.DISJOINT
