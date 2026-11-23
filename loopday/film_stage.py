"""Translate replay events to camera, cast, and prop cues."""

from __future__ import annotations

from typing import Any

from .film import SPEAKING_TYPES, build_film, cast_member, shot_style, text_for
from .film_art import build_art
from .town import ROADS


CAMERAS = {
    "clock": ([.38, 1.80, 2.62], [.01, 1.45, -.25], 30),
    "insert": ([1.20, 2.43, 2.26], [.32, 1.31, -.24], 33),
    "puddle": ([3.62, 1.42, 5.85], [-1.00, .84, .46], 43),
    "tree": ([3.00, 2.72, 6.08], [-.68, 1.54, 1.07], 38),
    "road": ([7.1, 3.65, 10.38], [-.64, 1.10, -1.42], 47),
    "square": ([5.22, 3.28, 8.52], [.00, 1.64, -1.52], 43),
    "piano": ([3.92, 2.68, 6.36], [-.53, 1.17, .07], 36),
    "ballroom": ([6.7, 3.2, 9.3], [0, 1.28, .02], 49),
    "two_shot": ([2.22, 2.14, 5.97], [0, 1.41, -.04], 42),
    "walk": ([5.82, 3.09, 7.31], [0, 1.18, .06], 43),
    "night": ([4.02, 2.37, 5.6], [0, 1.27, -.42], 45),
    "street": ([4.07, 2.54, 7.42], [0, 1.27, -.39], 46),
}
INTERIORS = {"inn", "hotel", "piano_teacher", "diner"}
PRIVATE_FIELDS = {
    "api_key", "authorization", "completion", "credential", "credentials", "password", "policy_observation",
    "prompt", "raw_model_output", "secret", "system_prompt", "token",
}
TRACE_FIELDS = {"model_reasoning", "model_trace", "reasoning_text", "reasoning_trace", "thinking", "trace", "trace_kind"}


def _color_state(set_name: str, tick: int, storm: bool) -> dict:
    if set_name == "inn":
        return {"sky": "#6e8794", "light": "#f1bf8c", "ambient": .81}
    if set_name == "hotel":
        return {"sky": "#372b3b", "light": "#f7ae70", "ambient": .86}
    if set_name == "piano_teacher":
        return {"sky": "#7b8c8e", "light": "#efc49e", "ambient": .85}
    if set_name == "diner":
        return {"sky": "#536c73", "light": "#efba86", "ambient": .88}
    if storm:
        return {"sky": "#758ca3", "light": "#acbbd6", "ambient": .84}
    if tick >= 26:
        return {"sky": "#4b5f78", "light": "#99a8c7", "ambient": .77}
    if tick < 4:
        return {"sky": "#9db9c9", "light": "#ffe1b1", "ambient": .94}
    return {"sky": "#afc4d0", "light": "#e0dac2", "ambient": .94}


