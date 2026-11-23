"""Local agents that choose legal town actions by scoring their observations."""

from __future__ import annotations

from dataclasses import dataclass, field
import json

from .appointments import lesson_plan
from .replay import digest
from .town import clock, next_stop

POLICY_VERSION = "2"


@dataclass
class Candidate:
    action: str
    score: float = 0.0
    factors: list[dict] = field(default_factory=list)
    support: tuple[str, ...] = ()

    def add(self, weight: float, reason: str) -> None:
        weight = round(weight, 4)
        if weight:
            self.score = round(self.score + weight, 4)
            self.factors.append({"weight": weight, "reason": reason})


def _fact(observation: dict, kind: str, state: str | None = None) -> dict | None:
    return next((row for row in reversed(observation["current_evidence"])
                 if row["type"] == kind and (state is None or row.get("state") == state)), None)


def _route(candidate: Candidate, observation: dict, destination: str, value: float, reason: str) -> None:
    location = observation["location_id"]
    if candidate.action == f"move:{next_stop(location, destination)}":
        candidate.add(value, reason)
    elif candidate.action == "wait" and location == destination:
        candidate.add(value * 0.77, reason)


def _phil(candidate: Candidate, obs: dict, planned: dict | None) -> None:
    action, tick, location = candidate.action, obs["tick"], obs["location_id"]
    memories = obs.get("memories", [])
    result = _fact(obs, "test_result", "whole")
    belief = next((row for row in memories if row["kind"] == "belief"), None)
    learned = result or belief
    wet_memory = next((row for row in memories if "steps into the puddle" in row["text"]), None)

    if action == "inspect_pencil":
        if "pencil" not in obs["world"]:
            candidate.add(6.0 if "energy" in obs else 10.1,
                          "Inspect the nightstand before making assumptions about the room.")
        return
    if action == "break_pencil":
        if "energy" in obs and obs["world"].get("pencil") != "broken" and not learned:
            candidate.add(7.8, "Leave a physical mark and check whether it stays overnight.")
        return
    if action == "avoid_puddle" and wet_memory and tick <= 4:
        candidate.add(3.4, "Remember how cold it felt to step into the puddle.")
        candidate.support = (wet_memory["event_id"],)
        if learned:
            candidate.add(3.3, "The physical test gives me a reason to expect the morning to repeat.")
            candidate.support += (learned["event_id"],)
        return
    if action.startswith("help:"):
        candidate.add(10, "There is an immediate problem in front of me and time to act.")
        return
    if action == "help_guests":
        candidate.add(7.6, "The ballroom crew could use another pair of hands.")
        return
    if action == "practice_piano":
        candidate.add(8.7, "The teacher is available now. I can learn something that lasts.")
        if planned:
            candidate.support = (planned["source_event"],)
        return
    if action in {"play_piano", "play_with_band"}:
        candidate.add(8.3 + min(obs["piano_level"] - 1, 3) * 0.33,
                      "Use the skill I practiced to contribute to the party.")
        return
    if action == "invite_rita" and _fact(obs, "kindness") and _fact(obs, "performance"):
        candidate.add(6.9, "We've shared the evening; give Rita a choice about staying.")
        return
    if action == "report_weather" and not any(row.get("subject") == "weather_segment" for row in obs["current_evidence"]):
        candidate.add(7.9, "Larry is here and I still owe the station a weather segment.")
        if learned and planned and planned["priority_due"] and planned["projected_lesson_if_wait"] is None:
            candidate.add(-1.7, "The posted lesson window closes before I can leave after the segment.")
        return
    if action == "attempt_exit":
        notice = obs["world"].get("road_notice")
        safe_window = notice is None or tick < notice["closure_tick"] - 2
        if not learned and not _fact(obs, "exit") and (obs["world"].get("road_closed") or safe_window):
            candidate.add(5.2, "Check for myself whether it is possible to leave town.")
        return
    if action == "buy_a_policy":
        candidate.add(2.8, "Ned has a point about insurance in this kind of weather.")
        return
    if action == "order_everything":
        candidate.add(2.6, "Breakfast is one thing I can still enjoy this morning.")
        return
    if action.startswith("talk:"):
        target = action.partition(":")[2]
        if target in {"ned", "larry", "rita"} and not _fact(obs, "utterance"):
            candidate.add(2.2, "Ask someone nearby what else is happening in town.")
        return
    if obs["exchange"]:
        return

    if location == "outskirts":
        _route(candidate, obs, "country_rd", 6.6, "Get back to town before the storm strands me here.")
    elif tick >= 32 and not learned:
        _route(candidate, obs, "inn", 6.5, "Get back to the inn before the night is over.")
    elif (learned and planned and planned["priority_due"] and not obs.get("piano_level")
          and "practice_piano" not in obs["actions"]):
        urgency = 3.6 if planned["projected_lesson_if_wait"] is None else 0.0
        _route(candidate, obs, planned["location"], 5.9 + urgency,
               f"The notice said lessons open at {clock(planned['opens'])}. Leave time to reach the teacher.")
        if candidate.action == planned["route_action"]:
            candidate.support = (planned["source_event"], learned["event_id"])
    elif learned and tick >= 18:
        _route(candidate, obs, "hotel", 6.4, "Head toward people gathering for the evening party.")
    elif tick < 7:
        _route(candidate, obs, "knob", 5.0, "Get to the groundhog segment.")
    elif 14 <= tick <= 20 and not learned and not _fact(obs, "exit"):
        _route(candidate, obs, "country_rd", 4.4, "See what the roads look like before committing to the evening.")
    elif tick >= 20:
        _route(candidate, obs, "inn", 4.9, "It is getting late and I have a room at the inn.")
    else:
        _route(candidate, obs, "diner", 4.2, "Get warm and see who is around the café.")


