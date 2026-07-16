"""Feature-flagged runtime wrapper for the structured narrative director."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import os

from narrative_engine import NarrativeEngine, NarrativeState


TRUE_VALUES = {"1", "true", "yes", "on"}


def director_enabled(value: Optional[str] = None) -> bool:
    raw = os.environ.get("NARRATIVE_DIRECTOR_ENABLED", "0") if value is None else value
    return str(raw).strip().lower() in TRUE_VALUES


class DirectorRuntime:
    def __init__(
        self,
        events_path: str | Path = "story_events.json",
        enabled: Optional[bool] = None,
        seed: Optional[int] = None,
    ) -> None:
        self.events_path = Path(events_path)
        self.enabled = director_enabled() if enabled is None else bool(enabled)
        self.seed = seed
        self._engines: Dict[str, NarrativeEngine] = {}

    def restore(
        self,
        session_id: str,
        saved_state: Optional[Dict[str, Any]] = None,
    ) -> NarrativeEngine:
        state = NarrativeState.from_dict(saved_state)
        engine = NarrativeEngine.from_file(
            self.events_path,
            state=state,
            seed=self.seed,
        )
        self._engines[session_id] = engine
        return engine

    def engine_for(self, session_id: str) -> NarrativeEngine:
        return self._engines.get(session_id) or self.restore(session_id)

    def before_response(
        self,
        session_id: str,
        user_text: str,
        scene: str,
        saved_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "decision": None, "state": saved_state}

        engine = (
            self.restore(session_id, saved_state)
            if saved_state is not None and session_id not in self._engines
            else self.engine_for(session_id)
        )
        decision = engine.plan_turn(user_text, scene)
        return {
            "enabled": True,
            "decision": decision,
            "state": engine.state.to_dict(),
        }

    def after_response(self, session_id: str, rendered_text: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "quality_issues": [], "state": None}

        engine = self.engine_for(session_id)
        issues = engine.note_rendered_output(rendered_text)
        return {
            "enabled": True,
            "quality_issues": issues,
            "state": engine.state.to_dict(),
        }

    def state_for(self, session_id: str) -> Optional[Dict[str, Any]]:
        engine = self._engines.get(session_id)
        return engine.state.to_dict() if engine else None
