import json
import os

from codexalgia.hook import EVENTS
from codexalgia.install import codex_hooks
from tests.support import IsolatedTestCase

COMMAND = 'python3 "/data/codexalgia.pyz" hook'
FOREIGN = {"type": "command", "command": "say done"}


class CodexHooksTest(IsolatedTestCase):
    def write(self, data):
        path = codex_hooks.hooks_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def read(self):
        return json.loads(codex_hooks.hooks_path().read_text())

    def commands(self, event):
        return [h["command"] for g in self.read()["hooks"].get(event, []) for h in g["hooks"]]

    def test_registers_every_event_without_matchers(self):
        codex_hooks.install(COMMAND)
        hooks = self.read()["hooks"]
        self.assertEqual(set(hooks), set(EVENTS))
        self.assertEqual(hooks["Stop"], [{"hooks": [{"type": "command", "command": COMMAND, "timeout": 5}]}])

    def test_short_events_stay_within_codex_limit(self):
        codex_hooks.install(COMMAND)
        for event in ("SessionEnd", "Interrupt"):
            self.assertEqual(self.read()["hooks"][event][0]["hooks"][0]["timeout"], 3)

    def test_only_known_top_level_keys(self):
        # Codex rejects the whole file if it has keys other than "description" and "hooks".
        self.write({"description": "mine"})
        codex_hooks.install(COMMAND)
        self.assertEqual(set(self.read()), {"description", "hooks"})

    def test_keeps_other_hooks(self):
        self.write({"hooks": {"Stop": [{"hooks": [FOREIGN]}]}})
        codex_hooks.install(COMMAND)
        self.assertEqual(self.commands("Stop"), ["say done", COMMAND])

    def test_reinstall_changes_nothing(self):
        self.assertTrue(codex_hooks.install(COMMAND))
        before = codex_hooks.hooks_path().read_text()
        self.assertFalse(codex_hooks.install(COMMAND))
        self.assertEqual(codex_hooks.hooks_path().read_text(), before)

    def test_reinstall_keeps_positions(self):
        # Codex remembers trust per position, so neither our hook nor the user's may move.
        codex_hooks.install(COMMAND)
        data = self.read()
        data["hooks"]["Stop"].append({"hooks": [FOREIGN]})
        self.write(data)
        self.assertTrue(codex_hooks.install('python3 "/new/codexalgia.pyz" hook'))
        self.assertEqual(self.commands("Stop"), ['python3 "/new/codexalgia.pyz" hook', "say done"])

    def test_duplicates_are_removed(self):
        self.write({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": COMMAND}]}] * 2}})
        codex_hooks.install(COMMAND)
        self.assertEqual(self.commands("Stop"), [COMMAND])

    def test_uninstall_removes_only_ours(self):
        self.write({"hooks": {"Stop": [{"hooks": [FOREIGN]}]}})
        codex_hooks.install(COMMAND)
        codex_hooks.uninstall()
        self.assertEqual(self.read(), {"hooks": {"Stop": [{"hooks": [FOREIGN]}]}})
        self.assertTrue(os.path.exists(str(codex_hooks.hooks_path()) + ".codexalgia.bak"))

    def test_uninstall_removes_a_file_that_only_held_ours(self):
        codex_hooks.install(COMMAND)
        codex_hooks.uninstall()
        self.assertFalse(codex_hooks.hooks_path().exists())
        codex_hooks.uninstall()  # nothing to do, and no file is created
        self.assertFalse(codex_hooks.hooks_path().exists())

    def test_invalid_json_stops_with_a_message(self):
        codex_hooks.hooks_path().parent.mkdir(parents=True)
        codex_hooks.hooks_path().write_text("{ not json")
        with self.assertRaises(SystemExit):
            codex_hooks.install(COMMAND)
        self.assertEqual(codex_hooks.hooks_path().read_text(), "{ not json")

    def test_codex_home_is_respected(self):
        os.environ["CODEX_HOME"] = os.path.join(self.home, "elsewhere")
        codex_hooks.install(COMMAND)
        self.assertTrue(os.path.isfile(os.path.join(self.home, "elsewhere", "hooks.json")))


class HooksDisabledTest(IsolatedTestCase):
    def config(self, text):
        path = codex_hooks.codex_home() / "config.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_default_is_enabled(self):
        self.assertFalse(codex_hooks.hooks_disabled())
        self.config('model = "gpt-5"\n[hooks]\nhooks = false\n')
        self.assertFalse(codex_hooks.hooks_disabled())

    def test_feature_flag_turns_hooks_off(self):
        for text in ("[features]\nhooks = false\n", "[ features ]\ncodex_hooks=false # old name\n", "features.hooks = false\n"):
            self.config(text)
            self.assertTrue(codex_hooks.hooks_disabled(), text)
        self.config("[features]\nhooks = true\n")
        self.assertFalse(codex_hooks.hooks_disabled())
