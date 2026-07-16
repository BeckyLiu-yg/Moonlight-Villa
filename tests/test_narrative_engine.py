import json
import tempfile
import unittest
from pathlib import Path

from narrative_engine import NarrativeEngine, NarrativeState


EVENTS_PATH = Path(__file__).resolve().parents[1] / "story_events.json"


class NarrativeEngineTests(unittest.TestCase):
    def test_first_turn_opens_central_mystery(self):
        engine = NarrativeEngine.from_file(EVENTS_PATH, seed=1)
        decision = engine.plan_turn("先看看这里。", "garden")

        self.assertEqual(decision["plot_event"]["id"], "rift_recognition")
        self.assertIn("why_the_rift_recognizes_the_visitor", decision["open_threads"])
        self.assertGreaterEqual(decision["relationship_state"]["disclosure"], 6)

    def test_events_respect_prerequisites_and_turns(self):
        engine = NarrativeEngine.from_file(EVENTS_PATH, seed=2)
        event_ids = []
        for turn in range(1, 8):
            decision = engine.plan_turn("继续调查线索。", "garden")
            if decision["plot_event"]:
                event_ids.append(decision["plot_event"]["id"])

        self.assertEqual(
            event_ids,
            ["rift_recognition", "sundial_echo", "sixth_room_trace"],
        )

    def test_belief_revision_survives_serialization(self):
        engine = NarrativeEngine.from_file(EVENTS_PATH, seed=3)
        engine.plan_turn("这个判断可能不对。", "library")
        engine.record_belief_revision(
            subject="villa_map",
            previous_view="The map is complete.",
            revised_view="The map may omit a room.",
            evidence=["mirror_trace"],
            confidence=0.7,
        )

        restored = NarrativeState.from_dict(engine.state.to_dict())
        self.assertEqual(
            restored.beliefs["villa_map"].revised_view,
            "The map may omit a room.",
        )
        self.assertEqual(restored.beliefs["villa_map"].evidence, ["mirror_trace"])

    def test_motif_cooldown_and_quality_check(self):
        engine = NarrativeEngine.from_file(EVENTS_PATH, seed=4)
        engine.plan_turn("测试。", "garden")
        engine.note_rendered_output("文本提到了月石戒指。")
        engine.plan_turn("继续。", "garden")

        self.assertIn("moonstone_ring", engine.blocked_motifs())
        issues = engine.quality_issues("心跳达到每分钟120次。")
        self.assertIn("precise_biometric_measurement", issues)

    def test_dialogue_modes_do_not_repeat_immediately(self):
        engine = NarrativeEngine.from_file(EVENTS_PATH, seed=5)
        modes = [
            engine.plan_turn("继续。", "garden")["dialogue_mode"]
            for _ in range(6)
        ]
        for index in range(2, len(modes)):
            self.assertNotIn(modes[index], modes[index - 2:index])


if __name__ == "__main__":
    unittest.main()
