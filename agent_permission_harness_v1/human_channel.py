"""Typed in-memory human inbox; transport alone never grants authority.

Messages stay local. Permission replies are only observations for the separate
ledger dispatcher, which must verify the pending request before issuing a grant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal
from uuid import uuid4

from pa_rl.contracts import PermissionChoice, Scope, contract_json_round_trip


MessageKind = Literal["permission", "escalation"]
ReplyKind = Literal["permission", "clarification", "deny", "stop"]


def _text(value: object, name: str, *, empty: bool = False) -> None:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"{name} must be {'text' if empty else 'non-empty text'}")


@dataclass(frozen=True)
class HumanMessage:
    message_id: str
    kind: MessageKind
    task_goal: str
    step_id: str
    requested_scope: Scope | None
    logical_step: int
    reason: str

    def __post_init__(self) -> None:
        for name in ("message_id", "task_goal", "step_id", "reason"):
            _text(getattr(self, name), name)
        if not isinstance(self.kind, str) or self.kind not in {"permission", "escalation"}:
            raise ValueError("message kind must be permission or escalation")
        if self.requested_scope is not None and not isinstance(self.requested_scope, Scope):
            raise ValueError("requested_scope must be a Scope or None")
        if self.kind == "permission" and self.requested_scope is None:
            raise ValueError("permission requests require a scope")
        if type(self.logical_step) is not int or self.logical_step < 0:
            raise ValueError("logical_step must be a non-negative integer")


@dataclass(frozen=True)
class HumanReply:
    message_id: str
    kind: ReplyKind
    permission: PermissionChoice | None = None
    text: str = ""

    def __post_init__(self) -> None:
        _text(self.message_id, "message_id")
        _text(self.text, "text", empty=True)
        if not isinstance(self.kind, str) or self.kind not in {"permission", "clarification", "deny", "stop"}:
            raise ValueError("reply kind must be permission, clarification, deny or stop")
        if self.kind == "permission":
            if not isinstance(self.permission, PermissionChoice):
                raise ValueError("permission replies require a typed PermissionChoice")
        elif self.permission is not None:
            raise ValueError("only permission replies may carry a permission choice")
        if self.kind == "clarification" and not self.text.strip():
            raise ValueError("clarification replies require text")


HumanResponder = Callable[[HumanMessage], HumanReply | None]


class LocalHumanChannel:
    """Local message delivery with matching IDs and once-consumed replies."""

    def __init__(self, responder: HumanResponder | None = None, *, session_id: str | None = None) -> None:
        if responder is not None and not callable(responder):
            raise ValueError("responder must be callable or None")
        self._responder = responder
        if session_id is not None:
            _text(session_id, 'session_id')
        # An explicit ID is for reproducible, isolated offline fixtures only.
        self._session_id = uuid4().hex if session_id is None else session_id
        self._messages: dict[str, HumanMessage] = {}
        self._replies: dict[str, HumanReply] = {}
        self._consumed: set[str] = set()

    def send(
        self,
        kind: MessageKind,
        task_goal: str,
        step_id: str,
        requested_scope: Scope | None,
        logical_step: int,
        reason: str,
    ) -> HumanMessage:
        message = HumanMessage(
            f"human_{self._session_id}_{len(self._messages) + 1:06d}", kind, task_goal, step_id,
            requested_scope, logical_step, reason,
        )
        self._messages[message.message_id] = message
        if self._responder is not None:
            reply = self._responder(message)
            if reply is not None:
                if not isinstance(reply, HumanReply) or reply.message_id != message.message_id:
                    raise ValueError("responder must return a reply matching the sent message")
                self.submit(reply)
        return message

    def submit(self, reply: HumanReply) -> None:
        if not isinstance(reply, HumanReply):
            raise ValueError("reply must be a HumanReply")
        if reply.message_id not in self._messages:
            raise ValueError("unknown human message ID")
        if reply.message_id in self._replies or reply.message_id in self._consumed:
            raise ValueError("human message already has a reply")
        message = self._messages[reply.message_id]
        if message.kind == "escalation" and reply.kind == "permission":
            raise ValueError("escalation clarification cannot confer permission")
        self._replies[reply.message_id] = reply

    def take_reply(self, message_id: str) -> HumanReply | None:
        _text(message_id, "message_id")
        if message_id not in self._messages:
            raise ValueError("unknown human message ID")
        if message_id in self._consumed:
            raise ValueError("human reply already consumed")
        reply = self._replies.get(message_id)
        if reply is not None:
            self._consumed.add(message_id)
        return reply

    def snapshot(self) -> dict:
        return {
            "messages": [
                {
                    "message": contract_json_round_trip(message),
                    "status": (
                        "consumed" if message_id in self._consumed else
                        "replied" if message_id in self._replies else "pending"
                    ),
                    "reply": contract_json_round_trip(self._replies.get(message_id)),
                }
                for message_id, message in self._messages.items()
            ]
        }


__all__ = ["HumanMessage", "HumanReply", "HumanResponder", "LocalHumanChannel"]