def _rita(candidate: Candidate, obs: dict) -> None:
    action, tick = candidate.action, obs["tick"]
    if action == "accept_invitation":
        witnessed_kindness = sum(row["type"] == "kindness" for row in obs["current_evidence"])
        candidate.add(7.55 + min(witnessed_kindness, 3) * 0.12,
                      "I feel comfortable with Phil and can stay to hear another song.")
    elif action == "decline_invitation":
        candidate.add(7.6, "I have my own plans for the evening and can head in when I'm ready.")
    elif action == "check_in_with_station":
        candidate.add(6.7, "Call the station while I'm at the hotel and can give a firsthand update.")
    elif action.startswith("share_fact:") and tick >= 18:
        candidate.add(3.8, "If we have a free moment, share something personal on my own terms.")
    elif action.startswith("talk:") and not _fact(obs, "utterance"):
        candidate.add(3.6, "Find out what the crew has seen or what the town is doing.")
    elif obs["exchange"] == 0:
        destination = "hotel" if tick >= 18 else obs["schedule"]["usual_location"]
        _route(candidate, obs, destination, 5.4,
               "Get back to the station phone and the party." if tick >= 18
               else "Follow up on the next step in today's reporting plan.")


def _crew(candidate: Candidate, actor: str, obs: dict) -> None:
    action, tick = candidate.action, obs["tick"]
    if action == "credit_phil":
        candidate.add(9.4, "I learned about a concrete thing Phil did, and he deserves credit for it.")
    elif action == "film_broll":
        candidate.add(7.1, "Capture this physical moment while it can still be filmed.")
    elif action == "show_policy":
        customer = len(obs["present"]) > 1
        candidate.add(6.0 + 0.6 * customer, "Set out a policy where the morning foot traffic can see it.")
    elif action.startswith("talk:") and not _fact(obs, "utterance"):
        candidate.add(4.3, "Ask about a good local story." if actor == "larry"
                      else "Make an introduction and see what the other person is up to.")
    elif obs["exchange"] == 0:
        destination = "hotel" if tick >= 18 else obs["schedule"]["usual_location"]
        _route(candidate, obs, destination, 5.5,
               "I want to be there before the ballroom fills up." if tick >= 18
               else "Go where today's work is supposed to happen.")


_DIALOGUE = {
    "phil": {"talk": "What are you hearing around town?", "report_weather": "It's cold enough to negotiate with the thermometer.",
             "invite_rita": "Would you like to stay for another song?"},
    "rita": {"talk": "Tell me the part the camera missed.", "accept_invitation": "I have time for one more song.",
             "decline_invitation": "You go on. I'm heading in for the night."},
    "larry": {"talk": "If anything moves, tell me before the shot is over.", "credit_phil": "I heard what you did. That deserved a shot."},
    "ned": {"talk": "Well, that's a good coat. What else should we write a policy for?",
            "credit_phil": "People are saying you came through for them today."},
}


