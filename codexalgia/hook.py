"""Codex hook: one handler for every event, recording state and sending notifications when enabled.

It prints nothing, so it never answers a PermissionRequest or blocks a Stop: Codex carries on as without it.
"""
import json
import os
import subprocess
import sys
import time

from . import config, notify, paths, state

# Codex event -> state to record; None removes the session.
# Subagents report their parent's session_id, so their tool events keep the parent busy. SubagentStop
# isn't handled, because the parent usually keeps working after it.
EVENTS = {
    "SessionStart": state.READY,
    "UserPromptSubmit": state.BUSY,
    "PreToolUse": state.BUSY,
    "PostToolUse": state.BUSY,
    "PermissionRequest": state.WAITING,
    "Stop": state.READY,
    "Interrupt": state.READY,
    "SessionEnd": None,
}

SUMMARY_LENGTH = 120


def handle(payload):
    event = payload.get("hook_event_name")
    if event not in EVENTS:
        return
    session = str(payload.get("session_id") or "default")
    value = EVENTS[event]
    if value is None:
        state.clear(session)
    else:
        state.set_state(session, value)

    settings = config.load()
    if settings["notifications"]:
        message = notification_for(event, payload)
        if message and event == "PermissionRequest":
            remind_later(session, *message[:2])
        elif message:
            notify.send(*message, sound=settings["sound"])


def notification_for(event, payload):
    """Return (title, message, icon) for events worth a notification, else None."""
    project = os.path.basename(os.path.normpath(payload.get("cwd") or os.getcwd()))
    if event == "Stop":
        message = summarize(payload.get("last_assistant_message")) or "Task finished"
        return f"Codex is ready · {project}", message, paths.icon("hip-ok")
    if event == "PermissionRequest":
        return f"Codex needs you · {project}", _approval_message(payload), paths.icon("hip-pain")
    return None


def remind_later(session, title, message):
    """Start a detached `remind`, so the hook returns at once and Codex can go on deciding the approval."""
    stamp = state.current(session)[1]
    command = [sys.executable, str(paths.app_file()), "remind", session, str(stamp), title, message]
    quiet = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        subprocess.Popen(command, creationflags=notify.CREATE_NO_WINDOW, **quiet)
    else:
        subprocess.Popen(command, start_new_session=True, **quiet)


def remind(session, stamp, title, message):
    """Notify only if the session is still waiting after the grace period, unchanged since `stamp`.

    When Codex approves a call itself, the tool usually runs and finishes within that time, and its
    PostToolUse changes the state. A call that takes longer can still cause a notification.
    """
    time.sleep(state.APPROVAL_GRACE_SECONDS)
    settings = config.load()
    if settings["notifications"] and state.current(session) == (state.WAITING, int(stamp)):
        notify.send(title, message, paths.icon("hip-pain"), sound=settings["sound"])


def _approval_message(payload):
    # PermissionRequest has no message field, so describe the tool that is waiting for approval.
    tool = payload.get("tool_name") or "a tool"
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if isinstance(command, list):
        command = " ".join(str(part) for part in command)
    if tool == "Bash" and command:
        return f"Wants to run: {summarize(command)}"
    if tool == "apply_patch":
        return "Wants to edit files"
    return f"Wants to use {tool}"


def summarize(text):
    """The first non-empty line of `text`, without Markdown markers, shortened to fit a notification."""
    line = next((line for line in str(text or "").splitlines() if line.strip()), "")
    line = " ".join(line.replace("**", "").replace("`", "").lstrip("#>*- \t").split())
    if len(line) > SUMMARY_LENGTH:
        line = line[: SUMMARY_LENGTH - 1].rstrip() + "…"
    return line


def main():
    try:
        handle(json.load(sys.stdin))
    except Exception:
        pass  # a failing hook must never block Codex
