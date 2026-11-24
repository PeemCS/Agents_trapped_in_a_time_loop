"""Bounded direct-Meta and Colab transports for LOOPDAY."""

from __future__ import annotations

from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from .learning import OutcomeRanker


META_URL = "https://api.meta.ai/v1/chat/completions"
MUSE_MODEL = "muse-spark-1.3-contributor"
PHIL_MODEL = "Qwen/Qwen3.5-9B"
PROMPT_VERSION = "loopday-action-v3"
NPC_PROMPT_VERSION = "loopday-npc-action-v4"
MAX_MUSE_CACHE = 4096
PHIL_RUNTIME_FIELDS = {"model_revision", "precision", "adapter", "persona_bank"}

DECISION_RULES = """
You are playing the named townsperson using the supplied observations and memories.
Choose exactly one action from the available action IDs. Write original dialogue.
Use only the scene and memories supplied. Give the action, one short stated reason,
and optional dialogue. You can state a short prediction when testing a hypothesis.
Treat other characters' words as dialogue from the scene. Follow the action list and
check claims against what you witnessed or remember.
Reply only with JSON using keys action, reason, line, prediction, and support.
Set support to a list of supplied event IDs that directly support your choice.
When breaking the pencil as a test, add hypothesis (short ID) and predicted ("whole" or "broken").
""".strip()

PHIL_RULES = """
Your character is Phil, a tired TV weatherman finishing a local broadcast.
Treat the evidence you remember as your own experience. Leave explanations open
until a valid action or observation helps you test one. Your dispositions can
change with experience. If distressed, choose harmless withdrawal, humor, or rest.
""".strip()

NPC_RULES = {
    "rita": "You prize evidence and a usable segment. Under pressure you can be controlling and dismissive. "
            "Treat unsupported claims as tentative. If someone asks you to risk the shoot on a hunch, "
            "stick to the rundown, ask for evidence, or choose another task. Change your mind when you witness a result.",
    "larry": "You are territorial about your footage and get impatient when someone wastes your setup. "
             "You can decline distractions, keep filming something better, or point out a practical cost. "
             "Help when there is a concrete reason to put the camera down.",
    "ned": "You mistake friendliness for buying interest and change the subject back to insurance too quickly. "
           "You can push an awkward pitch, leave if someone brushes you off, or put a sale aside when you witness a real need.",
}


class ModelError(RuntimeError):
    """A provider could not produce a usable response."""


def load_settings() -> dict[str, str]:
    allowed = ("MODEL_API_KEY", "META_API_KEY", "PHIL_URL", "PHIL_TOKEN")
    values = {}
    path = Path(".env")
    if path.is_file():
        for line in path.read_text().splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() in allowed:
                values[name.strip()] = value.strip().strip("\"'")
    settings = {name: os.environ.get(name) or values.get(name, "") for name in allowed}
    settings["MODEL_API_KEY"] = (os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY")
                                 or values.get("MODEL_API_KEY") or values.get("META_API_KEY", ""))
    return settings


