"""Local human messages must never fabricate or replay authority."""

import json
import unittest

from pa_rl.contracts import PermissionChoice, Scope

from agent_permission_harness_v1.human_channel import (
    HumanReply,
    LocalHumanChannel,
)


def scope():
    return Scope("work", "Cloud Drive", "report", ("summary",), "read",
                 "send summary", "agent", "session")


class HumanChannelTests(unittest.TestCase):
    def message(self, channel, kind="permission"):
        return channel.send(kind, "Share project summary", "read-report", scope(),
                            3, "Scope needs user approval")

    def test_request_waits_without_responder_and_reply_is_once_consumed(self):
        channel = LocalHumanChannel()
        message = self.message(channel)
        self.assertIsNone(channel.take_reply(message.message_id))
        channel.submit(HumanReply(message.message_id, "permission",
                                  PermissionChoice.ALLOW_ONCE))
        self.assertEqual(channel.take_reply(message.message_id).permission,
                         PermissionChoice.ALLOW_ONCE)
        with self.assertRaises(ValueError):
            channel.take_reply(message.message_id)
        with self.assertRaises(ValueError):
            channel.submit(HumanReply(message.message_id, "permission",
                                      PermissionChoice.ALLOW_REUSE))

    def test_escalation_clarification_never_becomes_permission(self):
        channel = LocalHumanChannel()
        message = self.message(channel, "escalation")
        with self.assertRaises(ValueError):
            channel.submit(HumanReply(message.message_id, "permission",
                                      PermissionChoice.ALLOW_REUSE))
        channel.submit(HumanReply(message.message_id, "clarification",
                                  text="Use only the summary fields"))
        reply = channel.take_reply(message.message_id)
        self.assertIsNone(reply.permission)
        self.assertEqual(reply.text, "Use only the summary fields")

    def test_unknown_and_duplicate_replies_cannot_replace_first_answer(self):
        channel = LocalHumanChannel()
        message = self.message(channel)
        with self.assertRaises(ValueError):
            channel.submit(HumanReply("missing-message", "permission",
                                      PermissionChoice.ALLOW_ONCE))
        channel.submit(HumanReply(message.message_id, "permission",
                                  PermissionChoice.DENY_PERSIST))
        with self.assertRaises(ValueError):
            channel.submit(HumanReply(message.message_id, "permission",
                                      PermissionChoice.ALLOW_REUSE))
        self.assertEqual(channel.take_reply(message.message_id).permission,
                         PermissionChoice.DENY_PERSIST)

    def test_injected_responder_creates_actual_typed_reply(self):
        def responder(message):
            return HumanReply(message.message_id, "permission",
                              PermissionChoice.ALLOW_ONCE)
        channel = LocalHumanChannel(responder)
        message = self.message(channel)
        self.assertEqual(channel.take_reply(message.message_id).permission,
                         PermissionChoice.ALLOW_ONCE)

    def test_responder_must_match_current_message(self):
        channel = LocalHumanChannel(
            lambda message: HumanReply("different-id", "permission",
                                       PermissionChoice.ALLOW_REUSE))
        with self.assertRaises(ValueError):
            self.message(channel)
        self.assertEqual(channel.snapshot()["messages"][0]["status"], "pending")

    def test_reply_schema_rejects_untyped_or_misplaced_permission(self):
        for kind, permission in (("permission", None),
                                 ("permission", "allow_once"),
                                 ("clarification", PermissionChoice.ALLOW_ONCE),
                                 ("deny", PermissionChoice.DENY_PERSIST),
                                 ("unknown", None)):
            with self.subTest(kind=kind, permission=permission):
                with self.assertRaises(ValueError):
                    HumanReply("human-1", kind, permission, "explanation")
        channel = LocalHumanChannel()
        with self.assertRaises(ValueError):
            channel.submit({"message_id": "human-1", "kind": "permission"})

    def test_snapshot_is_json_safe_and_does_not_expose_mutable_state(self):
        channel = LocalHumanChannel()
        message = self.message(channel)
        channel.submit(HumanReply(message.message_id, "deny", text="Do not read"))
        snapshot = channel.snapshot()
        self.assertEqual(json.loads(json.dumps(snapshot))["messages"][0]["reply"]["kind"],
                         "deny")
        snapshot["messages"][0]["status"] = "consumed"
        self.assertEqual(channel.snapshot()["messages"][0]["status"], "replied")
        self.assertEqual(channel.take_reply(message.message_id).kind, "deny")

    def test_invalid_message_shape_has_no_outbox_effect(self):
        channel = LocalHumanChannel()
        for kind, requested, logical in (("send-email", scope(), 0),
                                         ("permission", None, 0),
                                         ("permission", scope(), -1),
                                         ("permission", scope(), True)):
            with self.subTest(kind=kind, logical=logical):
                with self.assertRaises(ValueError):
                    channel.send(kind, "Task", "read", requested, logical, "why")
        self.assertEqual(channel.snapshot(), {"messages": []})

    def test_malformed_kinds_and_message_ids_raise_validation_errors(self):
        channel = LocalHumanChannel()
        with self.assertRaises(ValueError):
            channel.send([], "Task", "read", scope(), 0, "why")
        with self.assertRaises(ValueError):
            HumanReply("human-1", [], text="invalid")
        for identifier in (None, [], "", "unknown"):
            with self.subTest(identifier=identifier):
                with self.assertRaises(ValueError):
                    channel.take_reply(identifier)

    def test_previous_session_message_cannot_answer_new_session_request(self):
        previous = LocalHumanChannel()
        previous_message = self.message(previous)
        current = LocalHumanChannel()
        current_message = self.message(current)
        with self.assertRaises(ValueError):
            current.submit(HumanReply(previous_message.message_id, "permission",
                                      PermissionChoice.ALLOW_REUSE))
        self.assertIsNone(current.take_reply(current_message.message_id))


if __name__ == "__main__":
    unittest.main()
