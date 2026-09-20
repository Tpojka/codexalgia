import base64
import hashlib
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from unittest import mock

from codexalgia import EXTENSION_ID, config, install, paths
from codexalgia.install import codex_hooks, system
from tests.support import IsolatedTestCase
from tests.test_host import read_message


class InstallTest(IsolatedTestCase):
    def run_installer(self, *args):
        with redirect_stdout(io.StringIO()) as out:
            install.main(list(args))
        return out.getvalue()

    def hook_commands(self):
        hooks = json.loads(codex_hooks.hooks_path().read_text())["hooks"]
        return {h["command"] for groups in hooks.values() for g in groups for h in g["hooks"]}

    def test_exit_installs_nothing(self):
        self.assertIn("Nothing installed", self.run_installer("3"))
        self.assertFalse(os.path.exists(self.data))
        self.assertFalse(codex_hooks.hooks_path().exists())

    def test_install_is_self_contained_and_works(self):
        self.addCleanup(system.unregister_host)
        out = self.run_installer("2")

        self.assertTrue(paths.app_file().is_file())
        self.assertTrue((paths.extension_dir() / "manifest.json").is_file())
        self.assertTrue(paths.icon("hip-ok").is_file())
        self.assertTrue(paths.icon("hip-pain").is_file())
        self.assertTrue(config.load()["notifications"])
        self.assertEqual(len(self.hook_commands()), 1)
        self.assertIn("/hooks", out)

        # The installed app runs on its own: a hook event is recorded as session state, with no output.
        payload = json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "s1"})
        run = subprocess.run(
            [sys.executable, str(paths.app_file()), "hook"], input=payload.encode(), capture_output=True, cwd=self.home
        )
        self.assertEqual((run.returncode, run.stdout), (0, b""))
        self.assertEqual((paths.sessions_dir() / "s1").read_text(), "busy")

    def test_reinstall_keeps_hooks_trusted(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("1")
        before = codex_hooks.hooks_path().read_text()
        out = self.run_installer("2", "--no-sound")
        self.assertIn("unchanged", out)
        self.assertEqual(codex_hooks.hooks_path().read_text(), before)

    def test_warns_when_codex_hooks_are_turned_off(self):
        self.addCleanup(system.unregister_host)
        codex_hooks.codex_home().mkdir()
        (codex_hooks.codex_home() / "config.toml").write_text("[features]\nhooks = false\n")
        self.assertIn("Hooks are turned off", self.run_installer("1"))

    def test_menu_asks_about_sound_only_for_the_notifier(self):
        self.addCleanup(system.unregister_host)
        with mock.patch("builtins.input", side_effect=["2", "n"]):
            out = self.run_installer()
        self.assertIn("2) Chrome extension + OS notifier", out)
        self.assertEqual(config.load(), {"notifications": True, "sound": False})

        with mock.patch("builtins.input", side_effect=["1"]) as ask:
            self.run_installer()
        self.assertEqual(ask.call_count, 1)

    def test_sound_flag_without_prompting(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("2", "--no-sound")
        self.assertFalse(config.load()["sound"])
        self.run_installer("2")
        self.assertTrue(config.load()["sound"])

    def test_set_changes_installed_setting(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("2")
        self.assertIn("Sound off", self.run_installer("set", "sound", "off"))
        self.assertEqual(config.load(), {"notifications": True, "sound": False})
        self.run_installer("set", "notifications", "off")
        self.assertFalse(config.load()["notifications"])

    def test_set_rejects_bad_input_and_missing_install(self):
        with self.assertRaises(SystemExit):
            self.run_installer("set", "sound", "on")  # not installed yet
        self.run_installer("3")
        with self.assertRaises(SystemExit):
            self.run_installer("set", "volume", "on")

    def test_option_1_turns_notifier_off(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("2")
        self.run_installer("1")
        self.assertFalse(config.load()["notifications"])

    def test_uninstall_removes_everything(self):
        self.run_installer("1")
        self.run_installer("uninstall")
        self.assertFalse(os.path.exists(self.data))
        self.assertFalse(codex_hooks.hooks_path().exists())

    def test_manifest_key_gives_the_extension_id(self):
        # Chrome derives the ID from the key: the first 32 hex digits of its SHA-256, mapped 0-f to a-p.
        with open(os.path.join(install.REPO, "extension", "manifest.json")) as f:
            key = base64.b64decode(json.load(f)["key"])
        digest = hashlib.sha256(key).hexdigest()[:32]
        self.assertEqual("".join(chr(ord("a") + int(c, 16)) for c in digest), EXTENSION_ID)

    def test_chrome_can_start_the_registered_host(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("1")
        manifest = json.loads(system.manifest_path().read_text())
        self.assertEqual(manifest["allowed_origins"], [f"chrome-extension://{EXTENSION_ID}/"])

        # Chrome runs the manifest's path with the extension origin as the argument.
        proc = subprocess.Popen([manifest["path"], "chrome-extension://test/"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            self.assertEqual(read_message(proc.stdout)["state"], "ready")
            proc.stdin.close()
            self.assertEqual(proc.wait(timeout=10), 0)
        finally:
            proc.kill()
            proc.stdout.close()