class LocalDirector:
    """Independent utility policies with seed-dependent, reproducible exploration."""

    mode = "local_policy"

    def __init__(self, seed: int = 7, *, exploration: float = 1.25) -> None:
        if type(seed) is not int or seed < 0:
            raise ValueError("The local policy seed must be a non-negative integer.")
        if not 0 <= exploration <= 3:
            raise ValueError("Local policy exploration must be between 0 and 3.")
        self.seed, self.exploration = seed, exploration
        self._metadata: dict = {}

    def is_live(self, actor: str) -> bool:
        return False

    def decision_metadata(self) -> dict:
        return self._metadata

    def choose(self, actor: str, observation: dict) -> str:
        appointments = observation.get("known_appointments", [])
        planned = (lesson_plan(appointments[0], observation["location_id"], observation["tick"])
                   if actor == "phil" and appointments else None)
        notice_lines = {event["text"] for event in observation["current_evidence"] if event["type"] == "timetable"}
        scenarios = [
            actor, observation["tick"], observation["exchange"], observation["location_id"],
            sorted(observation["present"]), sorted(observation["actions"]),
            [line for line in observation["observations"] if line not in notice_lines],
        ]
        action_values = observation.get("learned_action_values", {})
        choices = []
        for action in observation["actions"]:
            candidate = Candidate(action)
            family = action.partition(":")[0]
            if action == "wait":
                candidate.add(1.0, "Wait for a better opportunity.")
            elif family == "move":
                candidate.add(-0.6, "Walking takes time and may take me away from useful company.")
            if actor == "phil":
                _phil(candidate, observation, planned)
                if past := action_values.get(family):
                    estimate = past["mean"] * past["count"] / (past["count"] + 2)
                    candidate.add(max(-0.8, min(0.8, estimate * 0.55)),
                                  f"Past experience with this action family across {past['count']} attempts.")
            elif actor == "rita":
                _rita(candidate, observation)
            else:
                _crew(candidate, actor, observation)
            random_unit = int(digest([self.seed, scenarios, action])[:8], 16) / 2**32
            exploration = max(0.0, min(self.exploration, candidate.score / 2))
            jitter = round((2 * random_unit - 1) * exploration, 4)
            choices.append((round(candidate.score + jitter, 4), candidate, jitter))

        choices.sort(key=lambda row: (-row[0], row[1].action))
        _, chosen, _ = choices[0]
        prose = [factor for factor in chosen.factors if factor["weight"] > 0]
        reason = max(prose, key=lambda factor: factor["weight"])["reason"] if prose else "Use an available action."
        action = chosen.action
        self._metadata = {
            "policy": self.mode, "policy_version": POLICY_VERSION, "policy_seed": self.seed,
            "ties": "action_id",
            "presented_options": [
                {"action": candidate.action, "utility": candidate.score, "exploration": jitter,
                 "score": score, "factors": candidate.factors, "support": list(candidate.support)}
                for score, candidate, jitter in choices
            ],
            "selected_action": action,
        }
        if planned:
            scheduled_option = next((candidate for _, candidate, _ in choices
                                     if candidate.action == planned["route_action"]
                                     and planned["source_event"] in candidate.support), None)
            if (scheduled_option
                    and action not in {planned["route_action"], "practice_piano"}
                    and planned["projected_lesson_if_wait"] != planned["projected_lesson_if_act_now"]):
                planned["tradeoff"] = {
                    "selected_action": action, "route_action": planned["route_action"],
                    "projected_loss": ("missed_window" if planned["projected_lesson_if_wait"] is None
                                       else "later_lesson"),
                }
            self._metadata["appointment_plan"] = planned
        answer = {"action": action, "reason": reason, "support": list(chosen.support)}
        line = _DIALOGUE[actor].get(action.partition(":")[0])
        if line:
            answer["line"] = line
        if action == "break_pencil":
            answer.update(prediction="If the room resets, the pencil will be whole in the morning.",
                          hypothesis="room_resets", predicted="whole")
        return json.dumps(answer, ensure_ascii=False)
