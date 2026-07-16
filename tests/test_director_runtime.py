import os
import unittest
from pathlib import Path
from unittest.mock import patch

from director_runtime import DirectorRuntime, director_enabled


EVENTS_PATH = Path(__file__).resolve().parents[1] / "story_events.json"


class DirectorRuntimeTests(unittest.TestCase):
    def test_flag_defaults_off(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(director_enabled())

    def test_flag_accepts_common_true_values(self):
        for value in ("1", "true", "YES", "on"):
            self.assertTrue(director_enabled(value))

    def test_disabled_runtime_is_noop(self):
        runtime = DirectorRuntime(EVENTS_PATH, enabled=False)
        result = runtime.before_response("s1", "测试", "garden")
        self.assertFalse(result["enabled"])
        self.assertIsNone(result["decision"])

    def test_enabled_runtime_plans_and_persists_state(self):
        runtime = DirectorRuntime(EVENTS_PATH, enabled=True, seed=1)
        before = runtime.before_response("s1", "查看这里", "garden")
        self.assertTrue(before["enabled"])
        self.assertEqual(
            before["decision"]["plot_event"]["id"],
            "rift_recognition",
        )

        after = runtime.after_response("s1", "文本提到了月石戒指。")
        motif_names = [item["name"] for item in after["state"]["recent_motifs"]]
        self.assertIn("moonstone_ring", motif_names)

    def test_saved_state_can_be_restored(self):
        first = DirectorRuntime(EVENTS_PATH, enabled=True, seed=2)
        result = first.before_response("s1", "调查线索", "garden")

        second = DirectorRuntime(EVENTS_PATH, enabled=True, seed=2)
        restored = second.before_response(
            "s1",
            "继续",
            "garden",
            saved_state=result["state"],
        )
        self.assertEqual(restored["decision"]["turn"], 2)


if __name__ == "__main__":
    unittest.main()
