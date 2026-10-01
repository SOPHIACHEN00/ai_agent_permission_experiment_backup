"""Strictly validated public policy-interface records for Task 3A."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from .config import DEFAULT_CONFIG
from .contracts import ActionCandidate, AuthorizationStatus, ControllerAction, GrantType, Scope, canonical_hash, freeze_value
from .public_events import PublicEventChainError, PublicEventRecord, verify_public_event_chain
from .scope_matching import ScopeRelation

_HASH16 = re.compile(r"[0-9a-f]{16}\Z"); _HASH64 = re.compile(r"[0-9a-f]{64}\Z"); _AUTH = re.compile(r"authorization_[0-9a-f]{20}\Z")
_TASK_KEYS = ("phase", "next_required_step_id", "next_required_scope_identity", "remaining_step_count", "primary_complete", "has_unknown_effect", "last_public_execution_result_code")
_AUTH_KEYS = ("status", "grant_type", "remaining_uses", "expiry_bucket", "expiry_step", "scope_relation", "last_public_authority_event_id", "reask_relation")
_REASONS = frozenset({"not_needed", "user_declined", "safe_impossibility"})
_TARGETS = frozenset({"human_owner", "security_owner"})
_PHASES = frozenset({"open", "finished", "unknown"})

def _scope_identity(scope: Scope) -> str: return "scope_" + canonical_hash(scope)[:16]
def _task_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip(): raise ValueError("task_step_id must be non-empty text")
    return value.strip()
def _auth_id(value: Any) -> str:
    if not isinstance(value, str) or _AUTH.fullmatch(value) is None: raise ValueError("authorization ID syntax is invalid")
    return value
def _json(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)): return value
    if isinstance(value, int) and not isinstance(value, bool): return value
    if isinstance(value, float): canonical_hash(value); return value
    if isinstance(value, Mapping):
        if any(not isinstance(k, str) for k in value): raise ValueError("public mapping keys must be text")
        return {k: _json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return tuple(_json(v) for v in value)
    raise ValueError("public values must be canonical JSON only")
def _pos(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1: raise ValueError(f"{name} must be positive integer")
    return value

def _task_view(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_TASK_KEYS): raise ValueError("task_view has an invalid schema")
    phase = value["phase"]
    if phase not in _PHASES: raise ValueError("invalid public task phase")
    for key in ("primary_complete", "has_unknown_effect"):
        if not isinstance(value[key], bool): raise ValueError("task flags must be bool")
    if isinstance(value["remaining_step_count"], bool) or not isinstance(value["remaining_step_count"], int) or value["remaining_step_count"] < 0: raise ValueError("invalid remaining step count")
    for key in ("next_required_step_id", "next_required_scope_identity", "last_public_execution_result_code"):
        if value[key] is not None and (not isinstance(value[key], str) or not value[key].strip()): raise ValueError("invalid public task field")
    if value["next_required_scope_identity"] is not None and not re.fullmatch(r"scope_[0-9a-f]{16}", value["next_required_scope_identity"]): raise ValueError("invalid scope identity")
    return freeze_value(dict(value))

def _summary(value: Mapping[str, Any], logical_step: int) -> Mapping[str, Any]:
    _pos(logical_step, "logical_step")
    if not isinstance(value, Mapping) or set(value) != set(_AUTH_KEYS): raise ValueError("authorization summary has invalid schema")
    status, grant, relation = value["status"], value["grant_type"], value["scope_relation"]
    if status is not None and status not in {item.value for item in AuthorizationStatus}: raise ValueError("invalid authorization status")
    if grant is not None and grant not in {item.value for item in GrantType}: raise ValueError("invalid grant type")
    if relation is not None and relation not in {item.value for item in ScopeRelation}: raise ValueError("invalid scope relation")
    uses, expiry = value["remaining_uses"], value["expiry_step"]
    if uses is not None and (isinstance(uses, bool) or not isinstance(uses, int) or uses < 0): raise ValueError("invalid remaining uses")
    if expiry is not None: _pos(expiry, "expiry_step")
    if value["expiry_bucket"] not in {None, "future", "expired"}: raise ValueError("invalid expiry bucket")
    event_id = value["last_public_authority_event_id"]
    if event_id is not None and (not isinstance(event_id, str) or re.fullmatch(r"public_event_[0-9a-f]{16}", event_id) is None): raise ValueError("invalid public authority event ID")
    if value["reask_relation"] not in {None, "do_not_reask_until_scope_change", "reask_on_new_need"}: raise ValueError("invalid reask relation")
    if status is None:
        if any(value[key] is not None for key in ("grant_type", "remaining_uses", "expiry_bucket", "expiry_step", "scope_relation", "last_public_authority_event_id")): raise ValueError("empty authorization summary is inconsistent")
    else:
        if expiry is None or value["expiry_bucket"] is None: raise ValueError("record summary requires expiry")
        expected_bucket = "future" if expiry > logical_step else "expired"
        if value["expiry_bucket"] != expected_bucket: raise ValueError("expiry bucket does not match the current logical step")
        if status == AuthorizationStatus.EXPIRED.value and value["expiry_bucket"] != "expired": raise ValueError("expired status requires expired bucket")
        if status in {AuthorizationStatus.ACTIVE.value, AuthorizationStatus.RESERVED.value} and value["expiry_bucket"] != "future": raise ValueError("live status requires future bucket")
        if status in {AuthorizationStatus.PENDING.value, AuthorizationStatus.REJECTED.value}:
            if grant is not None or uses is not None: raise ValueError("pending/rejected authority cannot carry a grant")
        else:
            if grant is None: raise ValueError("settled authority requires a grant type")
            if grant == GrantType.REUSABLE.value and uses is not None: raise ValueError("reusable authority has unbounded uses")
            if grant == GrantType.ONE_TIME.value and uses is None: raise ValueError("one-time authority requires use count")
            if status == AuthorizationStatus.CONSUMED.value and (grant != GrantType.ONE_TIME.value or uses != 0): raise ValueError("consumed authority must be exhausted one-time grant")
            if status in {AuthorizationStatus.ACTIVE.value, AuthorizationStatus.RESERVED.value} and grant == GrantType.ONE_TIME.value and uses != 1: raise ValueError("live one-time authority must have one use")
    return freeze_value(dict(value))

@dataclass(frozen=True)
class ResolvedCandidate:
    slot_index: int; base_candidate: ActionCandidate; base_candidate_id: str; action: ControllerAction
    public_scope_identity: str; public_scope_hash: str; task_step_id: str | None; authorization_id: str | None
    prior_authorization_id: str | None; public_reason_code: str | None; escalation_target_code: str | None; identifier: str
    def __post_init__(self) -> None:
        if isinstance(self.slot_index, bool) or not isinstance(self.slot_index, int) or self.slot_index < 0: raise ValueError("invalid slot")
        if not isinstance(self.base_candidate, ActionCandidate) or self.base_candidate_id != self.base_candidate.identifier or self.action is not self.base_candidate.action: raise ValueError("base candidate binding invalid")
        if self.public_scope_identity != _scope_identity(self.base_candidate.scope) or self.public_scope_hash != canonical_hash(self.base_candidate.scope): raise ValueError("scope binding invalid")
        fields = (self.task_step_id, self.authorization_id, self.prior_authorization_id, self.public_reason_code, self.escalation_target_code)
        required = {
            ControllerAction.REQUEST_AUTHORIZATION: (True, False, False, False, False), ControllerAction.REQUEST_REFRESH: (True, False, True, False, False),
            ControllerAction.DISABLE_LOCAL_AUTHORIZATION: (False, True, False, False, False), ControllerAction.EXECUTE_WITH_AUTHORIZATION: (True, None, False, False, False),
            ControllerAction.DENY_WITH_REASON: (False, False, False, True, False), ControllerAction.ESCALATE: (False, False, False, False, True),
        }[self.action]
        for item, need in zip(fields, required):
            if need is True and item is None: raise ValueError("missing action binding")
            if need is False and item is not None: raise ValueError("irrelevant action binding")
        if self.task_step_id is not None: object.__setattr__(self, "task_step_id", _task_id(self.task_step_id))
        if self.authorization_id is not None: object.__setattr__(self, "authorization_id", _auth_id(self.authorization_id))
        if self.prior_authorization_id is not None: object.__setattr__(self, "prior_authorization_id", _auth_id(self.prior_authorization_id))
        if self.public_reason_code is not None and self.public_reason_code not in _REASONS: raise ValueError("invalid public reason code")
        if self.escalation_target_code is not None and self.escalation_target_code not in _TARGETS: raise ValueError("invalid escalation target code")
        if self.identifier != self._identifier(): raise ValueError("resolved identifier is not canonical")
    def _semantic(self) -> Mapping[str, Any]:
        base = {"base_candidate_id": self.base_candidate_id, "action": self.action.value, "public_scope_identity": self.public_scope_identity, "public_scope_hash": self.public_scope_hash}
        if self.action in {ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.REQUEST_REFRESH, ControllerAction.EXECUTE_WITH_AUTHORIZATION}: base["task_step_id"] = self.task_step_id
        if self.action in {ControllerAction.EXECUTE_WITH_AUTHORIZATION, ControllerAction.DISABLE_LOCAL_AUTHORIZATION}: base["authorization_id"] = self.authorization_id
        if self.action is ControllerAction.REQUEST_REFRESH: base["prior_authorization_id"] = self.prior_authorization_id
        if self.action is ControllerAction.DENY_WITH_REASON: base["public_reason_code"] = self.public_reason_code
        if self.action is ControllerAction.ESCALATE: base["escalation_target_code"] = self.escalation_target_code
        return base
    def _identifier(self) -> str: return "resolved_" + canonical_hash({"slot_index": self.slot_index, **self._semantic()})[:16]
    def with_slot(self, slot: int) -> "ResolvedCandidate": return replace(self, slot_index=slot, identifier="resolved_" + canonical_hash({"slot_index": slot, **self._semantic()})[:16])
    def public_view(self) -> Mapping[str, Any]: return freeze_value({"slot_index": self.slot_index, "identifier": self.identifier, **self._semantic()})

def make_resolved_candidate(*, base_candidate: ActionCandidate, task_step_id: str | None = None, authorization_id: str | None = None, prior_authorization_id: str | None = None, public_reason_code: str | None = None, escalation_target_code: str | None = None) -> ResolvedCandidate:
    if not isinstance(base_candidate, ActionCandidate): raise ValueError("base candidate required")
    action = base_candidate.action; scope_id = _scope_identity(base_candidate.scope); scope_hash = canonical_hash(base_candidate.scope)
    # calculate from a temporary semantic mapping matching the action matrix.
    data = {"base_candidate_id": base_candidate.identifier, "action": action.value, "public_scope_identity": scope_id, "public_scope_hash": scope_hash}
    if action in {ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.REQUEST_REFRESH, ControllerAction.EXECUTE_WITH_AUTHORIZATION}: data["task_step_id"] = task_step_id
    if action in {ControllerAction.EXECUTE_WITH_AUTHORIZATION, ControllerAction.DISABLE_LOCAL_AUTHORIZATION}: data["authorization_id"] = authorization_id
    if action is ControllerAction.REQUEST_REFRESH: data["prior_authorization_id"] = prior_authorization_id
    if action is ControllerAction.DENY_WITH_REASON: data["public_reason_code"] = public_reason_code
    if action is ControllerAction.ESCALATE: data["escalation_target_code"] = escalation_target_code
    return ResolvedCandidate(0, base_candidate, base_candidate.identifier, action, scope_id, scope_hash, task_step_id, authorization_id, prior_authorization_id, public_reason_code, escalation_target_code, "resolved_" + canonical_hash({"slot_index": 0, **data})[:16])

@dataclass(frozen=True)
class CandidateCatalog:
    slots: tuple[ResolvedCandidate, ...]; catalog_hash: str
    def __post_init__(self) -> None:
        if not isinstance(self.slots, tuple) or len(self.slots) > DEFAULT_CONFIG.candidate_limit or any(not isinstance(slot, ResolvedCandidate) for slot in self.slots): raise ValueError("invalid catalog slots")
        if tuple(slot.slot_index for slot in self.slots) != tuple(range(len(self.slots))): raise ValueError("catalog slots must be contiguous")
        keys = tuple(canonical_hash(slot._semantic()) for slot in self.slots)
        if len(set(keys)) != len(keys) or keys != tuple(sorted(keys)): raise ValueError("catalog is not canonical")
        if self.catalog_hash != canonical_hash(tuple(slot.public_view() for slot in self.slots)): raise ValueError("catalog hash invalid")
    @classmethod
    def build(cls, candidates: Sequence[ResolvedCandidate]) -> "CandidateCatalog":
        if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence): raise ValueError("candidates must be sequence")
        ordered = tuple(item.with_slot(index) for index, item in enumerate(sorted(tuple(candidates), key=lambda item: canonical_hash(item._semantic()))))
        return cls(ordered, canonical_hash(tuple(item.public_view() for item in ordered)))
    def public_view(self) -> tuple[Mapping[str, Any], ...]: return tuple(item.public_view() for item in self.slots)

@dataclass(frozen=True)
class PublicMaskState:
    logical_step: int; task_view: Mapping[str, Any]; authorization_views: Mapping[str, Mapping[str, Any]]; preference_relation: Mapping[str, str] | None
    def __post_init__(self) -> None:
        object.__setattr__(self, "logical_step", _pos(self.logical_step, "logical_step")); object.__setattr__(self, "task_view", _task_view(self.task_view))
        if not isinstance(self.authorization_views, Mapping): raise ValueError("authorization views must be mapping")
        rows = { _auth_id(key): _summary(value, self.logical_step) for key, value in self.authorization_views.items() }
        object.__setattr__(self, "authorization_views", freeze_value(rows))
        if self.preference_relation is None: object.__setattr__(self, "preference_relation", freeze_value({}))
        elif not isinstance(self.preference_relation, Mapping) or any(not isinstance(k, str) or not re.fullmatch(r"scope_[0-9a-f]{16}", k) or v not in {"do_not_reask_until_scope_change", "reask_on_new_need"} for k, v in self.preference_relation.items()): raise ValueError("invalid preference relation")
        else: object.__setattr__(self, "preference_relation", freeze_value(dict(self.preference_relation)))

def build_action_mask(catalog: CandidateCatalog, state: PublicMaskState) -> tuple[bool, ...]:
    if not isinstance(catalog, CandidateCatalog) or not isinstance(state, PublicMaskState): raise ValueError("public catalog/state required")
    finished = state.task_view["phase"] == "finished" or state.task_view["primary_complete"] or state.task_view["has_unknown_effect"]
    out=[]
    for slot in catalog.slots:
        view = state.authorization_views.get(slot.authorization_id or slot.prior_authorization_id or "")
        status = None if view is None else view["status"]; relation = None if view is None else view["scope_relation"]
        uses = None if view is None else view["remaining_uses"]; expiry = None if view is None else view["expiry_step"]
        active_cover = view is not None and status == AuthorizationStatus.ACTIVE.value and relation in {ScopeRelation.EXACT.value, ScopeRelation.NARROWER.value} and isinstance(expiry, int) and expiry > state.logical_step and (uses is None or uses > 0)
        if slot.action in {ControllerAction.DENY_WITH_REASON, ControllerAction.ESCALATE}: out.append(True)
        elif slot.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION: out.append(not finished and active_cover)
        elif slot.action is ControllerAction.REQUEST_AUTHORIZATION: out.append(state.preference_relation.get(slot.public_scope_identity) != "do_not_reask_until_scope_change")
        elif slot.action is ControllerAction.REQUEST_REFRESH: out.append(view is not None and status in {"active", "consumed", "expired", "revoked", "superseded"} and relation in {ScopeRelation.EXACT.value, ScopeRelation.NARROWER.value, ScopeRelation.BROADER.value} and state.preference_relation.get(slot.public_scope_identity) != "do_not_reask_until_scope_change")
        else: out.append(view is not None and status == AuthorizationStatus.ACTIVE.value)
    if catalog.slots and not any(out): raise ValueError("catalog needs a safe action")
    return tuple(out)

def _request_context(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"request", "task"}: raise ValueError("request context must use the canonical public schema")
    if any(not isinstance(value[key], str) or not value[key].strip() for key in ("request", "task")): raise ValueError("request context fields must be non-empty text")
    return freeze_value({"request": value["request"], "task": value["task"]})

def _history(records: Sequence[PublicEventRecord]) -> Mapping[str, Any]:
    try: verify_public_event_chain(records)
    except PublicEventChainError as error: raise ValueError("history must be a verified public chain") from error
    recent=[record.public_view() for record in records[-4:]]; pad={"sequence":None,"event_id":None,"logical_step":None,"event_type":None,"payload":freeze_value({}),"payload_hash":None,"previous_event_hash":None,"event_hash":None}
    recent=[pad for _ in range(4-len(recent))]+recent; types=[record.event_type for record in records]
    counts={"prompt":types.count("permission_requested"),"permission_choice":types.count("permission_granted")+types.count("permission_denied"),"denial":types.count("permission_denied")+types.count("denied_with_reason"),"revocation":types.count("authorization_revoked")+types.count("local_authorization_disabled"),"grant":types.count("permission_granted"),"verified_error":types.count("verified_error")+types.count("execution_blocked")}
    response={"allow":counts["grant"],"deny":types.count("permission_denied"),"total":counts["permission_choice"]}; d=response["total"]+2.0
    return freeze_value({"records":tuple(recent),"counts":counts,"response_counts":response,"response_rates":{"allow":(response["allow"]+1.0)/d,"deny":(response["deny"]+1.0)/d}})

def _candidate_views(value: tuple[Mapping[str, Any], ...]) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, tuple): raise ValueError("candidate catalog view must be a tuple")
    frozen: list[Mapping[str, Any]]=[]; semantic_hashes=[]
    common={"slot_index","identifier","base_candidate_id","action","public_scope_identity","public_scope_hash"}
    action_fields={
        ControllerAction.REQUEST_AUTHORIZATION:{"task_step_id"}, ControllerAction.REQUEST_REFRESH:{"task_step_id","prior_authorization_id"},
        ControllerAction.DISABLE_LOCAL_AUTHORIZATION:{"authorization_id"}, ControllerAction.EXECUTE_WITH_AUTHORIZATION:{"task_step_id","authorization_id"},
        ControllerAction.DENY_WITH_REASON:{"public_reason_code"}, ControllerAction.ESCALATE:{"escalation_target_code"},
    }
    for expected_slot, row in enumerate(value):
        if not isinstance(row,Mapping) or not isinstance(row.get("action"),str): raise ValueError("invalid candidate public view")
        try: action=ControllerAction(row["action"])
        except ValueError as error: raise ValueError("invalid candidate action") from error
        if set(row)!=common|action_fields[action] or row["slot_index"]!=expected_slot or isinstance(row["slot_index"],bool): raise ValueError("candidate public schema is invalid")
        if not isinstance(row["identifier"],str) or re.fullmatch(r"resolved_[0-9a-f]{16}",row["identifier"]) is None: raise ValueError("invalid resolved ID")
        if not isinstance(row["base_candidate_id"],str) or re.fullmatch(r"candidate_[0-9a-f]{16}",row["base_candidate_id"]) is None: raise ValueError("invalid base candidate ID")
        if not isinstance(row["public_scope_identity"],str) or re.fullmatch(r"scope_[0-9a-f]{16}",row["public_scope_identity"]) is None or not isinstance(row["public_scope_hash"],str) or _HASH64.fullmatch(row["public_scope_hash"]) is None: raise ValueError("invalid candidate scope")
        if row["public_scope_identity"] != "scope_" + row["public_scope_hash"][:16]: raise ValueError("candidate scope identity does not match scope hash")
        for key in action_fields[action]:
            item=row[key]
            if key=="authorization_id" and action is ControllerAction.EXECUTE_WITH_AUTHORIZATION and item is None: continue
            if key in {"authorization_id","prior_authorization_id"}: _auth_id(item)
            elif key=="task_step_id": _task_id(item)
            elif key=="public_reason_code" and item not in _REASONS: raise ValueError("invalid reason code")
            elif key=="escalation_target_code" and item not in _TARGETS: raise ValueError("invalid target code")
        semantic={key:row[key] for key in row if key not in {"slot_index","identifier"}}
        if row["identifier"]!="resolved_"+canonical_hash({"slot_index":expected_slot,**semantic})[:16]: raise ValueError("resolved view hash is invalid")
        semantic_hashes.append(canonical_hash(semantic)); frozen.append(freeze_value(dict(row)))
    if len(set(semantic_hashes))!=len(semantic_hashes) or tuple(semantic_hashes)!=tuple(sorted(semantic_hashes)): raise ValueError("candidate public views are not canonical")
    return tuple(frozen)

def _interaction_view(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value,Mapping) or set(value)!={"records","counts","response_counts","response_rates"}: raise ValueError("invalid observation history schema")
    records=value["records"]
    if not isinstance(records,tuple) or len(records)!=4: raise ValueError("history must contain exactly four records")
    record_keys={"sequence","event_id","logical_step","event_type","payload","payload_hash","previous_event_hash","event_hash"}; frozen_records=[]; seen_real=False; first_record=None; previous_record=None; visible_types=[]
    for row in records:
        if not isinstance(row,Mapping) or set(row)!=record_keys: raise ValueError("invalid public history record schema")
        if row["sequence"] is None:
            if seen_real or any(row[key] is not None for key in record_keys-{"payload","sequence"}) or not isinstance(row["payload"],Mapping) or row["payload"]: raise ValueError("invalid history padding")
            frozen_records.append(freeze_value(dict(row))); continue
        seen_real=True
        try: record=PublicEventRecord(row["sequence"],row["event_id"],row["logical_step"],row["event_type"],row["payload"],row["payload_hash"],row["previous_event_hash"],row["event_hash"])
        except (TypeError,ValueError) as error: raise ValueError("invalid public history record") from error
        if previous_record is None:
            if (record.sequence == 1) != (record.previous_event_hash is None): raise ValueError("first visible public history record has invalid predecessor")
            first_record=record
        if previous_record is not None and (record.sequence!=previous_record.sequence+1 or record.previous_event_hash!=previous_record.event_hash or record.logical_step<previous_record.logical_step): raise ValueError("public history record order/linkage is invalid")
        previous_record=record; visible_types.append(record.event_type)
        frozen_records.append(record.public_view())
    count_keys={"prompt","permission_choice","denial","revocation","grant","verified_error"}; response_keys={"allow","deny","total"}; rate_keys={"allow","deny"}
    if not isinstance(value["counts"],Mapping) or set(value["counts"])!=count_keys or not isinstance(value["response_counts"],Mapping) or set(value["response_counts"])!=response_keys or not isinstance(value["response_rates"],Mapping) or set(value["response_rates"])!=rate_keys: raise ValueError("invalid history statistics schema")
    if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in (*value["counts"].values(),*value["response_counts"].values())): raise ValueError("history counts must be nonnegative integers")
    counts=value["counts"]; response=value["response_counts"]
    if response["total"]!=response["allow"]+response["deny"] or response["total"]!=counts["permission_choice"] or response["allow"]!=counts["grant"] or counts["denial"]<response["deny"]: raise ValueError("history response counts are inconsistent")
    visible_counts={"prompt":visible_types.count("permission_requested"),"permission_choice":visible_types.count("permission_granted")+visible_types.count("permission_denied"),"denial":visible_types.count("permission_denied")+visible_types.count("denied_with_reason"),"revocation":visible_types.count("authorization_revoked")+visible_types.count("local_authorization_disabled"),"grant":visible_types.count("permission_granted"),"verified_error":visible_types.count("verified_error")+visible_types.count("execution_blocked")}
    visible_response={"allow":visible_counts["grant"],"deny":visible_types.count("permission_denied"),"total":visible_counts["permission_choice"]}
    if any(counts[key]<visible_counts[key] for key in count_keys) or any(response[key]<visible_response[key] for key in response_keys): raise ValueError("history statistics undercount visible records")
    if (first_record is None or first_record.sequence==1) and (dict(counts)!=visible_counts or dict(response)!=visible_response): raise ValueError("complete visible history statistics are not exact")
    denominator=response["total"]+2.0; expected={"allow":(response["allow"]+1.0)/denominator,"deny":(response["deny"]+1.0)/denominator}
    if any(type(value["response_rates"][key]) is not float or value["response_rates"][key]!=expected[key] for key in rate_keys): raise ValueError("history response rates are inconsistent")
    return freeze_value({"records":tuple(frozen_records),"counts":dict(counts),"response_counts":dict(response),"response_rates":dict(value["response_rates"])})

@dataclass(frozen=True)
class EnvironmentObservation:
    scenario_id:str; environment_version:str; logical_step:int; horizon:int; horizon_remaining:int; request_context:Mapping[str,Any]; task_view:Mapping[str,Any]; authorization_views:Mapping[str,Any]; interaction_history:Mapping[str,Any]; candidate_catalog:tuple[Mapping[str,Any],...]; catalog_hash:str; action_mask:tuple[bool,...]
    def __post_init__(self) -> None:
        if not isinstance(self.scenario_id,str) or not self.scenario_id or not isinstance(self.environment_version,str) or not self.environment_version: raise ValueError("invalid observation identity")
        _pos(self.horizon,"horizon")
        if self.logical_step == self.horizon+1:
            if self.horizon_remaining != 0 or self.candidate_catalog != () or self.catalog_hash != canonical_hash(()) or self.action_mask != (): raise ValueError("closed observation must have no live catalog")
        elif not (isinstance(self.logical_step,int) and not isinstance(self.logical_step,bool) and 1<=self.logical_step<=self.horizon and self.horizon_remaining==self.horizon-self.logical_step+1): raise ValueError("invalid live observation step")
        object.__setattr__(self,"request_context",_request_context(self.request_context)); object.__setattr__(self,"task_view",_task_view(self.task_view)); object.__setattr__(self,"authorization_views",freeze_value({ _auth_id(k):_summary(v,self.logical_step) for k,v in self.authorization_views.items()}))
        catalog_view=_candidate_views(self.candidate_catalog); object.__setattr__(self,"candidate_catalog",catalog_view)
        if not isinstance(self.action_mask,tuple) or len(catalog_view)!=len(self.action_mask) or any(not isinstance(x,bool) for x in self.action_mask): raise ValueError("invalid observation policy data")
        if not isinstance(self.catalog_hash, str) or _HASH64.fullmatch(self.catalog_hash) is None or self.catalog_hash != canonical_hash(catalog_view): raise ValueError("invalid observation catalog hash")
        object.__setattr__(self,"interaction_history",_interaction_view(self.interaction_history))
    def as_mapping(self)->Mapping[str,Any]: return freeze_value({k:getattr(self,k) for k in ("scenario_id","environment_version","logical_step","horizon","horizon_remaining","request_context","task_view","authorization_views","interaction_history","candidate_catalog","catalog_hash","action_mask")})

def build_environment_observation(*,scenario_id:str,environment_version:str,logical_step:int,horizon:int,request_context:Mapping[str,Any],task_view:Mapping[str,Any],authorization_views:Mapping[str,Mapping[str,Any]],public_records:Sequence[PublicEventRecord],catalog:CandidateCatalog,action_mask:Sequence[bool])->EnvironmentObservation:
    if not isinstance(catalog,CandidateCatalog): raise ValueError("catalog required")
    closed=logical_step==horizon+1
    if closed:
        if catalog.slots or tuple(action_mask): raise ValueError("closed observation cannot select actions")
    elif logical_step>horizon or logical_step<1: raise ValueError("invalid observation logical step")
    return EnvironmentObservation(scenario_id,environment_version,logical_step,horizon,0 if closed else horizon-logical_step+1,request_context,_task_view(task_view),authorization_views,_history(public_records),() if closed else catalog.public_view(),canonical_hash(()) if closed else catalog.catalog_hash,tuple(action_mask))
