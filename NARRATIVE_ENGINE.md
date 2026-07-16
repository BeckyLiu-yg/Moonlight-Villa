# Narrative Director

This directory-level module adds a structured AI director beneath the existing
application. It does not generate player-facing dialogue. Instead, it decides
what the character understands, which belief changes, which plot event becomes
eligible, and which recent expressive motifs should be avoided.

## Files

- `narrative_engine.py`: state, event selection, belief revision, relationship
  dimensions, motif cooldowns, and output quality checks.
- `story_events.json`: configurable gothic-mystery event graph.
- `dialogue_contract.json`: JSON Schema for the director's turn decision.
- `tests/test_narrative_engine.py`: standard-library unit tests.

## Core state

The relationship is intentionally multi-dimensional:

- `trust`: willingness to rely on shared evidence.
- `rapport`: conversational alignment and familiarity.
- `disclosure`: readiness to reveal hidden information.

Beliefs are versioned as `previous_view -> revised_view` with evidence and a
confidence score. This lets a character remain composed while still changing
their understanding over a long-running story.

## Suggested integration

1. Restore `NarrativeState` from the save record.
2. Call `plan_turn(user_text, scene)` before rendering a response.
3. Pass the returned structured decision to an authored dialogue renderer.
4. After rendering, call `note_rendered_output(text)`.
5. If `quality_issues` is non-empty, select another authored line or rerender.
6. Persist `decision["state"]` with the normal save data.

Minimal example:

```python
from narrative_engine import NarrativeEngine, NarrativeState

state = NarrativeState.from_dict(saved_director_state)
engine = NarrativeEngine.from_file("story_events.json", state=state)
decision = engine.plan_turn(user_text, current_scene)

line_id = decision["plot_event"]["line_id"] if decision["plot_event"] else None
rendered_text = authored_renderer.render(line_id=line_id, context=decision)

issues = engine.note_rendered_output(rendered_text)
if issues:
    rendered_text = authored_renderer.render_alternative(
        line_id=line_id,
        avoid_motifs=decision["avoid_motifs"],
    )

save_director_state(engine.state.to_dict())
```

## Validation

Run from the repository root:

```bash
python -m unittest discover -s tests -p "test_narrative_engine.py"
```

The module uses only Python's standard library.
