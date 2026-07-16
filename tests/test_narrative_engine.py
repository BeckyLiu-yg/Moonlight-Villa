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

    def test_weak_correction_does_not_immediately_replace_belief(self):
        engine = NarrativeEngine.from_file(EVENTS_PATH, seed=3)
        engine.plan_turn("这个判断可能不对。", "library")
        belief = engine.add_belief(
            subject="villa_map",
            current_view="The map is complete.",
            confidence=0.85,
            rigidity=0.7,
        )
        engine.add_belief_evidence(
            subject="villa_map",
            statement="A visitor questions the map.",
            supports_current=False,
            strength=0.25,
            source_reliability=0.5,
            candidate_view="The map may omit a room.",
        )

        self.assertEqual(belief.current_view, "The map is complete.")
        self.assertIn(belief.status, {"stable", "questioned"})

    def test_repeated_strong_evidence_can_eventually_revise_belief(self):
        engine = NarrativeEngine.from_file(EVENTS_PATH, seed=7)
        engine.plan_turn("继续核对。", "library")
        engine.add_belief(
            subject="villa_map",
            current_view="The map is complete.",
            confidence=0.75,
            rigidity=0.35,
        )
        for index in range(4):
            belief = engine.add_belief_evidence(
                subject="villa_map",
                statement=f"Independent contradiction {index}",
                supports_current=False,
                strength=0.9,
                source_reliability=0.9,
                candidate_view="The map may omit a room.",
            )

        self.assertEqual(belief.current_view, "The map may omit a room.")
        self.assertEqual(belief.status, "revised")

        restored = NarrativeState.from_dict(engine.state.to_dict())
        self.assertEqual(
            restored.beliefs["villa_map"].current_view,
            "The map may omit a room.",
        )
        self.assertEqual(len(restored.beliefs["villa_map"].evidence), 4)

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
