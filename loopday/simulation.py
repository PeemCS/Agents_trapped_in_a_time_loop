"""LOOPDAY's deterministic town and its recorded agent decisions."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field, replace
import json
import re

from .appointments import NOTICE_LOCATIONS, lesson_notice, notice_text
from .memory import Memory
from .provenance import restore_names
from .relationships import Relationship, spoken_facts
from .replay import changed_event, comparable, digest, match, utterance_intent
from .town import (
    ANCHORS, APPOINTMENTS, CAST, OPPORTUNITIES, PLACES, REJOIN_TICKS, RITA_FACTS,
    ROADS, STARTS, TURNS, clock, next_stop, schedule_at,
)


CHECKPOINT_VERSION = 2
MAX_EXCHANGES = 2
_SCENE_WINDOW = 10
_BELIEF_TEXT = "Physical changes can disappear at dawn. The repeated broadcast alone did not show that."
_GUARDED_PHRASES = ("kill myself", "hurt myself", "take my own life")
_BAND_STATUSES = frozenset({"verified", "partially_verified", "fallback", "unconfigured", "budget", "circuit_open"})
_RECEIPT_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")


@dataclass(frozen=True)
class Choice:
    action: str
    reason: str
    line: str = ""
    prediction: str = ""
    support: tuple[str, ...] = ()
    hypothesis: str = ""
    predicted: str = ""

    @classmethod
    def read(cls, raw: str, actions: list[str]) -> Choice | None:
        try:
            item = json.loads(raw)
        except (TypeError, ValueError):
            return None
        if not isinstance(item, dict) or item.get("action") not in actions:
            return None
        optional = ("line", "prediction", "hypothesis", "predicted")
        fields = {key: "" if item.get(key) is None else item[key] for key in optional}
        fields["reason"] = item.get("reason", "")
        if any(not isinstance(value, str) for value in fields.values()):
            return None
        support = item.get("support", [])
        if not isinstance(support, list) or any(not isinstance(value, str) for value in support):
            return None
        return cls(
            action=item["action"],
            support=tuple(dict.fromkeys(support[:4])),
            **{field: value.strip()[:380] for field, value in fields.items()},
        )


class FixtureDirector:
    """Deterministic actor choices used for test and preview footage."""

    mode = "fixture"

    def __init__(self, *, choose_community: bool = False) -> None:
        self.choose_community = choose_community

    def is_live(self, actor: str) -> bool:
        return False

    def choose(self, actor: str, obs: dict) -> str:
        tick, location, options = obs["tick"], obs["location_id"], obs["actions"]
        memory = obs.get("memories", [])
        learned = bool(memory)
        support = []
        action, line, prediction, hypothesis, predicted = "wait", "", "", "", ""
        reason = ""
        if obs["exchange"]:
            if actor == "phil" and "talk:ned" in options and tick == 3:
                action, line = "talk:ned", "I’ll read the fine print after my socks thaw."
        elif actor == "phil":
            if tick == 0:
                action = "inspect_pencil"
            elif tick == 1:
                action = "move:main_st"
                puddle = next((row for row in memory if "puddle" in row["text"]), None)
                test = next((row for row in obs["current_evidence"]
                             if row["type"] == "test_result" and row.get("state") == "whole"), None)
                if puddle and test:
                    action = "avoid_puddle"
                    support = [test["event_id"], puddle["event_id"]]
                    reason = "The pencil was whole again. What happened at this corner might repeat too."
            elif tick == 3 and location == "main_st":
                action = "talk:ned"
                line = "Any chance you sell insurance against wet socks?"
            elif tick == 4 and learned:
                action = "move:piano_teacher"
            elif tick == 6 and location == "main_st":
                action = "move:knob"
            elif tick == 10 and location == "piano_teacher" and learned:
                action = "move:main_st"
            elif tick == 11 and "help:kid_tree" in options and learned:
                action = "help:kid_tree"
            elif tick == 11 and location == "knob":
                action = "move:main_st"
            elif tick == 12:
                action = "move:piano_teacher" if learned else "move:inn"
            elif "practice_piano" in options:
                action = "practice_piano"
            elif tick == 18 and location == "piano_teacher":
                action = "move:hotel"
            elif tick == 24 and location == "hotel":
                action = "help_guests"
            elif tick == 26 and location == "hotel":
                action = "play_piano"
            elif tick == 30 and location == "hotel":
                action, line = "invite_rita", "Would you stay for one more song?"
            elif tick == 35 and location == "inn":
                action = "break_pencil"
                prediction = "If the room resets too, this pencil will be whole at six."
                hypothesis, predicted = "room_resets", "whole"
        elif actor == "rita":
            if "accept_invitation" in options and not self.choose_community:
                action, line = "accept_invitation", "One more song sounds good."
            elif "decline_invitation" in options:
                action, line = "decline_invitation", "You go on. I’m going to call the station."
            elif tick == 12 and location == "main_st":
                action = "move:diner"
            elif tick == 18 and location in {"knob", "diner"}:
                action = "move:hotel"
        elif actor in {"larry", "ned"}:
            if actor == "ned" and tick == 3 and "talk:phil" in options:
                action, line = "talk:phil", "Phil! I’ve got a policy for weather like this."
            elif tick == 12 and location == "main_st":
                action = "move:diner"
            elif tick == 18 and location in {"knob", "diner"}:
                action = "move:hotel"
            elif tick == 30 and "credit_phil" in options:
                action = "credit_phil"
        if action not in options:
            action, line, prediction, support = "wait", "", "", []
            hypothesis, predicted, reason = "", "", ""
        reason = reason or f"Fixture choice: {action}."
        return json.dumps(asdict(Choice(action, reason, line, prediction, tuple(support), hypothesis, predicted)))


@dataclass
class DayState:
    positions: dict[str, str] = field(default_factory=lambda: dict(STARTS))
    seen: dict[str, list[int]] = field(default_factory=lambda: {actor: [] for actor in CAST})
    learned_facts: dict[str, dict[str, dict]] = field(default_factory=lambda: {actor: {} for actor in CAST})
    opportunities: dict[str, str] = field(default_factory=lambda: {event: "pending" for event in OPPORTUNITIES})
    modes: dict[str, str] = field(default_factory=lambda: {actor: "scripted" for actor in CAST if actor != "phil"})
    divergence_start: dict[str, int] = field(default_factory=dict)
    disclosed_rita_facts: list[str] = field(default_factory=list)
    appraised: list[str] = field(default_factory=list)
    moved: list[str] = field(default_factory=list)
    known_phil_facts: list[str] = field(default_factory=list)
    credits: dict[str, str] = field(default_factory=dict)
    relationship: Relationship = field(default_factory=Relationship)
    rita_evidence: list[str] = field(default_factory=list)
    public_help: list[str] = field(default_factory=list)
    pencil: str = "whole"
    invitation: bool = False
    invited: bool = False
    accepted: bool = False
    invitation_event_id: str | None = None
    reply_event_id: str | None = None
    helped: bool = False
    performed: bool = False
    practiced: bool = False
    appointment_event: str | None = None
    bought_policy: bool = False
    shown_policy: bool = False
    checked_station: bool = False
    filmed_sources: list[str] = field(default_factory=list)
    recognition: float = 0.0
    recognition_event: str | None = None


class Simulation:
    def __init__(
        self, director, *, keep_memory: bool = True, lesson_tick: int = 16,
        seed: int = 7, reset_pencil: bool = True, transport=None,
    ) -> None:
        self.director = director
        self.transport = transport
        self.keep_memory = keep_memory
        self.lesson_tick = lesson_tick
        self.seed = seed
        self.reset_pencil = reset_pencil
        self.events: list[dict] = []
        self.memory = Memory()
        self.canonical: dict[tuple[str, int, int], dict] = {}
        self.loop = 0
        self.tick = 0
        self.completed_loops = 0
        self.next_tick = 0
        self.day_ticks: int | None = None
        self.piano_level = 0
        self.ending = "repeat"
        self.ending_reason: str | None = None
        self.live_decisions = 0
        self.replayed_decisions = 0
        self.pencil_experiment: dict | None = None
        self.first_realization: str | None = None
        self.withheld_memory: frozenset[str] = frozenset()
        self.day = DayState()
        self._log_digest = digest([])
        self._canonical_digest = digest([])
        self._phil_decisions: list[int] = []
        self._pending_tick = False
        self.mood = 0.10
        self.arousal = 0.40
        self.quiet_days = 0
        self.goals = [CAST["phil"]["goal"]]
        self.action_values: dict[str, dict] = {}

    @property
    def positions(self) -> dict[str, str]:
        return self.day.positions

    @property
    def rita_evidence(self) -> list[str]:
        return self.day.rita_evidence

    @rita_evidence.setter
    def rita_evidence(self, value: list[str]) -> None:
        self.day.rita_evidence = value

    @property
    def invitation(self) -> bool:
        return self.day.invitation

    @invitation.setter
    def invitation(self, value: bool) -> None:
        self.day.invitation = value

    def log(self, kind: str, text: str, *, recipients: tuple[str, ...] = (), **fields) -> dict:
        index = len(self.events)
        event = {
            "id": f"e{index:05d}", "order": index, "ts_order": index,
            "loop": self.loop, "tick": self.tick, "time": clock(self.tick),
            "date": "February 3" if kind == "day_two" else "February 2",
            "type": kind, "text": text, **fields,
        }
        if recipients and self.transport is not None:
            event["transport"] = self._dispatch(event, recipients)
        self.events.append(event)
        self._log_digest = digest([self._log_digest, event])
        return event

    def _dispatch(self, event: dict, recipients: tuple[str, ...]) -> dict:
        safe_fields = ("id", "loop", "tick", "type", "actor", "to", "location", "text")
        envelope = {key: event[key] for key in safe_fields if key in event}
        fallback = {"transport": "local", "status": "fallback", "receipt": None, "verified_recipients": []}
        try:
            summary = self.transport.deliver(envelope, recipients)
        except Exception:
            return fallback
        if not isinstance(summary, dict):
            return fallback
        receipt = summary.get("receipt")
        if not isinstance(receipt, str) or not _RECEIPT_ID.fullmatch(receipt):
            receipt = None
        status = summary.get("status")
        if not isinstance(status, str) or status not in _BAND_STATUSES:
            return fallback
        claimed = summary.get("verified_recipients", [])
        verified = [actor for actor in recipients if actor in claimed] if receipt and isinstance(claimed, list) else []
        if status not in {"verified", "partially_verified"}:
            verified = []
        elif not verified:
            status = "fallback"
        return {"transport": "band" if verified else "local", "status": status,
                "receipt": receipt, "verified_recipients": verified}

    def _witnesses(self, location: str) -> list[str]:
        return [actor for actor, place in self.positions.items() if place == location]

    def _memory_event(self, record: dict, *, operation: str | None = None, **details) -> None:
        change = operation or record["operation"]
        self.log("memory", f"Phil's memory changes: {change}.", actor="phil",
                 location=record.get("location"), op=change, evidence=record["event_id"],
                 memory_id=record.get("id"), memory_kind=record["kind"], witnesses=["phil"], **details)

    def _recognize(self, event: dict) -> None:
        strength, source = self.memory.deja_vu(self.loop, event["text"], self.withheld_memory)
        if strength <= self.day.recognition:
            return
        self.day.recognition, self.day.recognition_event = strength, source
        sensation = ("A jolt of recognition." if strength >= 0.9 else "Something feels oddly familiar.")
        self.log("deja_vu", sensation, actor="phil", location=self.positions["phil"],
                 value=strength, trigger=event["id"], source_event=source, witnesses=["phil"])

    def observe(self, kind: str, text: str, actor: str, **fields) -> dict:
        return self.publish(kind, text, self.positions[actor], actor=actor, **fields)

    def publish(self, kind: str, text: str, location: str, **fields) -> dict:
        witnesses = fields.pop("witnesses", self._witnesses(location))
        recipient = fields.get("to")
        addressed = kind in {"utterance", "gossip", "invitation", "reply"} and recipient in witnesses
        event = self.log(kind, text, location=location, witnesses=witnesses,
                         recipients=(recipient,) if addressed else (), **fields)
        for actor in witnesses:
            self.day.seen[actor].append(event["order"])
        if "phil" in witnesses and kind not in {"position", "gossip"}:
            if kind in {"anchor", "utterance"}:
                self._recognize(event)
            if kind != "prediction":
                importance = 0.9 if kind in {"pencil", "test_result", "timetable"} else 0.6
                self._memory_event(self.memory.observe(self.loop, event, importance, self.mood))
        if kind in {"kindness", "performance", "prank"} and event.get("actor") == "phil":
            self._shareable_fact(event)
        return event

    def start(self, loop: int) -> None:
        previous_pencil = self.day.pencil
        self.loop, self.tick, self.next_tick = loop, 0, 0
        self.day = DayState(pencil="whole" if self.reset_pencil else previous_pencil)
        self._phil_decisions = []
        if not self.keep_memory:
            self.memory = Memory()
            self.pencil_experiment = None
            self.piano_level = 0
            self.first_realization = None
            self.mood, self.arousal, self.quiet_days = 0.10, 0.40, 0
            self.goals = [CAST["phil"]["goal"]]
            self.action_values = {}
        self.log("day_start", "February 2 begins.", positions=dict(self.positions))
        self._emotion("morning reset")

    def _active_here(self, location: str) -> list[str]:
        return [name for name, status in self.day.opportunities.items()
                if status == "active" and OPPORTUNITIES[name].location == location]

    def _broll_subject(self) -> dict | None:
        return next(
            (event for event in reversed(self._scene("larry"))
             if event["location"] == self.positions["larry"] and event["tick"] >= self.tick - 1
             and event["type"] in {"puddle", "world_event", "kindness", "performance"}
             and event["id"] not in self.day.filmed_sources),
            None,
        )

    def allowed(self, actor: str, exchange: int = 0) -> list[str]:
        location = self.positions[actor]
        present = self._witnesses(location)
        actions = ["wait", *(f"talk:{other}" for other in present if actor != other)]
        if exchange == 0 and actor not in self.day.moved:
            actions += [f"move:{place}" for place in ROADS[location]
                        if place != "outskirts" and (location != "outskirts" or self.tick < 20)]
        if actor == "rita" and self.invitation and "phil" in present:
            actions.append("decline_invitation")
            if len(self.rita_evidence) >= 2 and self.day.relationship.gate(self.tick) == 3:
                actions.append("accept_invitation")
        if exchange:
            return actions
        if actor != "phil":
            if actor == "larry" and self._broll_subject():
                actions.append("film_broll")
            if actor == "ned" and location == "main_st" and 3 <= self.tick <= 9 and not self.day.shown_policy:
                actions.append("show_policy")
            if actor == "rita" and location == "hotel" and self.tick >= 14 and not self.day.checked_station:
                actions.append("check_in_with_station")
            if "phil" in present and self.tick >= 26 and actor not in self.day.credits:
                if any(entry["kind"] == "kindness" for entry in self.day.learned_facts[actor].values()):
                    actions.append("credit_phil")
            if actor == "rita" and "phil" in present:
                actions.extend(
                    f"share_fact:{fact}" for fact, (_, gate, _) in RITA_FACTS.items()
                    if gate <= self.day.relationship.gate(self.tick)
                    and fact not in self.day.disclosed_rita_facts
                )
            return actions

        if location == "inn":
            actions.append("inspect_pencil")
            if actor not in self.day.moved:
                actions.append("avoid_puddle")
            actions.append("break_pencil")
        if location == "country_rd" and actor not in self.day.moved:
            actions.append("attempt_exit")
        if location == "knob" and self.tick >= 4 and "larry" in present:
            actions.append("report_weather")
        if location == "main_st" and "ned" in present and 3 <= self.tick <= 9 and not self.day.bought_policy:
            actions.append("buy_a_policy")
        if location == "diner":
            actions.append("order_everything")
        if location == "piano_teacher" and not self.day.practiced and self.lesson_tick <= self.tick <= self.lesson_tick + 2:
            actions.append("practice_piano")
        actions += [f"help:{name}" for name in self._active_here(location)]
        if location == "hotel":
            if self.tick >= 24 and not self.day.helped:
                actions.append("help_guests")
            if self.tick >= 26 and self.piano_level and not self.day.performed:
                actions.append("play_piano")
                if self.piano_level >= 3:
                    actions.append("play_with_band")
            if self.tick >= 26 and "rita" in present and not self.day.invited:
                actions.append("invite_rita")
        return actions

    def _scene(self, actor: str) -> list[dict]:
        withheld = self.withheld_memory if actor == "phil" else frozenset()
        return [self.events[index] for index in self.day.seen[actor][-_SCENE_WINDOW:]
                if self.events[index]["id"] not in withheld]

    def _read_timetable(self) -> None:
        if self.positions["phil"] not in NOTICE_LOCATIONS or self.day.appointment_event:
            return
        appointment = lesson_notice(self.lesson_tick)
        event = self.observe("timetable", notice_text(appointment), "phil", subject="piano_lesson",
                             appointment=appointment, witnesses=["phil"])
        self.day.appointment_event = event["id"]

    def _known_appointments(self, memories: list[dict], current: list[dict]) -> list[dict]:
        event_id = self.day.appointment_event
        if event_id and event_id not in self.withheld_memory:
            event = next((row for row in reversed(self.events) if row["id"] == event_id), None)
            if event:
                if not any(row["event_id"] == event_id for row in current):
                    current.append({"type": "timetable", "text": event["text"], "event_id": event_id,
                                    "actor": "phil", "subject": "piano_lesson"})
                return [{**event["appointment"], "basis": "observed_notice", "event_id": event_id}]
        return [{**row["appointment"], "basis": "remembered_notice", "event_id": row["event_id"]}
                for row in memories if row.get("appointment")]

    def observation(self, actor: str, exchange: int = 0) -> dict:
        location = self.positions[actor]
        scene = self._scene(actor)
        active = self._active_here(location)
        obs = {
            "actor": actor, "name": CAST[actor]["name"],
            "goal": ", ".join(self.goals) if actor == "phil" else CAST[actor]["goal"],
            "voice": CAST[actor]["voice"],
            "date": "February 2", "time": clock(self.tick), "tick": self.tick,
            "location": location, "location_id": location, "exchange": exchange,
            "actions": self.allowed(actor, exchange), "present": self._witnesses(location),
            "observations": [entry["text"] for entry in scene],
            "current_evidence": [{
                "type": entry["type"], "event_id": entry["id"], "text": entry["text"],
                "actor": entry.get("actor"), "subject": entry.get("subject"),
                **({"state": entry["state"]} if "state" in entry else {}),
            } for entry in scene if entry["type"] not in {"position", "gossip"}],
            "world": {"opportunities": active},
        }
        if active:
            obs["world"]["opportunity_details"] = [
                {"id": name, "visible": OPPORTUNITIES[name].notice,
                 "until": clock(OPPORTUNITIES[name].closes)}
                for name in active
            ]
        receipts = [
            {"event_id": entry["id"], "actor": entry["actor"], "transport": "band",
             "receipt": entry["transport"]["receipt"]}
            for entry in scene if actor in entry.get("transport", {}).get("verified_recipients", [])
        ]
        if receipts:
            obs["message_receipts"] = receipts
        if location in {"country_rd", "outskirts"}:
            obs["world"]["road_closed"] = self.tick >= 20
            if self.tick < 20:
                obs["world"]["road_notice"] = {"closure_tick": 20, "forecast": "Road may close at 16:00."}
        if location == "inn":
            inspected = next((entry for entry in reversed(scene) if entry["type"] == "pencil"), None)
            if inspected:
                obs["world"]["pencil"] = inspected["state"]
        if actor == "phil":
            agenda = " ".join(entry["text"] for entry in scene[-3:]) + " " + obs["goal"]
            recalled = self.memory.recall(self.loop, location, query=agenda, valence=self.mood,
                                          withheld=self.withheld_memory)
            if self.loop > 1 and location == "inn" and self.tick <= 1:
                # Keep these visible at the checkpoint where they can affect the route.
                evidence = [item for item in self.memory.recall(
                    self.loop, location, limit=20, query="puddle pencil reset",
                    valence=self.mood, withheld=self.withheld_memory,
                ) if "puddle" in item["text"] or item["kind"] == "belief"][:3]
                for item in reversed(evidence):
                    if item not in recalled:
                        recalled.insert(0, item)
            obs["memories"] = recalled[:8]
            appointments = self._known_appointments(obs["memories"], obs["current_evidence"])
            if appointments:
                obs["known_appointments"] = appointments
            obs["piano_level"] = self.piano_level
            obs["mood"] = self._phase()
            if self.tick >= 28:
                obs["energy"] = "Tired after a long day. Speak plainly."
            if self.day.recognition >= 0.5:
                obs["sensation"] = ("a jolt of recognition" if self.day.recognition >= 0.9
                                    else "an odd sense of familiarity")
            today = self._values_at(location, "rita" in obs["present"])
            if today:
                obs["gut_feeling"] = today
            if self.director.mode == "local_policy":
                obs["learned_action_values"] = self._familiar_actions(
                    location, "rita" in obs["present"], min_count=1,
                )
        else:
            planned, activity = schedule_at(actor, self.tick)
            obs["schedule"] = {"usual_location": planned, "activity": activity}
            obs["daily_facts"] = [
                {"kind": fact["kind"], "subject": fact["subject"], "text": fact["text"]}
                for fact in self.day.learned_facts[actor].values()
            ]
        if actor == "rita":
            obs["rita_evidence_count"] = len(self.rita_evidence)
            obs["relationship"] = self.day.relationship.attitude(self.tick)
        return obs

    def _decision_state(self) -> str:
        return digest({
            "log": self._log_digest, "canonical": self._canonical_digest,
            "seed": self.seed, "settings": [self.keep_memory, self.lesson_tick, self.reset_pencil, self.day_ticks],
            "loop": self.loop, "tick": self.tick, "day": asdict(self.day), "memory": self.memory.records,
            "experiment": self.pencil_experiment, "skill": self.piano_level,
            "realization": self.first_realization, "goals": self.goals, "values": self.action_values,
            "mood": [self.mood, self.arousal, self.quiet_days],
        })

    def _mark_mode(self, actor: str, mode: str, source: dict | None = None) -> None:
        before = self.day.modes[actor]
        self.day.modes[actor] = mode
        if mode == "live":
            self.day.divergence_start[actor] = self.tick
        kind = "divergence" if mode == "live" else "npc_mode"
        source_fields = {
            "source_actor": source.get("actor") if source else None,
            "source_event": source["id"] if source else None,
            "source_type": source["type"] if source else None,
        }
        if mode == "live":
            source_fields["cause"] = "changed_local_evidence" if source else "changed_context"
        self.log(kind, f"{CAST[actor]['name']}'s scene is {mode}.", actor=actor,
                 location=self.positions[actor], before=before, npc_mode=mode, **source_fields)

    def _replay(self, actor: str, exchange: int, state: dict, scene: list[dict]) -> tuple[dict | None, str | None]:
        if actor == "phil" or self.loop == 1:
            return None, None
        canonical = self.canonical.get((actor, self.tick, exchange))
        match_kind = match(canonical["perception"], state) if canonical and canonical.get("perception") else None
        previous = self.day.modes[actor]
        if previous == "live" and exchange == 0 and self.tick in REJOIN_TICKS[actor]:
            since = self.day.divergence_start.get(actor, self.tick)
            important = any(
                row["importance"] >= 0.5 and row["tick"] >= since
                for row in self.day.learned_facts[actor].values()
            )
            if not important:
                self._mark_mode(actor, "rejoining")
                previous = "rejoining"
        if match_kind and previous in {"scripted", "rejoining"}:
            if previous == "rejoining":
                self._mark_mode(actor, "scripted")
            return canonical, match_kind
        if previous == "scripted":
            previous_scene = canonical.get("perception") if canonical else None
            self._mark_mode(actor, "live", changed_event(previous_scene, scene, actor))
        return None, None

    def _choose(self, actor: str, obs: dict) -> tuple[Choice, str, str | None, dict, dict]:
        live = getattr(self.director, "is_live", lambda _: self.director.mode == "live")(actor)
        local = self.director.mode == "local_policy"
        mode = "live" if live else "local_policy" if local else "fixture"
        raw = self.director.choose(actor, obs)
        choice = Choice.read(raw, obs["actions"])
        if choice is None and live:
            obs = {**obs, "repair": "Choose one exact action ID and return the required JSON object."}
            raw = self.director.choose(actor, obs)
            choice = Choice.read(raw, obs["actions"])
        if choice is None:
            failure = getattr(self.director, "decision_metadata", lambda: {})()
            failure_kind = (failure.get("failure_kind", "invalid_action")
                            if isinstance(failure, dict) else "invalid_action")
            self.log("rejected", "The proposed action failed validation.", actor=actor,
                     location=self.positions[actor], failure_kind=failure_kind)
            return Choice("wait", "The world waited after rejecting the action."), mode, None, obs, {}
        line = " ".join((choice.reason, choice.line, choice.prediction, choice.hypothesis)).casefold()
        if any(phrase in line for phrase in _GUARDED_PHRASES):
            self.log("safety_filtered", "The world held this beat for a PG alternative.",
                     actor=actor, location=self.positions[actor])
            return Choice("wait", "The world paused."), mode, None, obs, {}
        metadata = getattr(self.director, "decision_metadata", lambda: {})() if live or local else {}
        if not isinstance(metadata, dict):
            metadata = {}
        if metadata.get("alias_names") is True:
            choice = replace(choice, reason=restore_names(choice.reason), line=restore_names(choice.line),
                             prediction=restore_names(choice.prediction))
        return choice, mode, raw, obs, metadata

    def decide(self, actor: str, exchange: int = 0) -> list[str]:
        if actor == "phil":
            self._close_reward()
        obs = self.observation(actor, exchange)
        state = comparable(obs, self._scene(actor))
        signature = digest(state)
        checkpoint = self._decision_state() if actor == "phil" else None
        canonical, match_kind = self._replay(actor, exchange, state, self._scene(actor))
        if canonical and canonical["choice"]["action"] in obs["actions"]:
            choice = Choice(**canonical["choice"])
            mode, raw, metadata = "replay", None, {}
            self.replayed_decisions += 1
        else:
            canonical, match_kind = None, None
            choice, mode, raw, obs, metadata = self._choose(actor, obs)
            self.live_decisions += 1
        recalled = [row["event_id"] for row in obs.get("memories", [])]
        current = [row["event_id"] for row in obs["current_evidence"]]
        supports = [item for item in choice.support if item in recalled or item in current]
        fields = {
            "actor": actor, "action": choice.action, "location": self.positions[actor], "mode": mode,
            "source": canonical["source"] if canonical else mode, "fingerprint": signature,
            "exchange": exchange, "recalled": recalled, "current_evidence": current,
            "stated_support": supports, "available_actions": obs["actions"], "replay_match": match_kind,
        }
        if canonical and canonical.get("decision_id"):
            fields["replay_source_event"] = canonical["decision_id"]
        if actor == "phil":
            fields.update(
                checkpoint_fingerprint=checkpoint, policy_observation=obs, completion=raw,
                decision_key=self._value_key(self.positions[actor], "rita" in obs["present"]),
                phase=self._phase(), potential_before=self.day.relationship.potential(self.tick),
                withheld_memory=sorted(self.withheld_memory),
            )
        if obs.get("message_receipts"):
            fields["message_receipts"] = obs["message_receipts"]
        if actor != "phil" and self.day.learned_facts[actor]:
            fields["known_fact_sources"] = [
                {"subject": fact["subject"], "source_event": fact["evidence"],
                 "heard_via": fact["heard_via"], "fidelity": fact["fidelity"]}
                for fact in self.day.learned_facts[actor].values() if "heard_via" in fact
            ]
        if metadata:
            fields["policy_metadata" if mode == "local_policy" else "model_metadata"] = metadata
        event = self.log("decision", choice.reason or choice.action, **fields)
        if actor == "phil":
            self._phil_decisions.append(event["order"])
            for record, before in self.memory.rehearse(
                self.loop, supports, valence=self.mood, seed=self.seed, decision=event["id"],
            ):
                self._memory_event(record, operation="RECONSOLIDATE", before=before,
                                   after=record["text"], decision_id=event["id"])
        expected = self._prediction(choice)
        prediction_text = choice.prediction
        if choice.action == "break_pencil" and expected and not prediction_text:
            prediction_text = f"Phil predicts the pencil will be {expected} the next morning."
        if prediction_text:
            prediction = self.observe("prediction", prediction_text, actor,
                                      action=choice.action, decision_id=event["id"],
                                      hypothesis=choice.hypothesis or None, predicted=expected)
            if choice.action == "break_pencil" and self.day.pencil == "whole":
                self.pencil_experiment = {
                    "prediction": prediction["id"], "loop": self.loop, "expected": expected,
                    "hypothesis": choice.hypothesis or "room_resets",
                }
        responses = self.apply(actor, choice, canonical, event)
        if self.loop == 1 and actor != "phil":
            item = {
                "perception": state, "fingerprint": signature, "choice": asdict(choice), "source": mode,
                "decision_id": event["id"],
                "utterance_id": next((row["utterance_id"] for row in reversed(self.events[event["order"] + 1:])
                                      if row["type"] == "utterance" and row["actor"] == actor), None),
            }
            self.canonical[(actor, self.tick, exchange)] = item
            self._canonical_digest = digest([self._canonical_digest, actor, self.tick, exchange, item])
        for evidence in supports:
            linked = next((row for row in reversed(self.events) if row["id"] == evidence), None)
            if linked and linked["type"] == "test_result":
                self.log("evidence_use", f"{CAST[actor]['name']} cited the physical test when choosing what to do.",
                         actor=actor, location=self.positions[actor], source_event=evidence,
                         decision_id=event["id"], action=choice.action, use_kind="decision_cited")
        return responses

    def move(self, actor: str, target: str, source: str = "decision") -> None:
        origin = self.positions[actor]
        if target not in ROADS[origin] or actor in self.day.moved:
            raise ValueError("Movement requires an unused turn and an adjacent destination.")
        witnesses = tuple(dict.fromkeys(self._witnesses(origin) + self._witnesses(target)))
        self.positions[actor] = target
        self.day.moved.append(actor)
        self.publish("position", f"{CAST[actor]['name']} goes to {PLACES[target]['label']}.",
                     target, actor=actor, moving_from=origin, witnesses=list(witnesses), source=source)
        if actor == "phil":
            self._read_timetable()

    def _utter(self, actor: str, choice: Choice, target: str, canonical: dict | None,
               decision: dict | None) -> dict:
        identifier = canonical.get("utterance_id") if canonical else None
        origin = {key: decision[key] for key in ("mode", "source")} if decision else {}
        if decision:
            origin["decision_id"] = decision["id"]
        utterance = self.observe("utterance", choice.line, actor, to=target,
                                 intent=utterance_intent(choice.line),
                                 utterance_id=identifier or f"u{len(self.events):05d}", **origin)
        self._evaluate_rita_facts(actor, target, utterance)
        return utterance

    def _evaluate_rita_facts(self, actor: str, target: str, utterance: dict) -> None:
        facts = spoken_facts(utterance["text"])
        if actor == "rita" and "phil" in utterance["witnesses"]:
            disclosed = self.day.known_phil_facts
            disclosed.extend(fact for fact in facts if fact not in disclosed)
        if actor != "phil" or target != "rita":
            return
        unknown = [fact for fact in facts if fact not in self.day.known_phil_facts]
        if unknown:
            self.log("suspicion_spike", "Rita is unsettled that Phil knew a private detail.",
                     actor="rita", location=self.positions["rita"], facts=unknown,
                     source_event=utterance["id"])
            self._appraise(utterance, "deception")

    @staticmethod
    def _prediction(choice: Choice) -> str | None:
        if choice.predicted in {"whole", "broken"}:
            return choice.predicted
        return None

    def _inspect(self) -> None:
        seen = self.observe("pencil", f"Phil inspects the pencil. It is {self.day.pencil}.",
                            "phil", state=self.day.pencil)
        experiment = self.pencil_experiment
        if not experiment or experiment["loop"] >= self.loop or "action" not in experiment:
            return
        observed = self.day.pencil
        expected = experiment.get("expected")
        outcome = self.observe(
            "test_result", f"The pencil is {observed} this morning.", "phil",
            prediction=experiment["prediction"], action_evidence=experiment["action"],
            observation=seen["id"], state=observed, prediction_id=experiment["prediction"],
            action_event_id=experiment["action"], observation_event_id=seen["id"],
            hypothesis=experiment.get("hypothesis", "room_resets"), predicted=expected, observed=observed,
            agrees_with_prediction=observed == expected if expected else None,
        )
        if observed == "whole" and not self.first_realization:
            self.first_realization = outcome["id"]
            if self.keep_memory:
                belief = self.memory.consolidate(self.loop, "belief", _BELIEF_TEXT, outcome, pinned=True)
                self._memory_event(belief)
        self.pencil_experiment = None

    def apply(self, actor: str, choice: Choice, canonical: dict | None = None,
              decision: dict | None = None) -> list[str]:
        action = choice.action
        if action.startswith("move:"):
            target = action.split(":", 1)[1]
            puddle = actor == "phil" and self.positions[actor] == "inn" and target == "main_st"
            self.move(actor, target)
            if puddle:
                self.observe("puddle", "Phil steps into the puddle on Main Street.", actor, state="wet",
                             subject="puddle")
                self._change_mood(-0.04, 0.06, "wet socks")
        elif action == "avoid_puddle":
            self.move(actor, "main_st")
            self.observe("puddle", "Phil steps around the puddle this time.", actor, state="dry",
                         subject="puddle")
        elif action.startswith("talk:") and choice.line:
            target = action.split(":", 1)[1]
            self._utter(actor, choice, target, canonical, decision)
            return [target]
        elif action == "inspect_pencil":
            self._inspect()
        elif action == "break_pencil":
            already_broken = self.day.pencil == "broken"
            self.day.pencil = "broken"
            text = ("The pencil is already broken." if already_broken
                    else "Phil breaks the pencil and leaves it on the nightstand.")
            broken = self.observe("pencil", text, actor, state="broken", subject="pencil")
            if not already_broken and self.pencil_experiment and self.pencil_experiment["loop"] == self.loop:
                self.pencil_experiment["action"] = broken["id"]
        elif action == "attempt_exit":
            if self.tick >= 20:
                self.observe("exit", "Phil reaches the barricade. Snow has shut down the road.", actor, state="blocked")
                self._change_mood(-0.12, 0.12, "blocked departure")
            else:
                self.move(actor, "outskirts")
                self.observe("exit", "Phil crosses the town line. The roadside sign has stopped spinning.", actor,
                             state="left_town")
        elif action == "report_weather":
            self.observe("camera", choice.line or "Larry films Phil reporting from the snow.", actor,
                         subject="weather_segment")
        elif action == "film_broll":
            subject = self._broll_subject()
            if subject:
                self.day.filmed_sources.append(subject["id"])
                self.observe("camera", "Larry raises his camera to catch what just happened.", actor,
                             subject="town_broll", source_event=subject["id"])
        elif action == "check_in_with_station":
            self.day.checked_station = True
            self.observe("station", "Rita calls the station with an update on the crew.", actor,
                         subject="station_update")
        elif action == "show_policy":
            self.day.shown_policy = True
            self.observe("deal", "Ned unfolds a sample policy for the morning foot traffic.", actor,
                         subject="policy_offer")
        elif action == "order_everything":
            self.observe("prank", "Phil orders the entire menu. The counter begins to disappear under plates.",
                         actor, subject="too_much_breakfast")
            self._change_mood(0.06, 0.15, "breakfast stunt")
        elif action == "buy_a_policy":
            self.day.bought_policy = True
            self.observe("deal", "Phil buys a policy. Ned has to check whether the receipt pad is real.", actor,
                         subject="ned_insurance")
            return ["ned"]
        elif action == "practice_piano":
            self.day.practiced = True
            self.piano_level += 1
            cited_notice = self.day.appointment_event
            if not decision or cited_notice not in decision["stated_support"]:
                cited_notice = None
            evidence = self.observe("skill", "Phil practices piano.", actor, skill="piano", level=self.piano_level,
                                    appointment_source_event=cited_notice)
            if self.piano_level == 1:
                record = self.memory.consolidate(
                    self.loop, "skill", f"I practiced at the teacher's studio at {clock(self.tick)}.",
                    evidence, pinned=True,
                )
                self._memory_event(record)
            self._change_mood(0.08, 0.02, "piano progress")
        elif action.startswith("help:"):
            name = action.split(":", 1)[1]
            self.day.opportunities[name] = "resolved_helped"
            self.observe("kindness", OPPORTUNITIES[name].helped, actor, subject=name, status="resolved_helped")
            self._change_mood(0.12, 0.08, name)
        elif action == "help_guests":
            self.day.helped = True
            self.observe("kindness", "Phil helps the party crew get the ballroom ready.", actor,
                         subject="ballroom_crew")
            self._change_mood(0.10, 0.05, "helped the ballroom crew")
        elif action in {"play_piano", "play_with_band"}:
            self.day.performed = True
            if action == "play_with_band":
                text = "Phil sits in with the band."
            elif self.piano_level == 1:
                text = "Phil plays a tentative version of the melody he practiced."
            else:
                text = "Phil sits at the piano and plays for the room."
            self.observe("performance", text, actor, subject="piano_performance", skill_level=self.piano_level)
            self._change_mood(0.10, 0.07, "played for the ballroom")
        elif action.startswith("share_fact:"):
            fact = action.split(":", 1)[1]
            self.day.disclosed_rita_facts.append(fact)
            message = Choice(action, choice.reason, RITA_FACTS[fact][2])
            self._utter(actor, message, "phil", canonical, decision)
            return ["phil"]
        elif action == "invite_rita":
            self.day.invitation = self.day.invited = True
            invitation = self.observe("invitation", choice.line or "Phil asks Rita to stay after the party.",
                                      actor, to="rita", decision_id=decision["id"] if decision else None)
            self.day.invitation_event_id = invitation["id"]
            return ["rita"]
        elif action in {"accept_invitation", "decline_invitation"}:
            self.day.invitation = False
            self.day.accepted = action == "accept_invitation"
            reply = self.observe(
                "reply", choice.line or ("Rita accepts." if self.day.accepted else "Rita declines."),
                actor, accepted=self.day.accepted, evidence=self.rita_evidence[:], to="phil",
                decision_id=decision["id"] if decision else None, invitation_id=self.day.invitation_event_id,
                gate_level=self.day.relationship.gate(self.tick),
            )
            self.day.reply_event_id = reply["id"]
            if not self.day.accepted:
                self._change_mood(-0.13, -0.08, "Rita heads home")
        elif action == "credit_phil":
            fact = next(entry for entry in self.day.learned_facts[actor].values() if entry["kind"] == "kindness")
            credit = self.observe("recognition", choice.line or "Someone noticed what Phil did today.",
                                  actor, source_event=fact["evidence"], subject=fact["subject"],
                                  heard_via=fact.get("heard_via"), decision_id=decision["id"] if decision else None)
            self.day.credits[actor] = credit["id"]
        return []

    def _shareable_fact(self, event: dict) -> None:
        fact = {
            "kind": event["type"], "subject": event["subject"], "text": event["text"],
            "evidence": event["id"], "heard_via": event["id"],
            "importance": 0.80, "fidelity": 1.0, "tick": self.tick,
        }
        for witness in event["witnesses"]:
            if witness != "phil":
                self.day.learned_facts[witness][fact["subject"]] = fact
        if event["type"] == "kindness" and any(actor != "phil" for actor in event["witnesses"]):
            self.day.public_help.append(event["id"])
        if "rita" in event["witnesses"]:
            self._appraise(event, event["type"])

    def _appraise(self, event: dict, kind: str, fidelity: float = 1.0) -> None:
        source = event.get("source_event", event["id"])
        if source in self.day.appraised:
            return
        deltas = self.day.relationship.update(kind, fidelity)
        if not deltas:
            return
        self.day.appraised.append(source)
        if kind in {"kindness", "performance"}:
            self.rita_evidence.append(source)
        self.log("relationship", "Rita updates her impression of Phil.", actor="rita",
                 location=self.positions["rita"], source_event=source,
                 basis="gossip" if event["type"] == "gossip" else "witnessed",
                 state_after=asdict(self.day.relationship), deltas=deltas,
                 gate_level=self.day.relationship.gate(self.tick))

    def _gossip(self) -> None:
        pending = []
        for location in PLACES:
            listeners = [actor for actor in self._witnesses(location) if actor != "phil"]
            for teller in listeners:
                facts = list(self.day.learned_facts[teller].values())
                for listener in listeners:
                    if teller == listener:
                        continue
                    candidates = [fact for fact in facts
                                  if fact["subject"] not in self.day.learned_facts[listener]
                                  and fact["fidelity"] * 0.8 >= 0.5]
                    if candidates:
                        fact = max(candidates, key=lambda item: (item["importance"], item["fidelity"], item["subject"]))
                        pending.append((location, teller, listener, fact))
        for location, teller, listener, fact in pending:
            if fact["subject"] in self.day.learned_facts[listener]:
                continue
            received = {**fact, "fidelity": round(fact["fidelity"] * 0.8, 3), "tick": self.tick}
            event = self.publish("gossip", f"{CAST[teller]['name']} tells {CAST[listener]['name']}: {fact['text']}",
                                 location, actor=teller, to=listener, fidelity=received["fidelity"],
                                 source_event=fact["evidence"], teller_evidence=fact.get("heard_via"),
                                 subject=fact["subject"], witnesses=[teller, listener])
            received["heard_via"] = event["id"]
            self.day.learned_facts[listener][fact["subject"]] = received
            if listener == "rita":
                self._appraise(event, fact["kind"], 0.60 * received["fidelity"])

    def _schedule(self) -> None:
        for actor in SCHEDULES_ACTORS:
            hard = APPOINTMENTS.get(actor, {}).get(self.tick)
            scheduled, _ = schedule_at(actor, self.tick)
            following = self.day.modes[actor] != "live"
            destination = hard or (scheduled if following else None)
            if not destination or destination == self.positions[actor]:
                continue
            step = next_stop(self.positions[actor], destination)
            if step:
                self.move(actor, step, "appointment" if hard else "schedule")
            if hard and self.positions[actor] != hard:
                self.observe("missed_appointment", f"{CAST[actor]['name']} is too far away to make the appointment.",
                             actor, destination=hard)

    def _anchors_and_opportunities(self) -> None:
        if self.tick in ANCHORS:
            name, location, text = ANCHORS[self.tick]
            fields = {}
            if name == "ned_greeting":
                if self.positions["ned"] == location:
                    fields["actor"] = "ned"
                else:
                    text = "Ned's corner on Main Street is empty."
                    fields["absent_actor"] = "ned"
            self.publish("anchor", text, location, anchor=name, **fields)
        if self.tick == self.lesson_tick:
            self.publish("lesson", "The piano teacher opens the lesson.", "piano_teacher", subject="piano_lesson")
        for event, opportunity in OPPORTUNITIES.items():
            if opportunity.opens == self.tick:
                self.day.opportunities[event] = "active"
                self.publish("world_event", opportunity.notice, opportunity.location,
                             subject=event, status="active")

    def _close_opportunities(self) -> None:
        for event, opportunity in OPPORTUNITIES.items():
            if opportunity.closes == self.tick and self.day.opportunities[event] == "active":
                self.day.opportunities[event] = "resolved_unhelped"
                self.publish("world_event", opportunity.elapsed, opportunity.location,
                             subject=event, status="resolved_unhelped")
                if event == "old_man_cold" and self.positions["phil"] == opportunity.location:
                    self._change_mood(-0.30, -0.16, "the relief crew arrives after a long wait")

    def _turns(self) -> None:
        pending: list[str] = []
        for actor, ticks in TURNS.items():
            lesson_turn = actor == "phil" and self.tick == self.lesson_tick and self.positions[actor] == "piano_teacher"
            if self.tick in ticks or lesson_turn:
                if actor in pending:
                    pending.remove(actor)
                pending.extend(target for target in self.decide(actor) if target not in pending)
        for exchange in range(1, MAX_EXCHANGES):
            if not pending:
                break
            responding, pending = pending, []
            for actor in responding:
                pending.extend(target for target in self.decide(actor, exchange) if target not in pending)

    def _phase(self) -> str:
        if self.mood < -0.40 and self.arousal > 0.60:
            return "restless"
        if self.mood < -0.40 and self.arousal < 0.35 and self.quiet_days < 3:
            return "withdrawn"
        if self.mood < -0.25:
            return "low"
        return "steady"

    def _emotion(self, cause: str) -> None:
        self.log("emotion", f"Phil feels {self._phase()}.", actor="phil",
                 location=self.positions["phil"], valence=round(self.mood, 3),
                 arousal=round(self.arousal, 3), phase=self._phase(), cause=cause, witnesses=["phil"])

    def _change_mood(self, valence: float, arousal: float, cause: str) -> None:
        previous = self._phase()
        self.mood = max(-1.0, min(1.0, self.mood + valence))
        self.arousal = max(0.0, min(1.0, self.arousal + arousal))
        if previous != self._phase():
            self._emotion(cause)

    def _value_key(self, location: str, rita_present: bool) -> str:
        return f"{self.tick // 4}:{location}:{int(rita_present)}"

    def _values_at(self, location: str, rita_present: bool) -> list[str]:
        values = sorted(((stats["mean"], name) for name, stats in self._familiar_actions(location, rita_present).items()),
                        reverse=True)
        return [f"Past attempts at {action} felt {'more promising' if mean > 0 else 'less promising'} here."
                for mean, action in values[:2]]

    def _familiar_actions(self, location: str, rita_present: bool, min_count: int = 2) -> dict[str, dict]:
        key = self._value_key(location, rita_present) + "|"
        return {name.removeprefix(key): item.copy() for name, item in self.action_values.items()
                if name.startswith(key) and item["count"] >= min_count}

    def _close_reward(self, terminal: float = 0.0) -> None:
        if not self._phil_decisions:
            return
        event = self.events[self._phil_decisions[-1]]
        if "reward" in event:
            return
        difference = self.day.relationship.potential(self.tick) - event["potential_before"]
        event["reward"] = round(difference + terminal, 5)
        event["r_t"] = event["reward"]

    def _finish_reward(self) -> None:
        self._close_reward(2.0 if self.ending == "day_two" else 0.0)
        future = 0.0
        for stats in self.action_values.values():
            stats["mean"] *= 0.85
        for index in reversed(self._phil_decisions):
            event = self.events[index]
            future += event["reward"]
            event["return_to_go"] = round(future, 5)
            event["G_t"] = event["return_to_go"]
            action_type = event["action"].split(":", 1)[0]
            key = f"{event['decision_key']}|{action_type}"
            stats = self.action_values.setdefault(key, {"mean": 0.0, "count": 0})
            stats["count"] += 1
            stats["mean"] += (future - stats["mean"]) / stats["count"]

    def _finish_day(self) -> None:
        if self.day.accepted and len(self.rita_evidence) >= 2 and self.day.relationship.gate(self.tick) == 3:
            self.ending, self.ending_reason = "day_two", "rita_chose_to_stay"
            self.log("ending_decision", "Rita chose to stay after seeing how Phil spent the day.",
                     actor="rita", location="hotel", evidence=self.rita_evidence[:],
                     reason=self.ending_reason, reply_event_id=self.day.reply_event_id,
                     invitation_id=self.day.invitation_event_id)
        elif self.first_realization and len(self.day.public_help) >= 2 and len(self.day.credits) >= 2:
            self.ending, self.ending_reason = "day_two", "community_recognition"
            self.log("ending_decision", "The crew recognizes what Phil did for the town.",
                     actor="phil", location=self.positions["phil"],
                     evidence=[*self.day.public_help, *self.day.credits.values(), self.first_realization],
                     reason=self.ending_reason)
        self._finish_reward()
        if self.keep_memory and self.first_realization and len(self.goals) == 1:
            self.goals.append("Use what I have learned to make something better today.")
            reflection = self.log("reflection", "Phil can carry a practical lesson into tomorrow.",
                                  actor="phil", location=self.positions["phil"],
                                  source_event=self.first_realization, basis="verified_world_result", witnesses=["phil"])
            remembered = self.memory.consolidate(self.loop, "reflection", self.goals[-1], reflection)
            self._memory_event(remembered)
        for operation, record in self.memory.fade(self.loop):
            self._memory_event(record, operation=operation)
        self.quiet_days = self.quiet_days + 1 if self._phase() == "withdrawn" else 0
        self.mood += 0.15 * (0.1 - self.mood)
        self.arousal += 0.25 * (0.4 - self.arousal)
        if self.quiet_days >= 3:
            self.arousal, self.quiet_days = 0.60, 0
        self.log("night", "The day ends.", ending=self.ending, ending_reason=self.ending_reason,
                 relationship=asdict(self.day.relationship), gate_level=self.day.relationship.gate(self.tick),
                 evidence=self.rita_evidence[:], memory_count=len(self.memory.records))
        self.completed_loops = self.loop
        if self.ending == "day_two":
            self.tick = 0
            line = ("February 3. Rita reaches over to switch off the radio."
                    if self.ending_reason == "rita_chose_to_stay"
                    else "February 3. The radio calls for clear skies. The crew makes plans for breakfast.")
            self.log("day_two", line, ending_reason=self.ending_reason, location="inn")

    def advance_tick(self, ticks: int = 36) -> bool:
        """Advance one complete clock tick and finish the day when its clock closes."""
        if self.ending == "day_two":
            return False
        if self._pending_tick:
            raise ValueError("An interrupted tick requires restoration from a prior checkpoint.")
        if not 1 <= ticks <= 36:
            raise ValueError("A day must have between one and 36 ticks.")
        if self.loop == self.completed_loops:
            self.start(self.completed_loops + 1)
            self.day_ticks = ticks
        elif self.day_ticks is not None and ticks != self.day_ticks:
            raise ValueError("The day length must stay constant while resuming a day.")
        else:
            self.day_ticks = ticks
        self._pending_tick = True
        self.tick = self.next_tick
        self.day.moved.clear()
        self.day.recognition, self.day.recognition_event = 0.0, None
        self._schedule()
        self._anchors_and_opportunities()
        self._read_timetable()
        self._turns()
        self._close_opportunities()
        self._gossip()
        self.next_tick += 1
        if self.next_tick >= ticks:
            self._finish_day()
        self._pending_tick = False
        return True

    def checkpoint(self) -> dict:
        """Return a versioned, detached snapshot after a complete tick."""
        if self._pending_tick:
            raise ValueError("Save a checkpoint only after the current tick completes.")
        snapshot = {
            "version": CHECKPOINT_VERSION, "loop": self.loop, "tick": self.tick,
            "completed_loops": self.completed_loops, "next_tick": self.next_tick, "day_ticks": self.day_ticks,
            "ending": self.ending, "ending_reason": self.ending_reason,
            "events": self.events, "memory": self.memory.records, "piano_level": self.piano_level,
            "pencil_experiment": self.pencil_experiment, "first_realization": self.first_realization,
            "live_decisions": self.live_decisions, "replayed_decisions": self.replayed_decisions,
            "day": asdict(self.day), "log_digest": self._log_digest, "canonical_digest": self._canonical_digest,
            "phil_decisions": self._phil_decisions, "withheld_memory": sorted(self.withheld_memory),
            "config": {
                "keep_memory": self.keep_memory, "lesson_tick": self.lesson_tick, "seed": self.seed,
                "reset_pencil": self.reset_pencil,
            },
            "mood": self.mood, "arousal": self.arousal, "quiet_days": self.quiet_days,
            "goals": self.goals, "action_values": self.action_values,
            "canonical": [{"actor": actor, "tick": tick, "exchange": exchange, **item}
                          for (actor, tick, exchange), item in self.canonical.items()],
        }
        # Canonical choices contain tuple supports in memory. A JSON round trip gives the
        # caller the same detached types that a saved checkpoint would have on disk.
        return json.loads(json.dumps(snapshot, ensure_ascii=False, allow_nan=False))

    @classmethod
    def from_checkpoint(
        cls, checkpoint: dict, director, *, withheld_memory: tuple[str, ...] | None = None,
        transport=None,
    ) -> Simulation:
        result = cls(director, transport=transport, **checkpoint.get("config", {}))
        result.restore(checkpoint)
        if withheld_memory is not None:
            result.withheld_memory = frozenset(withheld_memory)
        return result

    def restore(self, checkpoint: dict) -> None:
        # Support night-only checkpoints produced before scene state was persisted.
        state = copy.deepcopy(checkpoint)
        version = state.get("version", 1)
        if version not in {1, CHECKPOINT_VERSION}:
            raise ValueError("Unsupported checkpoint version.")
        if "config" in state:
            for name, expected in state["config"].items():
                if getattr(self, name) != expected:
                    raise ValueError(f"Checkpoint has different {name}.")
        self.loop, self.tick = state["loop"], state["tick"]
        self.ending, self.ending_reason = state["ending"], state.get("ending_reason")
        self.events, self.memory = state["events"], Memory(state["memory"])
        self.piano_level, self.pencil_experiment = state["piano_level"], state["pencil_experiment"]
        self.live_decisions, self.replayed_decisions = state["live_decisions"], state["replayed_decisions"]
        self.completed_loops = state.get("completed_loops", self.loop)
        self.next_tick, self.day_ticks = state.get("next_tick", 0), state.get("day_ticks")
        self.first_realization = state.get("first_realization")
        self._log_digest = state["log_digest"] if "log_digest" in state else digest(self.events)
        self._canonical_digest = (state["canonical_digest"] if "canonical_digest" in state
                                  else digest(state["canonical"]))
        self._phil_decisions = state.get("phil_decisions", [])
        self.withheld_memory = frozenset(state.get("withheld_memory", []))
        day = state.get("day", {})
        relationship = Relationship(**day.pop("relationship", {}))
        self.day = DayState(**day, relationship=relationship)
        self.mood, self.arousal = state.get("mood", 0.10), state.get("arousal", 0.40)
        self.quiet_days = state.get("quiet_days", 0)
        self.goals, self.action_values = state.get("goals", self.goals), state.get("action_values", {})
        self.canonical = {}
        for entry in state["canonical"]:
            key = entry.pop("actor"), entry.pop("tick"), entry.pop("exchange", 0)
            entry.setdefault("source", self.director.mode)
            self.canonical[key] = entry
        self._pending_tick = False

    def run(self, loops: int, ticks: int = 36, on_day_finished=None, *, on_day=None, on_tick_finished=None) -> None:
        """Run through the requested total number of days, including prior saved days."""
        if loops < self.completed_loops:
            raise ValueError("The requested day count precedes the checkpoint.")
        while self.completed_loops < loops and self.ending != "day_two":
            previous = self.completed_loops
            self.advance_tick(ticks)
            if on_tick_finished:
                on_tick_finished(self.checkpoint())
            if self.completed_loops != previous:
                if on_day_finished:
                    on_day_finished(self.checkpoint())
                if on_day:
                    on_day(self)


SCHEDULES_ACTORS = tuple(actor for actor in CAST if actor != "phil")
