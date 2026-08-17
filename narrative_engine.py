"""Structured narrative director for Moonlight Villa.

This module plans relationship state, character belief updates, motif cooldowns,
and plot events. It deliberately returns structured decisions rather than
player-facing dialogue, so prose remains an authored rendering concern.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import random
import re


RELATIONSHIP_KEYS = ("trust", "rapport", "disclosure")
DIALOGUE_MODES = (
    "direct_response",
    "graceful_uncertainty",
    "dry_humor",
    "measured_question",
    "historical_context",
    "plot_observation",
)

MOTIF_PATTERNS = {
    "heartbeat": re.compile(r"心跳|脉搏", re.I),
    "historical_reference": re.compile(r"\b(?:1[0-9]{3}|20[0-9]{2})年\b|公元|世纪|百年前|千年前", re.I),
    "moonstone_ring": re.compile(r"月石戒指|戒面|戒指", re.I),
    "eye_change": re.compile(r"瞳孔|眼瞳", re.I),
    "clinical_observation": re.compile(r"医学角度|客观数据|生理反应|检测结果", re.I),
}

PRECISE_BIOMETRIC = re.compile(
    r"(?:心跳|脉搏|体温|振动频率).{0,12}\d+(?:\.\d+)?"
    r"(?:次|赫兹|hz|度|bpm)?|"
    r"\d+(?:\.\d+)?(?:次每分钟|次/分钟|赫兹|hz|bpm)",
    re.I,
)

UNSUPPORTED_LORE = re.compile(
    r"第三(?:个|位|人)|另(?:一|有)(?:个|位).{0,8}(?:住客|访客|居民|人)|"
    r"仍有.{0,8}(?:住客|访客|居民|人).{0,4}(?:住|留|藏)|"
    r"前世|转世|替身|旧爱|访客日志|七卷|同一只手|与你相似的访客",
    re.I,
)


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


@dataclass
class RelationshipState:
    trust: int = 15
    rapport: int = 10
    disclosure: int = 5

    def apply(self, delta: Dict[str, int]) -> None:
        for key in RELATIONSHIP_KEYS:
            if key in delta:
                setattr(self, key, clamp(getattr(self, key) + int(delta[key])))

    def satisfies(self, minimums: Dict[str, int]) -> bool:
        return all(getattr(self, key, 0) >= int(value) for key, value in minimums.items())


@dataclass
class Evidence:
    statement: str
    direction: int
    strength: float
    source_reliability: float
    turn: int

    @property
    def weighted_impact(self) -> float:
        direction = 1 if self.direction >= 0 else -1
        return direction * max(0.0, min(1.0, self.strength)) * max(
            0.0, min(1.0, self.source_reliability)
        )


@dataclass
class Belief:
    subject: str
    current_view: str
    confidence: float = 0.8
    rigidity: float = 0.65
    status: str = "stable"
    candidate_view: Optional[str] = None
    evidence: List[Evidence] = field(default_factory=list)
    updated_turn: int = 0


@dataclass
class NarrativeState:
    relationship: RelationshipState = field(default_factory=RelationshipState)
    beliefs: Dict[str, Belief] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)
    completed_events: List[str] = field(default_factory=list)
    recent_motifs: List[Dict[str, Any]] = field(default_factory=list)
    recent_modes: List[str] = field(default_factory=list)
    open_threads: List[str] = field(default_factory=list)
    known_facts: List[str] = field(default_factory=list)
    cain_scene: str = "garden"
    last_reward_turns: Dict[str, int] = field(default_factory=dict)
    turn: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship": asdict(self.relationship),
            "beliefs": {key: asdict(value) for key, value in self.beliefs.items()},
            "flags": list(self.flags),
            "completed_events": list(self.completed_events),
            "recent_motifs": list(self.recent_motifs),
            "recent_modes": list(self.recent_modes),
            "open_threads": list(self.open_threads),
            "known_facts": list(self.known_facts),
            "cain_scene": self.cain_scene,
            "last_reward_turns": dict(self.last_reward_turns),
            "turn": self.turn,
        }

    @classmethod
    def from_dict(cls, payload: Optional[Dict[str, Any]]) -> "NarrativeState":
        payload = payload or {}
        relationship = RelationshipState(**payload.get("relationship", {}))
        beliefs = {}
        for key, value in payload.get("beliefs", {}).items():
            belief_data = dict(value)
            evidence = [
                Evidence(**item) for item in belief_data.pop("evidence", [])
            ]
            beliefs[key] = Belief(evidence=evidence, **belief_data)
        return cls(
            relationship=relationship,
            beliefs=beliefs,
            flags=list(payload.get("flags", [])),
            completed_events=list(payload.get("completed_events", [])),
            recent_motifs=list(payload.get("recent_motifs", [])),
            recent_modes=list(payload.get("recent_modes", [])),
            open_threads=list(payload.get("open_threads", [])),
            known_facts=list(payload.get("known_facts", [])),
            cain_scene=str(payload.get("cain_scene", "garden")),
            last_reward_turns={
                str(key): int(value)
                for key, value in payload.get("last_reward_turns", {}).items()
            },
            turn=int(payload.get("turn", 0)),
        )


class NarrativeEngine:
    def __init__(
        self,
        events: Iterable[Dict[str, Any]],
        state: Optional[NarrativeState] = None,
        seed: Optional[int] = None,
        canon: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.events = list(events)
        self.canon = dict(canon or {})
        self.state = state or NarrativeState()
        valid_event_ids = {event["id"] for event in self.events}
        self.state.completed_events = [
            event_id for event_id in self.state.completed_events
            if event_id in valid_event_ids
        ]
        self.random = random.Random(seed)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        state: Optional[NarrativeState] = None,
        seed: Optional[int] = None,
    ) -> "NarrativeEngine":
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls(
            payload["events"],
            state=state,
            seed=seed,
            canon=payload.get("canon", {}),
        )

    def infer_intent(self, text: str) -> str:
        text = (text or "").strip()
        groups = (
            ("challenge", ("不对", "不信", "为什么", "凭什么", "证据", "隐瞒", "矛盾")),
            ("investigate", ("调查", "看看", "打开", "寻找", "线索", "房间", "检查", "验证", "观察")),
            ("share", ("我觉得", "我记得", "我经历", "我发现", "我注意到", "告诉你", "其实")),
            ("withdraw", ("算了", "不想说", "我要离开", "我想离开", "以后再说")),
            ("question", ("吗", "呢", "怎么", "什么", "哪里", "谁")),
        )
        for intent, words in groups:
            if any(word in text for word in words):
                return intent
        return "engage"

    def _reward_once(self, key: str, cooldown: int = 4) -> bool:
        last_turn = self.state.last_reward_turns.get(key, -999)
        if self.state.turn - last_turn < cooldown:
            return False
        self.state.last_reward_turns[key] = self.state.turn
        return True

    def relationship_delta_for(self, intent: str, text: str) -> Dict[str, int]:
        """Reward meaningful conduct, never mere message volume."""
        text = (text or "").strip()
        if intent == "challenge" and any(
            marker in text for marker in ("证据", "矛盾", "因为", "所以", "依据", "不成立")
        ):
            if self._reward_once("reasoned_challenge", cooldown=4):
                return {"trust": 1, "rapport": 2}
        if intent == "share" and any(
            marker in text for marker in ("我发现", "我注意到", "线索", "可以验证", "我记得")
        ):
            if self._reward_once("useful_disclosure", cooldown=5):
                return {"trust": 1, "rapport": 1}
        if intent == "withdraw":
            return {"rapport": -1}
        return {}

    def add_belief(
        self,
        subject: str,
        current_view: str,
        confidence: float = 0.8,
        rigidity: float = 0.65,
    ) -> Belief:
        belief = Belief(
            subject=subject,
            current_view=current_view,
            confidence=max(0.0, min(1.0, float(confidence))),
            rigidity=max(0.0, min(0.95, float(rigidity))),
            updated_turn=self.state.turn,
        )
        self.state.beliefs[subject] = belief
        return belief

    def add_belief_evidence(
        self,
        subject: str,
        statement: str,
        supports_current: bool,
        strength: float,
        source_reliability: float,
        candidate_view: Optional[str] = None,
    ) -> Belief:
        belief = self.state.beliefs.get(subject)
        if belief is None:
            raise KeyError(f"Unknown belief: {subject}")

        item = Evidence(
            statement=statement,
            direction=1 if supports_current else -1,
            strength=max(0.0, min(1.0, float(strength))),
            source_reliability=max(0.0, min(1.0, float(source_reliability))),
            turn=self.state.turn,
        )
        belief.evidence.append(item)
        belief.evidence = belief.evidence[-12:]
        if candidate_view and not supports_current:
            belief.candidate_view = candidate_view

        inertia = belief.rigidity
        belief.confidence = max(
            0.0,
            min(
                1.0,
                belief.confidence + item.weighted_impact * (1.0 - inertia),
            ),
        )
        belief.updated_turn = self.state.turn

        if belief.confidence >= 0.7:
            belief.status = "stable"
        elif belief.confidence >= 0.5:
            belief.status = "questioned"
        elif belief.confidence >= 0.3:
            belief.status = "suspended"
        elif belief.confidence >= 0.15:
            belief.status = "partially_revised"
        elif belief.candidate_view:
            belief.current_view = belief.candidate_view
            belief.candidate_view = None
            belief.confidence = 0.55
            belief.status = "revised"
        else:
            belief.status = "suspended"

        return belief

    def detect_motifs(self, text: str) -> List[str]:
        return [name for name, pattern in MOTIF_PATTERNS.items() if pattern.search(text or "")]

    def note_rendered_output(self, text: str) -> List[str]:
        motifs = self.detect_motifs(text)
        for motif in motifs:
            self.state.recent_motifs.append({"name": motif, "turn": self.state.turn})
        self.state.recent_motifs = self.state.recent_motifs[-24:]
        return self.quality_issues(text)

    def quality_issues(self, text: str) -> List[str]:
        issues: List[str] = []
        if PRECISE_BIOMETRIC.search(text or ""):
            issues.append("precise_biometric_measurement")
        if UNSUPPORTED_LORE.search(text or ""):
            issues.append("unsupported_third_party_lore")
        current = set(self.detect_motifs(text))
        blocked = set(self.blocked_motifs(window=3))
        if current & blocked:
            issues.append("repeated_recent_motif")
        return issues

    def blocked_motifs(self, window: int = 3) -> List[str]:
        threshold = max(0, self.state.turn - window)
        return sorted({
            item["name"]
            for item in self.state.recent_motifs
            if int(item.get("turn", -999)) >= threshold
        })

    def choose_mode(self) -> str:
        blocked = set(self.state.recent_modes[-2:])
        available = [mode for mode in DIALOGUE_MODES if mode not in blocked]
        mode = self.random.choice(available or list(DIALOGUE_MODES))
        self.state.recent_modes = (self.state.recent_modes + [mode])[-6:]
        return mode

    def event_is_eligible(
        self,
        event: Dict[str, Any],
        scene: str,
        intent: str,
        user_text: str,
    ) -> bool:
        trigger = event.get("trigger", {})
        if event["id"] in self.state.completed_events:
            return False
        if self.state.turn < int(trigger.get("min_turn", 0)):
            return False
        required_scene = trigger.get("scene")
        if required_scene and required_scene != scene:
            return False
        allowed_intents = trigger.get("intents", [])
        if allowed_intents and intent not in allowed_intents:
            return False
        keywords = trigger.get("keywords_any", [])
        if keywords and not any(word in user_text for word in keywords):
            return False
        if not self.state.relationship.satisfies(trigger.get("min_relationship", {})):
            return False
        flags = set(self.state.flags)
        if not set(trigger.get("requires_flags", [])).issubset(flags):
            return False
        if set(trigger.get("excludes_flags", [])) & flags:
            return False
        return True

    def select_event(
        self,
        scene: str,
        intent: str,
        user_text: str,
    ) -> Optional[Dict[str, Any]]:
        eligible = [
            event for event in self.events
            if self.event_is_eligible(event, scene, intent, user_text)
        ]
        if not eligible:
            return None
        eligible.sort(key=lambda event: (-int(event.get("priority", 0)), event["id"]))
        return eligible[0]

    def apply_event(self, event: Dict[str, Any]) -> None:
        if event["id"] not in self.state.completed_events:
            self.state.completed_events.append(event["id"])
        effects = event.get("effects", {})
        for flag in effects.get("add_flags", []):
            if flag not in self.state.flags:
                self.state.flags.append(flag)
        self.state.relationship.apply(effects.get("relationship_delta", {}))
        for fact in effects.get("reveal_facts", []):
            if fact not in self.state.known_facts:
                self.state.known_facts.append(fact)
        action = event.get("cain_action") or {}
        target_scene = action.get("target_scene")
        if target_scene:
            self.state.cain_scene = str(target_scene)
        for thread in effects.get("open_threads", []):
            if thread not in self.state.open_threads:
                self.state.open_threads.append(thread)
        for thread in effects.get("close_threads", []):
            if thread in self.state.open_threads:
                self.state.open_threads.remove(thread)

    def plan_turn(
        self,
        user_text: str,
        scene: str,
        intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.state.turn += 1
        resolved_intent = intent or self.infer_intent(user_text)
        relationship_delta = self.relationship_delta_for(resolved_intent, user_text)
        self.state.relationship.apply(relationship_delta)

        event = self.select_event(scene, resolved_intent, user_text)
        if event:
            self.apply_event(event)

        belief_updates = [
            {
                "subject": belief.subject,
                "current_view": belief.current_view,
                "candidate_view": belief.candidate_view,
                "confidence": belief.confidence,
                "rigidity": belief.rigidity,
                "status": belief.status,
                "recent_evidence": [
                    asdict(item) for item in belief.evidence[-3:]
                ],
            }
            for belief in self.state.beliefs.values()
        ]

        return {
            "turn": self.state.turn,
            "player_intent": resolved_intent,
            "response_intent": event.get("response_intent") if event else "respond_to_player",
            "dialogue_mode": self.choose_mode(),
            "relationship_delta": relationship_delta,
            "relationship_state": asdict(self.state.relationship),
            "belief_updates": belief_updates,
            "plot_event": {
                "id": event["id"],
                "summary": event["summary"],
                "line_id": event.get("line_id"),
            } if event else None,
            "avoid_motifs": self.blocked_motifs(window=3),
            "open_threads": list(self.state.open_threads),
            "known_facts": list(self.state.known_facts),
            "cain_action": dict(event.get("cain_action", {})) if event else None,
            "cain_scene": self.state.cain_scene,
            "state": self.state.to_dict(),
        }