def _stage_cast(positions: dict, location: str, actor: str | None, event: dict, camera: str,
                locations: dict) -> list[dict]:
    if camera == "clock":
        return []
    members = [key for key, place in positions.items() if place == location]
    if actor in members:
        members.remove(actor)
        members.insert(0, actor)
    to = event.get("to")
    if isinstance(to, list):
        to = to[0] if to else None
    if isinstance(to, str) and to in members and to != actor:
        members.remove(to)
        members.insert(1, to)
    cast = []
    for index, character in enumerate(members):
        x = (-.60, .84, -1.88, 1.92)[index % 4] + (index // 4) * .40
        z = .37 - .2 * min(index, 3)
        yaw = .20 if index % 2 == 0 else -.63
        if location == "hotel" and camera in {"ballroom", "two_shot"}:
            x += 1.6
            z += 1.58
        if location == "inn":
            x += 1.75
            z += .46
        if location == "knob":
            x -= 1.22
            z += 1.81
        if location in {"country_rd", "outskirts"}:
            x += 1.50
            z += 2.07
        speaking = event.get("type") in SPEAKING_TYPES or event.get("anchor") == "ned_greeting"
        pose = "talk" if character == actor and speaking else "idle"
        if character == to and actor != to and speaking:
            pose = "listen"
        if character == "larry" and camera == "square":
            pose = "aim_camera"
        if camera == "piano":
            if character == "phil":
                x, z, yaw, pose = -.22, .92, 3.14, "play"
            else:
                x, z = 1.5 + index * .64, .45 + index * .21
        if camera == "puddle" and character == "phil":
            x, z, yaw, pose = -.36, .88, 1.40, "walk"
        if camera == "insert" and character == "phil":
            pose, x, z = "reach", 1.14, -.16
        approach = None
        if event.get("type") == "position" and character == actor:
            pose = "walk"
            origin = locations.get(event.get("moving_from"), {})
            target = locations.get(location, {})
            if all(isinstance(point.get(coord), (int, float)) for point in (origin, target) for coord in ("x", "z")):
                dx, dz = origin["x"] - target["x"], origin["z"] - target["z"]
                scale = max(1, abs(dx) + abs(dz))
                approach = [3.8 * dx / scale, 2.3 * dz / scale]
        if event.get("type") == "exit" and event.get("state") == "left_town" and character == actor:
            pose = "walk"
            approach = [-2.5, 2.5]
        if event.get("type") in {"kindness", "kindness_offered"} and character == actor:
            pose = "walk" if event.get("subject") == "old_man_cold" else "reach"
        if camera == "tree" and event.get("type") == "kindness" and character == actor:
            x, z, yaw, pose = -.53, .89, -1.39, "lift"
        cast.append({"actor": character, "x": x, "z": z, "yaw": yaw, "pose": pose, "approach": approach})
    if event.get("subject") == "old_man_cold" and event.get("status") != "resolved_unhelped":
        walking = event.get("type") == "kindness"
        cast.append({"actor": "older_man", "x": .72, "z": .22, "yaw": .35 if walking else -.58,
                     "pose": "walk" if walking else "idle", "approach": [-1.65, .38] if walking else None})
    if camera == "tree" and event.get("status") != "resolved_unhelped":
        cast.append({"actor": "child", "x": -.95, "z": 1.12, "yaw": .5, "scale": .57, "elevation": 2.05,
                     "pose": "descend" if event.get("type") == "kindness" else "idle"})
    return cast


def compile_stages(run: dict) -> list[dict[str, Any]]:
    """Stage every source event, including events skipped in the film cut."""
    positions: dict[str, str] = {}
    modes: dict[str, str] = {}
    last_loop: int | None = None
    pencil = "whole"
    storm = False
    screens = []
    for index, event in enumerate(run["events"]):
        loop, kind, tick = event.get("loop", 1), event.get("type"), event.get("tick", 0)
        actor = event.get("actor", event.get("agent", event.get("speaker")))
        if last_loop != loop or kind == "day_start":
            last_loop = loop
            modes.clear()
            pencil, storm = "whole", False
        if isinstance(event.get("positions"), dict):
            positions.update(event["positions"])
        if kind == "position" and actor and event.get("location"):
            positions[actor] = event["location"]
        if kind in {"decision", "npc_mode", "divergence"} and actor:
            mode = event.get("npc_mode") or event.get("mode")
            if kind == "divergence" and not mode:
                mode = "changed"
            if isinstance(mode, str):
                modes[actor] = mode
        if kind in {"pencil", "test_result", "experiment_result"} and event.get("state") in {"broken", "whole"}:
            pencil = event["state"]
        if kind == "anchor" and event.get("anchor") in {"snow", "blizzard"}:
            storm = True
        camera, duration, sound = shot_style(event)
        if camera == "clock":
            location = "inn"
        elif kind == "night":
            location = positions.get("phil", "inn")
        else:
            location = event.get("location") or positions.get(actor) or positions.get("phil") or "main_st"
        set_name = location if location in {
            "inn", "main_st", "diner", "knob", "country_rd", "hotel", "piano_teacher", "alley", "outskirts",
        } else "main_st"
        if camera == "tree":
            set_name = "rescue_tree"
        eye, look, field = CAMERAS[camera]
        if camera == "two_shot" and set_name == "hotel":
            eye = [eye[0] + 1.7, eye[1], eye[2] + 1.5]
            look = [look[0] + 1.7, look[1], look[2] + 1.5]
        if camera == "night" and set_name == "inn":
            eye, look, field = CAMERAS["insert"]
        stage_cast = _stage_cast(positions, location, actor, event, camera, run.get("locations", {}))
        line = text_for(event)
        avoided = event.get("avoided", {"dry": True, "wet": False}.get(event.get("state")))
        if kind == "puddle" and avoided is None:
            avoided = "around" in line.lower() or "avoid" in line.lower()
        tag = run.get("locations", {}).get(location, {})
        weather = _color_state(set_name, tick, storm)
        if event.get("ending_reason") == "community_recognition" and kind == "day_two":
            weather = {"sky": "#769fb6", "light": "#fed297", "ambient": .98}
        screens.append({
            "event_index": index, "location": location,
            "label": tag.get("label", location) if isinstance(tag, dict) else str(tag),
            "set": set_name, "camera": camera, "eye": eye, "look": look, "fov": field,
            "cast": stage_cast, "positions": positions.copy(), "modes": modes.copy(),
            "pencil": pencil, "storm": storm and set_name not in INTERIORS,
            "flurry": 1.0 if storm and set_name not in INTERIORS else (0.28 if set_name not in INTERIORS else 0.0),
            "barrier": storm or event.get("state") == "blocked", "weather": weather,
            "splash": kind == "puddle" and not avoided,
            "opening": camera == "clock" and kind != "day_two",
            "tomorrow": kind == "day_two",
            "time": event.get("time", "06:00"),
            "switch_radio": kind == "day_two" and "radio" in line.casefold() and "rita" in line.casefold(),
            "subtitle": line if kind not in {"decision", "day_start"} and camera != "clock" else "",
            "speaker": cast_member(run, actor) if kind in SPEAKING_TYPES or event.get("anchor") == "ned_greeting" else "",
            "branch_breaks": camera == "tree" and event.get("status") == "resolved_unhelped",
            "sound": sound, "duration_ms": duration,
        })
    return screens


def build_bundle(run: dict, *, seconds: float = 94, model_traces: bool = False) -> dict:
    """Package a replay without including raw model traces by default."""
    replay = {key: run[key] for key in ("meta", "cast", "locations") if key in run}
    replay["events"] = run.get("events")
    replay = _public_data(replay, model_traces)
    film = build_film(replay, seconds)
    roads = sorted({tuple(sorted((origin, destination))) for origin, neighbors in ROADS.items() for destination in neighbors})
    return {"run": replay, "film": film, "stages": compile_stages(replay), "art": build_art(), "roads": roads}


def _public_data(value: Any, model_traces: bool = False) -> Any:
    if isinstance(value, list):
        return [_public_data(item, model_traces) for item in value]
    if isinstance(value, dict):
        hidden = PRIVATE_FIELDS if model_traces else PRIVATE_FIELDS | TRACE_FIELDS
        return {key: _public_data(item, model_traces) for key, item in value.items() if key.casefold() not in hidden}
    return value


def source_label(source: dict, *, still: bool = False) -> str:
    if source.get("mode") == "fixture":
        return "Fixture still" if still else "Fixture film"
    if source.get("mode") == "local_policy":
        if not source.get("complete"):
            return "Partial local run"
        return "Local policy still" if still else "Local policy film"
    if source.get("mode") == "muse_canary":
        return "Muse canary · fixture Phil"
    if source.get("mode") in ("live", "live-canary"):
        return "" if source.get("complete") else "Partial live run"
    return "Replay"
