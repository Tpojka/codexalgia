"""OS-specific install steps: how to call Python, and how Chrome finds the native host."""
import json
import os
import shlex
import sys
from pathlib import Path

from .. import EXTENSION_ID, HOST_NAME, paths

LABELS = {"darwin": "macOS", "linux": "Ubuntu/Linux", "win32": "Windows"}


def label():
    return LABELS.get(sys.platform, sys.platform)


def python_command():
    """How hooks start Python. On Windows `python` may be the Store stub, so use this interpreter's path."""
    if sys.platform == "win32":
        return f'"{Path(sys.executable).as_posix()}"'  # forward slashes work in Git Bash and cmd
    return "python3"


def write_host_launcher(app):
    """Chrome starts native hosts as executables, so wrap `python codexalgia.pyz host` in a script."""
    if sys.platform == "win32":
        launcher = paths.data_dir() / "codexalgia-host.bat"
        with open(launcher, "w", newline="\r\n") as f:
            f.write(f'@echo off\n"{sys.executable}" "{app}" host %*\n')
    else:
        launcher = paths.data_dir() / "codexalgia-host"
        launcher.write_text(f'#!/bin/sh\nexec python3 {shlex.quote(str(app))} host "$@"\n')
        launcher.chmod(0o755)
    return launcher


def register_host(launcher):
    """Tell Chrome where the native host is. Returns the manifest paths written."""
    manifest = json.dumps(
        {
            "name": HOST_NAME,
            "description": "Codexalgia: Codex status for Chrome",
            "path": str(launcher),
            "type": "stdio",
            "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"],
        },
        indent=2,
    ) + "\n"

    if sys.platform == "win32":
        import winreg

        target = manifest_path()
        target.write_text(manifest)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _windows_key()) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(target))
        return [target]

    written = []
    for directory in _manifest_dirs():
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{HOST_NAME}.json"
        target.write_text(manifest)
        written.append(target)
    return written


def manifest_path():
    """The native host manifest Chrome reads (the Chrome one, on Linux)."""
    if sys.platform == "win32":
        return paths.data_dir() / f"{HOST_NAME}.json"
    return _manifest_dirs()[0] / f"{HOST_NAME}.json"


def unregister_host():
    if sys.platform == "win32":
        import winreg

        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _windows_key())
        except FileNotFoundError:
            pass
        return
    for directory in _manifest_dirs(all_browsers=True):
        (directory / f"{HOST_NAME}.json").unlink(missing_ok=True)


def _windows_key():
    return rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"


def _manifest_dirs(all_browsers=False):
    if sys.platform == "darwin":
        return [Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts"]
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    # Chrome always; Chromium only when it has a profile (Snap/Flatpak browsers can't start native hosts).
    browsers = ["google-chrome", "chromium"]
    return [
        config / b / "NativeMessagingHosts"
        for b in browsers
        if all_browsers or b == "google-chrome" or (config / b).is_dir()
    ]