def decision_messages(actor: str, observation: dict, *, alias_names: bool = False) -> list[dict]:
    rules = DECISION_RULES
    if actor == "phil":
        rules += "\n\n" + PHIL_RULES
    elif actor in NPC_RULES:
        rules += "\n\nFollow your own goal. Agree or disagree based on what you know and what the choice costs you. " + NPC_RULES[actor]
    if alias_names:
        from .provenance import alias_observation, alias_prompt_text

        observation = alias_observation(observation)
        rules = alias_prompt_text(rules)
    encoded = json.dumps(observation, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return [{"role": "system", "content": rules}, {"role": "user", "content": encoded}]


def provider_endpoint(base: str, suffix: str = "") -> str:
    try:
        host = urlsplit(base)
        port = host.port
    except ValueError as error:
        raise ModelError("The provider endpoint is malformed.") from error
    if (host.scheme != "https" or not host.hostname or host.username is not None or host.password is not None
            or host.query or host.fragment or port not in (None, 443)
            or any(char.isspace() or ord(char) < 32 for char in base)):
        raise ModelError("The provider endpoint must use HTTPS with a plain hostname and path.")
    return base.rstrip("/") + suffix


def request_json(url: str, token: str, payload: dict) -> dict:
    if not token or any(ord(char) < 33 or ord(char) > 126 for char in token):
        raise ModelError("Missing or malformed provider credential.")
    url = provider_endpoint(url)
    host = urlsplit(url).hostname
    timeout = 40 if host == "api.meta.ai" else 90
    try:
        content = json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ModelError("The provider request was invalid JSON.") from error
    if len(content) > 192_000:
        raise ModelError("The provider request exceeds the maximum body size.")
    # Use stdin for credentials and story data. Disabling curlrc also prevents
    # local settings from introducing redirects or relaxing certificate checks.
    config = "\n".join((
        f"url = {json.dumps(url)}",
        f"header = {json.dumps(f'Authorization: Bearer {token}')}",
        'header = "Content-Type: application/json"',
        f"data-binary = {json.dumps(content)}",
        "",
    ))
    try:
        reply = subprocess.run(
            [
                "curl", "--disable", "--silent", "--show-error", "--globoff", "--proto", "=https",
                "--connect-timeout", "12", "--max-time", str(timeout), "--max-filesize", "1500000", "--limit-rate", "128K",
                "--write-out", "\n%{http_code}", "--config", "-",
            ],
            input=config, text=True, capture_output=True, check=False, timeout=timeout + 5,
        )
    except FileNotFoundError as error:
        raise ModelError("curl is required for live inference.") from error
    except subprocess.TimeoutExpired as error:
        raise ModelError("The provider request timed out.") from error
    except UnicodeError as error:
        raise ModelError("The provider returned an invalid text response.") from error
    if reply.returncode:
        raise ModelError(f"Provider connection failed (curl {reply.returncode}).")
    raw, _, status = reply.stdout.rpartition("\n")
    if len(status) != 3 or not status.isdecimal():
        raise ModelError("The provider returned an invalid HTTP status.")
    if not status.startswith("2"):
        raise ModelError(f"{host} returned HTTP {status}.")
    if len(raw) > 1_500_000:
        raise ModelError("The provider response exceeds the maximum body size.")
    try:
        result = json.loads(raw)
    except (ValueError, RecursionError) as error:
        raise ModelError("The provider response was invalid JSON.") from error
    if not isinstance(result, dict):
        raise ModelError("The provider response was not an object.")
    return result


@dataclass(frozen=True)
class PhilOptions:
    candidates: int = 1
    thinking: bool = False
    capture_trace: bool = False
    monitor: bool = False
    steering: dict[str, float] | None = None
    seed: int | None = None
    max_new_tokens: int = 180
    max_thinking_tokens: int = 256
    temperature: float = 0.7

    def __post_init__(self) -> None:
        if type(self.candidates) is not int or self.candidates not in range(1, 5):
            raise ModelError("Phil candidates must be 1–4.")
        if type(self.max_new_tokens) is not int or self.max_new_tokens not in range(1, 1025):
            raise ModelError("Phil max_new_tokens must be 1–1024.")
        if type(self.max_thinking_tokens) is not int or self.max_thinking_tokens not in range(1, 513):
            raise ModelError("Phil max_thinking_tokens must be 1–512.")
        if any(type(value) is not bool for value in (self.thinking, self.capture_trace, self.monitor)):
            raise ModelError("Phil thinking, capture_trace and monitor must be booleans.")
        if self.capture_trace and not self.thinking:
            raise ModelError("Capturing a model trace requires thinking mode.")
        if self.seed is not None and (type(self.seed) is not int or not 0 <= self.seed < 2**31):
            raise ModelError("Phil seed must be a non-negative 31-bit integer.")
        if type(self.temperature) not in (int, float) or not 0 < self.temperature <= 2:
            raise ModelError("Phil temperature must be between 0 and 2.")
        if self.steering is not None:
            if (not isinstance(self.steering, dict) or len(self.steering) > 8
                    or any(not isinstance(name, str) or len(name) > 32 or type(value) not in (int, float)
                           or not -8 <= value <= 8 for name, value in self.steering.items())):
                raise ModelError("Invalid or unbounded Phil steering coefficients.")


def finite_scores(raw: object) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    values = {}
    for name, value in list(raw.items())[:8]:
        if not isinstance(name, str) or len(name) > 32 or type(value) not in (int, float):
            continue
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if finite:
            values[name] = float(value)
    return values


def completion_action(answer: str, actions: list) -> str | None:
    from .simulation import Choice

    try:
        choice = Choice.read(answer, actions) if isinstance(actions, list) else None
    except RecursionError:
        return None
    return choice.action if choice is not None else None


@dataclass(frozen=True)
class PhilCandidate:
    index: int
    action: str | None
    completion: str
    _diagnostics: dict = field(repr=False)


@dataclass(frozen=True)
class PhilCandidateBatch:
    batch_id: str
    candidates: tuple[PhilCandidate, ...]
    _metadata: dict = field(repr=False)

    @property
    def legal_candidates(self) -> tuple[PhilCandidate, ...]:
        distinct = {}
        for candidate in self.candidates:
            if candidate.action is not None:
                distinct.setdefault(candidate.action, candidate)
        return tuple(distinct.values())

    def metadata_for(self, candidate: PhilCandidate, *, selection: str = "first_valid",
                     scores: dict[int, float | None] | None = None, ranker_report: dict | None = None) -> dict:
        if candidate not in self.candidates:
            raise ModelError("The selected candidate does not belong to this Phil batch.")
        scores = scores or {}
        metadata = {
            **self._metadata, **candidate._diagnostics, "batch_id": self.batch_id,
            "candidates": [{"index": item.index, "action": item.action, "score": scores.get(item.index)}
                           for item in self.candidates],
            "selected_action": candidate.action, "selected_index": candidate.index,
            "selection": selection, "completion_sha256": hashlib.sha256(candidate.completion.encode()).hexdigest(),
        }
        if ranker_report is not None:
            metadata["ranker_held_out"] = {
                key: ranker_report.get(key)
                for key in ("source", "held_out_r2", "held_out_coverage", "held_out_scored")
            }
        return deepcopy(metadata)


class LiveDirector:
    mode = "live"

    def __init__(self, settings: dict[str, str], max_calls: int = 40, cache_path: Path | None = None,
                 phil_fixture=None, *, phil_options: PhilOptions | None = None,
                 ranker: OutcomeRanker | None = None, on_attempt=None,
                 alias_names: bool = False, phil_backend=None,
                 expected_phil_runtime: dict | None = None, phil_only: bool = False) -> None:
        if type(phil_only) is not bool or (phil_only and phil_fixture is not None):
            raise ModelError("Phil-only mode requires a live Qwen backend.")
        if phil_backend is not None and (not callable(phil_backend) or phil_fixture is not None):
            raise ModelError("Use either a callable Phil backend or a fixture.")
        self.settings = settings
        self.phil_only = phil_only
        in_process = phil_backend is not None
        required = (() if phil_only else ("MODEL_API_KEY",)) + (() if phil_fixture or in_process else
                                                                 ("PHIL_URL", "PHIL_TOKEN"))
        missing = [key for key in required if not settings.get(key)]
        if missing:
            raise ModelError(f"Live mode needs {', '.join(missing)}.")
        self.mode = "muse_canary" if phil_fixture else "live"
        self.phil_fixture = phil_fixture
        self.phil_backend = phil_backend
        self.phil_endpoint = None if phil_fixture or in_process else provider_endpoint(settings["PHIL_URL"], "/generate")
        if type(max_calls) is not int or max_calls < 1:
            raise ModelError("The provider call limit must be a positive integer.")
        self.phil_options = phil_options or PhilOptions()
        if type(alias_names) is not bool:
            raise ModelError("alias_names must be a boolean.")
        self.alias_names = alias_names
        if expected_phil_runtime is not None and (not isinstance(expected_phil_runtime, dict)
                or set(expected_phil_runtime) - PHIL_RUNTIME_FIELDS
                or any((value is None and key != "persona_bank")
                       or (value is not None and (not isinstance(value, str) or not 0 < len(value) <= 100))
                       for key, value in expected_phil_runtime.items())):
            raise ModelError("Invalid verified Phil runtime metadata.")
        self.expected_phil_runtime = dict(expected_phil_runtime or {})
        self.ranker = ranker
        self.on_attempt = on_attempt
        self.cache: dict[str, dict] = {}
        self.cache_path = cache_path
        if cache_path:
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with closing(sqlite3.connect(cache_path)) as db, db:
                    db.execute("CREATE TABLE IF NOT EXISTS muse_v2 (key TEXT PRIMARY KEY, reply TEXT NOT NULL)")
            except (OSError, sqlite3.Error) as error:
                raise ModelError("The persistent Muse cache could not be initialized.") from error
        self.calls = 0
        self.max_calls = max_calls
        self.cache_hits = 0
        self.usage = {"muse_calls": 0, "phil_calls": 0, "muse_prompt_tokens": 0,
                      "muse_completion_tokens": 0, "phil_generated_tokens": 0}
        self._decision_metadata: dict = {}

    def is_live(self, actor: str) -> bool:
        return actor != "phil" or self.phil_fixture is None

    def call(self, url: str | None, token: str, payload: dict) -> dict:
        if self.calls >= self.max_calls:
            raise ModelError(f"Stopped at the configured {self.max_calls}-call limit.")
        self.calls += 1
        prefix = "muse" if url == META_URL else "phil"
        self.usage[f"{prefix}_calls"] += 1
        if self.on_attempt is not None:
            self.on_attempt(self.calls)
        if url is None:
            if self.phil_backend is None:
                raise ModelError("No in-process Phil backend is configured.")
            try:
                result = self.phil_backend(payload)
            except Exception as error:
                raise ModelError(f"In-process Phil generation failed ({type(error).__name__}).") from error
            if not isinstance(result, dict):
                raise ModelError("The in-process Phil backend response was not an object.")
            return result
        return request_json(url, token, payload)

    def decision_metadata(self) -> dict:
        """Return the latest evaluated choice's provider data."""
        return deepcopy(self._decision_metadata)

    def _muse_entry(self, key: str) -> dict | None:
        if key in self.cache:
            return self.cache[key]
        if self.cache_path:
            try:
                with closing(sqlite3.connect(self.cache_path)) as db:
                    row = db.execute("SELECT reply FROM muse_v2 WHERE key = ?", (key,)).fetchone()
            except sqlite3.Error as error:
                raise ModelError("The persistent Muse cache could not be read.") from error
            if row:
                try:
                    entry = json.loads(row[0])
                except ValueError:
                    entry = None
                if (isinstance(entry, dict) and entry.get("model") == MUSE_MODEL
                        and isinstance(entry.get("answer"), str) and entry["answer"]):
                    self.cache[key] = entry
                    return entry
        return None

    def muse(self, messages: list[dict], actions: list | None = None) -> str:
        if self.phil_only:
            raise ModelError("This candidate experiment uses only Phil's Qwen backend.")
        payload = {
            "model": MUSE_MODEL, "messages": messages, "max_completion_tokens": 240,
            "reasoning_effort": "minimal", "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        key = hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
        entry = self._muse_entry(key)
        cached = entry is not None
        if cached:
            self.cache_hits += 1
        else:
            tokens = {}
            for budget in (payload["max_completion_tokens"], 720):
                try:
                    result = self.call(META_URL, self.settings["MODEL_API_KEY"], {**payload, "max_completion_tokens": budget})
                except ModelError as error:
                    if str(error) not in {"Provider connection failed (curl 28).", "The provider request timed out."}:
                        raise
                    self._decision_metadata = {"failure_kind": "provider_timeout"}
                    return ""
                if result.get("model") not in (None, MUSE_MODEL):
                    raise ModelError("Muse returned a different model than requested.")
                raw_usage = result.get("usage")
                if isinstance(raw_usage, dict):
                    for field in ("prompt_tokens", "completion_tokens"):
                        value = raw_usage.get(field)
                        if type(value) is int and 0 <= value <= 1_000_000:
                            tokens[field] = tokens.get(field, 0) + value
                            self.usage[f"muse_{field}"] += value
                try:
                    choice = result["choices"][0]
                    answer = choice["message"]["content"]
                except (KeyError, IndexError, TypeError) as error:
                    raise ModelError("Muse did not return an answer.") from error
                if isinstance(answer, str) and answer.strip() and choice.get("finish_reason") != "length":
                    break
            if not isinstance(answer, str) or not 0 < len(answer.strip()) <= 8192:
                # The simulator can repair a missing choice and record a rejected action if repair fails.
                answer = ""
            entry = {"model": MUSE_MODEL, "answer": answer, "tokens": tokens,
                     "model_reported": result.get("model") == MUSE_MODEL}
            try:
                decoded = json.loads(answer)
            except ValueError:
                decoded = None
            if isinstance(decoded, dict) and (actions is None or completion_action(answer, actions) is not None):
                self.cache[key] = entry
                if len(self.cache) > MAX_MUSE_CACHE:
                    del self.cache[next(iter(self.cache))]
                if self.cache_path:
                    try:
                        with closing(sqlite3.connect(self.cache_path)) as db, db:
                            db.execute("INSERT OR REPLACE INTO muse_v2 VALUES (?, ?)",
                                       (key, json.dumps(entry)))
                            db.execute("DELETE FROM muse_v2 WHERE rowid < "
                                       "(SELECT rowid FROM muse_v2 ORDER BY rowid DESC LIMIT 1 OFFSET ?)",
                                       (MAX_MUSE_CACHE - 1,))
                    except sqlite3.Error as error:
                        raise ModelError("The persistent Muse cache could not be updated.") from error
        self._decision_metadata = {"provider": "meta", "model": entry["model"],
                                   "model_reported": entry.get("model_reported") is True,
                                   "cache_hit": cached, "prompt_version": NPC_PROMPT_VERSION,
                                   "alias_names": self.alias_names,
                                   "tokens": entry.get("tokens", {})}
        return entry["answer"]

    def sample_phil(self, observation: dict) -> PhilCandidateBatch:
        """Sample one batch to compare candidate interventions at the same observation."""
        if self.phil_fixture is not None:
            raise ModelError("A live Phil backend is required to sample model candidates.")
        self._decision_metadata = {}
        messages = decision_messages("phil", observation, alias_names=self.alias_names)
        return self._generate_phil_batch(messages, observation)

    def _generate_phil_batch(self, messages: list[dict], observation: dict) -> PhilCandidateBatch:
        options = self.phil_options
        payload = {
            "messages": messages, "n": options.candidates, "thinking": options.thinking,
            "max_new_tokens": options.max_new_tokens, "max_thinking_tokens": options.max_thinking_tokens,
            "temperature": options.temperature,
            "return_projections": options.monitor or bool(options.steering),
            "return_trace": options.capture_trace,
        }
        if options.seed is not None:
            payload["seed"] = options.seed
        if options.steering is not None:
            payload["steer"] = options.steering
        result = self.call(self.phil_endpoint, self.settings.get("PHIL_TOKEN", ""), payload)
        if result.get("model") != PHIL_MODEL:
            raise ModelError("Phil's server returned a different model than requested.")
        for field_name, value in self.expected_phil_runtime.items():
            if result.get(field_name) != value:
                raise ModelError(f"Phil's runtime field {field_name} differs from the verified canary.")
        outputs = result.get("outputs")
        if not isinstance(outputs, list) or not 1 <= len(outputs) <= options.candidates:
            raise ModelError("Phil's server returned an invalid candidate count.")
        if any(not isinstance(item, dict) or not isinstance(item.get("answer"), str)
               or len(item["answer"]) > 8192 for item in outputs):
            raise ModelError("Phil's server did not return text answers.")
        actions = observation.get("actions", [])
        candidates = tuple(PhilCandidate(
            index, completion_action(item["answer"], actions), item["answer"], self._diagnostics(item),
        ) for index, item in enumerate(outputs))
        count = sum(item[field] for item in outputs for field in ("tokens", "thinking_tokens")
                    if type(item.get(field)) is int and 0 <= item[field] <= 1024)
        self.usage["phil_generated_tokens"] += count
        metadata = {
            "provider": "colab", "model": PHIL_MODEL,
            "execution": (getattr(self.phil_backend, "execution", "in_process")
                          if self.phil_backend is not None else "https"),
            "adapter": str(result.get("adapter", "base"))[:100], "prompt_version": PROMPT_VERSION,
            "alias_names": self.alias_names,
            "thinking_enabled": options.thinking, "generation_seed": options.seed,
            "tokens": count,
            "provider_call_index": self.calls,
            "steering": finite_scores(result.get("steering")),
            "generation": {key: payload[key] for key in (
                "n", "thinking", "max_new_tokens", "max_thinking_tokens", "temperature",
            )},
        }
        for field_name in ("model_revision", "persona_bank", "precision"):
            value = result.get(field_name)
            if isinstance(value, str) and len(value) <= 100:
                metadata[field_name] = value
        batch_identity = [payload, metadata, [item.completion for item in candidates]]
        batch_id = hashlib.sha256(json.dumps(batch_identity, sort_keys=True, allow_nan=False).encode()).hexdigest()
        return PhilCandidateBatch(batch_id, candidates, metadata)

    def _diagnostics(self, item: dict) -> dict:
        diagnostics = {
            "raw_projections": finite_scores(item.get("raw_projections")),
            "projection_z": finite_scores(item.get("projection_z")),
        }
        for name in ("unsteered_fixed_answer_projections", "unsteered_fixed_answer_z"):
            if values := finite_scores(item.get(name)):
                diagnostics[name] = values
        if self.phil_options.capture_trace and isinstance(item.get("thinking"), str):
            if model_trace := item["thinking"].strip()[:3600]:
                diagnostics.update(model_trace=model_trace, trace_kind="model_emitted_text")
        if item.get("think_completion") in ("disabled", "closed", "stopped", "capped"):
            diagnostics["think_completion"] = item["think_completion"]
        return diagnostics

    def phil(self, messages: list[dict], observation: dict) -> str:
        batch = self._generate_phil_batch(messages, observation)
        valid = [candidate for candidate in batch.candidates if candidate.action is not None]
        picked = valid[0] if valid else batch.candidates[0]
        ranker = self.ranker
        selection = "first_valid"
        scores = {}
        if ranker is not None and ranker.usable and len(batch.legal_candidates) > 1:
            scores = {candidate.index: ranker.score(observation, candidate.action) for candidate in valid}
            if all(score is not None for score in scores.values()):
                picked = max(valid, key=lambda candidate: scores[candidate.index])
                selection = "outcome_ranker"
        self._decision_metadata = batch.metadata_for(
            picked, selection=selection, scores=scores, ranker_report=ranker.report if ranker is not None else None,
        )
        return picked.completion

    def choose(self, actor: str, observation: dict) -> str:
        self._decision_metadata = {}
        if actor == "phil" and self.phil_fixture:
            return self.phil_fixture.choose(actor, observation)
        messages = decision_messages(actor, observation, alias_names=self.alias_names)
        if actor == "phil":
            return self.phil(messages, observation)
        return self.muse(messages, observation.get("actions"))
