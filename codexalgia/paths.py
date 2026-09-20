"""Where the installed app, session state and config live: a per-user data directory, never the repository."""
import os
import sys
from pathlib import Path


def data_dir():
    override = os.environ.get("CODEXALGIA_HOME")
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Codexalgia"
    if sys.platform == "win32":
        return Path(os.environ["LOCALAPPDATA"]) / "Codexalgia"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "codexalgia"


def app_file():
    return data_dir() / "codexalgia.pyz"


def extension_dir():
    return data_dir() / "extension"


def sessions_dir():
    return data_dir() / "sessions"


def config_file():
    return data_dir() / "config.json"


def icon(name):
    return extension_dir() / "icons" / f"{name}-128.png"
