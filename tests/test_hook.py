import io
import json
import time
from contextlib import redirect_stdout
from unittest import mock

from codexalgia import config, hook, state
from tests.support import IsolatedTestCase


class HookTest(IsolatedTestCase):
    def run_hook(self, event, **payload):
        payload = {"hook_event_name": event, "session_id": "s1", "cwd": "/work/project", **payload}
        with mock.patch("sys.stdin", io.StringIO(json.dumps(payload))), redirect_stdout(io.StringIO()) as out:
            hook.main()
        return out.getvalue()

    def test_events_update_state(self):
        self.run_hook("UserPromptSubmit")
        self.assertEqual(state.summary()["state"], "busy")
        self.run_hook("Stop")
        self.assertEqual(state.summary(), {"state": "ready", "busy": 0, "total": 1})
        self.run_hook("SessionEnd")
        self.assertEqual(state.summary()["total"], 0)

    def test_permission_request_means_ready_after_the_grace_period(self):
        self.run_hook("PreToolUse", tool_name="Bash")
        self.run_hook("PermissionRequest", tool_name="Bash")
        self.assertEqual(state.summary()["state"], "busy")  # Codex may still approve it itself
        later = time.time() + state.APPROVAL_GRACE_SECONDS + 1
        self.assertEqual(state.summary(now=later)["state"], "ready")
        self.run_hook("PostToolUse", tool_name="Bash")
        self.assertEqual(state.summary(now=later)["state"], "busy")

    def test_interrupt_means_ready(self):
        self.run_hook("PreToolUse")
        self.run_hook("Interrupt")
        self.assertEqual(state.summary()["state"], "ready")

    def test_subagent_events_do_not_change_state(self):
        # Subagents share their parent's session_id, and the parent keeps working after SubagentStop.
        self.run_hook("PreToolUse")
        self.run_hook("SubagentStop", agent_id="a1")
        self.assertEqual(state.summary()["state"], "busy")

    @mock.patch("codexalgia.hook.subprocess.Popen")
    def test_hook_prints_nothing(self, popen):
        # Output could answer a PermissionRequest or block a Stop.
        config.save({"notifications": True})
        with mock.patch("codexalgia.notify.send"):
            for event in hook.EVENTS:
                self.assertEqual(self.run_hook(event, tool_name="Bash"), "")

    def test_unknown_event_and_bad_input_are_ignored(self):
        self.run_hook("SomethingNew")
        with mock.patch("sys.stdin", io.StringIO("not json")):
            hook.main()
        self.assertEqual(state.summary()["total"], 0)

    @mock.patch("codexalgia.notify.send")
    def test_no_notifications_unless_enabled(self, send):
        self.run_hook("Stop")
        send.assert_not_called()

    @mock.patch("codexalgia.notify.send")
    def test_notifications_when_enabled(self, send):
        config.save({"notifications": True})
        self.run_hook("Stop", last_assistant_message="")
        self.run_hook("Interrupt")
        self.assertEqual([c.args[:2] for c in send.call_args_list], [("Codex is ready · project", "Task finished")])
        self.assertTrue(send.call_args.kwargs["sound"])

    @mock.patch("codexalgia.notify.send")
    @mock.patch("codexalgia.hook.subprocess.Popen")
    def test_approval_is_left_to_a_detached_reminder(self, popen, send):
        config.save({"notifications": True})
        self.run_hook("PermissionRequest", tool_name="Bash", tool_input={"command": "npm test"})
        send.assert_not_called()
        command = popen.call_args.args[0]
        self.assertEqual(command[2:4], ["remind", "s1"])
        self.assertEqual(command[5:], ["Codex needs you · project", "Wants to run: npm test"])
        self.assertEqual(popen.call_args.kwargs["stdout"], hook.subprocess.DEVNULL)  # or Codex waits for it

    @mock.patch("codexalgia.hook.subprocess.Popen")
    def test_no_reminder_unless_enabled(self, popen):
        self.run_hook("PermissionRequest", tool_name="Bash")
        popen.assert_not_called()

    @mock.patch("codexalgia.notify.send")
    def test_sound_setting_is_passed_to_notifier(self, send):
        config.save({"notifications": True, "sound": False})
        self.run_hook("Stop")
        self.assertFalse(send.call_args.kwargs["sound"])

    @mock.patch("codexalgia.notify.send", side_effect=OSError("no notifier"))
    def test_notifier_failure_does_not_raise(self, send):
        config.save({"notifications": True})
        self.run_hook("Stop")
        self.assertEqual(state.summary()["state"], "ready")


@mock.patch.object(state, "APPROVAL_GRACE_SECONDS", 0)
@mock.patch("codexalgia.notify.send")
class RemindTest(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        config.save({"notifications": True, "sound": False})
        state.set_state("s1", state.WAITING)
        self.stamp = str(state.current("s1")[1])

    def remind(self):
        hook.remind("s1", self.stamp, "Codex needs you · project", "Wants to edit files")

    def test_notifies_when_still_waiting(self, send):
        self.remind()
        self.assertEqual(send.call_args.args[:2], ("Codex needs you · project", "Wants to edit files"))
        self.assertFalse(send.call_args.kwargs["sound"])

    def test_silent_when_codex_approved_it_itself(self, send):
        state.set_state("s1", state.BUSY)  # PostToolUse: the tool already ran
        self.remind()
        send.assert_not_called()

    def test_silent_for_an_older_request(self, send):
        self.stamp = str(int(self.stamp) - 1)  # a newer PermissionRequest has its own reminder
        self.remind()
        send.assert_not_called()

    def test_silent_when_session_ended_or_notifications_turned_off(self, send):
        config.save({"notifications": False})
        self.remind()
        state.clear("s1")
        config.save({"notifications": True})
        self.remind()
        send.assert_not_called()


class NotificationTextTest(IsolatedTestCase):
    def message(self, event, **payload):
        return hook.notification_for(event, {"cwd": "/work/project", **payload})[1]

    def test_stop_shows_the_first_line_of_the_last_answer(self):
        answer = "\n## **Done.** All `42` tests pass\n\nDetails follow."
        self.assertEqual(self.message("Stop", last_assistant_message=answer), "Done. All 42 tests pass")

    def test_long_answers_are_shortened(self):
        text = self.message("Stop", last_assistant_message="word " * 100)
        self.assertEqual(len(text), hook.SUMMARY_LENGTH)
        self.assertTrue(text.endswith("…"))

    def test_approval_describes_the_tool(self):
        self.assertEqual(self.message("PermissionRequest", tool_name="apply_patch", tool_input={}), "Wants to edit files")
        self.assertEqual(self.message("PermissionRequest", tool_name="mcp__github__merge"), "Wants to use mcp__github__merge")
        self.assertEqual(
            self.message("PermissionRequest", tool_name="Bash", tool_input={"command": ["git", "push"]}),
            "Wants to run: git push",
        )
        self.assertEqual(self.message("PermissionRequest"), "Wants to use a tool")

    def test_quiet_events_have_no_notification(self):
        for event in ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Interrupt", "SessionEnd"):
            self.assertIsNone(hook.notification_for(event, {}))
