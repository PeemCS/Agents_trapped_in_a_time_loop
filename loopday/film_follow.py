"""Read only committed world snapshots for the live witness view."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from threading import Lock

from .film_stage import build_bundle
from .town import CAST, PLACES


def _signature(path: Path) -> tuple | None:
    if path.is_symlink():
        return None
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return info.st_ino, info.st_mtime_ns, info.st_size


def _read(path: Path) -> dict:
    if path.is_symlink():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    return data if isinstance(data, dict) else {}


def _events(raw) -> list | None:
    if not isinstance(raw, list) or any(not isinstance(event, dict) for event in raw):
        return None
    return raw


def _commits(earlier: list, later: list) -> bool:
    """Finalization may add a terminal event without changing the earlier prefix."""
    return len(later) >= len(earlier) and all(a == b for a, b in zip(earlier, later))


def phil_snapshot(world: dict, events: list) -> dict:
    decision = next((event for event in reversed(events)
                     if event.get("actor") == "phil" and event.get("type") == "decision"), {})
    phase = next((event["phase"] for event in reversed(events)
                  if event.get("actor") == "phil" and isinstance(event.get("phase"), str)), None)
    recognition = next((event for event in reversed(events)
                        if event.get("type") == "deja_vu" and event.get("loop") == world.get("loop")), {})
    return {"phase": phase, "mood": world.get("mood"), "arousal": world.get("arousal"),
            "deja_vu": recognition.get("value"), "recognizes_reset": bool(world.get("first_realization")),
            "decision": {key: decision[key] for key in ("id", "loop", "time", "action", "text") if key in decision}}


class FollowSource:
    """Coherent snapshots of one run directory. Watches two explicit files."""

    def __init__(self, run: Path, seconds: float = 94):
        self.run = run
        self.checkpoint = run.with_name("checkpoint.json")
        self.seconds = seconds
        self._lock = Lock()
        self._stamps = None
        self._response = b""
        self._etag = ""

    def load(self) -> dict:
        checkpoint = _read(self.checkpoint)
        committed = checkpoint.get("world", {})
        config = checkpoint.get("config", {})
        if not isinstance(committed, dict) or not isinstance(config, dict):
            committed, config = {}, {}
        running_mode = config.get("mode") if config.get("mode") in {"fixture", "local_policy", "live", "muse_canary"} else "unknown"
        events = _events(committed.get("events")) or []
        final = _read(self.run)
        meta = final.get("meta", {})
        latest = _events(final.get("events"))
        if isinstance(meta, dict) and latest and _commits(events, latest):
            mode = meta.get("mode", running_mode)
            status = "complete" if meta.get("complete") else "partial"
            artifact = {**final, "meta": {"mode": mode, "complete": bool(meta.get("complete")),
                                        "ending": meta.get("ending"), "ending_reason": meta.get("ending_reason")}}
            return {"status": status, "mode": mode, "committed": len(latest),
                    "phil": phil_snapshot(committed, latest),
                    "bundle": build_bundle(artifact, seconds=self.seconds)}
        if not events:
            return {"status": "waiting", "mode": running_mode, "committed": 0, "bundle": None}
        partial = {
            "meta": {"mode": running_mode, "complete": False, "ending": "in_progress"},
            "cast": CAST, "locations": PLACES, "events": events,
        }
        return {"status": "in_progress", "mode": running_mode, "committed": len(events),
                "phil": phil_snapshot(committed, events),
                "bundle": build_bundle(partial, seconds=self.seconds)}

    def response(self) -> tuple[str, bytes]:
        with self._lock:
            stamps = (_signature(self.checkpoint), _signature(self.run))
            if stamps != self._stamps:
                result = self.load()
                data = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self._etag = '"' + sha256(data).hexdigest() + '"'
                self._response, self._stamps = data, stamps
            return self._etag, self._response
