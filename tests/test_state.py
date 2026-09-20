import os
import time

from codexalgia import paths, state
from tests.support import IsolatedTestCase


class StateTest(IsolatedTestCase):
    def test_no_sessions_is_ready(self):
        self.assertEqual(state.summary(), {"state": "ready", "busy": 0, "total": 0})

    def test_any_busy_session_makes_it_busy(self):
        state.set_state("a", state.BUSY)
        state.set_state("b", state.READY)
        self.assertEqual(state.summary(), {"state": "busy", "busy": 1, "total": 2})

    def test_clear_removes_session(self):
        state.set_state("a", state.BUSY)
        state.clear("a")
        state.clear("never-existed")
        self.assertEqual(state.summary()["total"], 0)

    def test_stale_busy_session_counts_as_ready(self):
        state.set_state("a", state.BUSY)
        later = time.time() + state.BUSY_STALE_SECONDS + 1
        self.assertEqual(state.summary(now=later), {"state": "ready", "busy": 0, "total": 1})

    def test_waiting_session_is_busy_until_the_grace_period_ends(self):
        state.set_state("a", state.WAITING)
        self.assertEqual(state.summary()["state"], "busy")
        later = time.time() + state.APPROVAL_GRACE_SECONDS + 1
        self.assertEqual(state.summary(now=later), {"state": "ready", "busy": 0, "total": 1})

    def test_current_reports_state_and_change(self):
        self.assertIsNone(state.current("a"))
        state.set_state("a", state.WAITING)
        value, stamp = state.current("a")
        self.assertEqual(value, "waiting")
        self.assertIsInstance(stamp, int)

    def test_abandoned_session_is_ignored(self):
        state.set_state("a", state.READY)
        later = time.time() + state.SESSION_STALE_SECONDS + 1
        self.assertEqual(state.summary(now=later)["total"], 0)

    def test_session_id_cannot_escape_the_sessions_dir(self):
        state.set_state("../../evil", state.BUSY)
        self.assertEqual(os.listdir(paths.sessions_dir()), ["evil"])

    def test_partial_writes_are_ignored(self):
        paths.sessions_dir().mkdir(parents=True)
        (paths.sessions_dir() / "a.tmp").write_text("busy")
        self.assertEqual(state.summary()["total"], 0)
