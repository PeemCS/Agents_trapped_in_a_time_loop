"""Keep replay artifacts atomic and reserve live calls before sending them."""

from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile


class RunStorageError(ValueError):
    """A run directory could not be opened safely."""


def write_text(path: Path, text: str) -> None:
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)


def write_json(path: Path, data: object) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RunStorageError(f"Expected a JSON object in {path.name}.")
    return value


@contextmanager
def exclusive_run(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    with (path / ".run.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RunStorageError("This output directory already has an active process.") from error
        yield


class CallJournal:
    """Store the highest reserved call separately from the world checkpoint."""

    def __init__(self, path: Path):
        self.path = path

    @staticmethod
    def validate(counters: object) -> dict:
        if not isinstance(counters, dict):
            raise RunStorageError("Invalid provider counters.")
        calls, hits, usage = counters.get("calls"), counters.get("cache_hits", 0), counters.get("usage", {})
        if (type(calls) is not int or calls < 0 or type(hits) is not int or hits < 0
                or not isinstance(usage, dict)
                or any(type(value) is not int or value < 0 for value in usage.values())):
            raise RunStorageError("Invalid provider counters.")
        return {"calls": calls, "cache_hits": hits, "usage": usage}

    @staticmethod
    def counters(director) -> dict:
        return {"calls": getattr(director, "calls", 0), "cache_hits": getattr(director, "cache_hits", 0),
                "usage": dict(getattr(director, "usage", {}))}

    def reserve(self, director, count: int) -> None:
        counters = self.counters(director)
        if counters["calls"] != count:
            raise RunStorageError("The provider reservation is out of sequence.")
        write_json(self.path, counters)

    def restore(self, director, checkpoint: dict) -> None:
        previous = self.validate(checkpoint.get("provider", {
            "calls": checkpoint.get("provider_calls", 0),
            "cache_hits": checkpoint.get("provider_cache_hits", 0),
        }))
        if self.path.exists():
            reserved = self.validate(read_json(self.path))
            if reserved["calls"] >= previous["calls"]:
                previous = {"calls": reserved["calls"],
                            "cache_hits": max(previous["cache_hits"], reserved["cache_hits"]),
                            "usage": {name: max(previous["usage"].get(name, 0), reserved["usage"].get(name, 0))
                                      for name in director.usage}}
        director.calls = previous["calls"]
        director.cache_hits = previous["cache_hits"]
        director.usage.update({name: previous["usage"].get(name, 0) for name in director.usage})
