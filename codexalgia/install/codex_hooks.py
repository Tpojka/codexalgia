"""Adds and removes Codexalgia's hooks in ~/.codex/hooks.json, leaving every other hook alone.

Codex runs a hook only after the user trusts it with /hooks, and it remembers that trust by the hook's
position in the file and a hash of its definition. So a reinstall rewrites our hooks where they already
are, with the same command and timeout, and Codex keeps trusting them.
"""
import json
import os
import shutil
from pathlib import Path

from ..hook import EVENTS

# Commands containing this belong to Codexalgia.
MARKER = "codexalgia.pyz"

# Codex gives these events 1 s by default and at most 3 s. A login shell plus Python can need more than 1 s.
SHORT_EVENTS = ("SessionEnd", "Interrupt")


def codex_home():
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def hooks_path():
    return codex_home() / "hooks.json"


def install(command):
    """Register `command` for every event the hook handles. Returns False if nothing changed."""
    return _update(command)


def uninstall():
    _update(None)


def handler(event, command):
    return {"type": "command", "command": command, "timeout": 3 if event in SHORT_EVENTS else 5}


def hooks_disabled():
    """True if ~/.codex/config.toml turns hooks off with `[features] hooks = false`."""
    try:
        text = (codex_home() / "config.toml").read_text(encoding="utf-8")
    except OSError:
        return False
    table = ""
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("["):
            table = line.strip("[] ").replace(" ", "")
            continue
        key, found, value = line.partition("=")
        key = key.strip().replace(" ", "")
        if found and f"{table}.{key}".lstrip(".") in ("features.hooks", "features.codex_hooks"):
            return value.strip() == "false"
    return False


def _update(command):
    path = hooks_path()
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            raise SystemExit(f"{path} isn't valid JSON. Fix or move it, then run the installer again.")
    before = json.dumps(data, sort_keys=True)

    hooks = data.setdefault("hooks", {})
    for event in list(hooks) + [e for e in EVENTS if e not in hooks]:
        ours = handler(event, command) if command and event in EVENTS else None
        groups = []
        for group in hooks.get(event, []):
            handlers = []
            for h in group.get("hooks", []):
                if MARKER not in h.get("command", ""):
                    handlers.append(h)
                elif ours:
                    handlers.append(ours)  # same place, so Codex keeps trusting it
                    ours = None
            if handlers:
                groups.append({**group, "hooks": handlers})
        if ours:
            groups.append({"hooks": [ours]})
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    if not hooks:
        del data["hooks"]

    if json.dumps(data, sort_keys=True) == before:
        return False
    if path.exists():
        shutil.copy2(path, str(path) + ".codexalgia.bak")
        if not data:
            path.unlink()  # it only held our hooks
            return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True
