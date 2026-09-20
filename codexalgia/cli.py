"""Entry point of the installed codexalgia.pyz: `hook` (called by Codex), `remind` (started by the hook)
or `host` (started by Chrome)."""
import sys


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "hook":
        from . import hook

        hook.main()
    elif command == "remind":
        from . import hook

        try:
            hook.remind(*sys.argv[2:6])
        except Exception:
            pass  # runs detached, with nobody to report to
    elif command == "host":
        from . import host

        host.main()
    else:
        sys.exit("usage: codexalgia.pyz hook|remind|host")
