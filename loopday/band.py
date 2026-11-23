"""Optional Band transport for in-world messages addressed to specific characters."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
from uuid import UUID

from .run_storage import read_json, write_json
from .town import CAST


API = "https://api.band.ai/api/v1/agent"


class BandError(ValueError):
    """Band configuration or transport failed."""


def uuid(value: object) -> str:
    try:
        return str(UUID(str(value)))
    except ValueError as error:
        raise BandError("Band room, participant and message IDs must be UUIDs.") from error


@dataclass(frozen=True)
class Identity:
    id: str
    handle: str
    name: str
    token: str = field(repr=False)

    def mention(self) -> dict[str, str]:
        return {"id": self.id, "handle": self.handle, "name": self.name}


def band_request(url: str, actor: Identity, *, method: str, payload: dict | None = None) -> dict:
    config = [f"url = {json.dumps(url)}", f"header = {json.dumps(f'X-API-Key: {actor.token}')}",
              f"request = {json.dumps(method)}"]
    if payload is not None:
        config.extend(('header = "Content-Type: application/json"', f"data-binary = {json.dumps(json.dumps(payload))}"))
    try:
        response = subprocess.run(
            ["curl", "--disable", "--silent", "--proto", "=https", "--connect-timeout", "3", "--max-time", "5",
             "--max-filesize", "500000", "--write-out", "\n%{http_code}", "--config", "-"],
            input="\n".join(config) + "\n", text=True, capture_output=True, check=False, timeout=6,
        )
        body, _, status = response.stdout.rpartition("\n")
        if response.returncode or status != "200":
            raise BandError("Band did not confirm the operation.")
        result = json.loads(body)
        if not isinstance(result, dict):
            raise BandError("Band returned an unexpected response.")
    except (OSError, subprocess.TimeoutExpired, UnicodeError, json.JSONDecodeError) as error:
        raise BandError("Band could not complete the operation.") from error
    return result


def identities(config: dict) -> tuple[str, dict[str, Identity]]:
    room_id = uuid(config.get("room_id"))
    raw = config.get("actors")
    if not isinstance(raw, dict) or not 2 <= len(raw) <= len(CAST) or any(actor not in CAST for actor in raw):
        raise BandError("Map two to four cast members to Band identities.")
    env_names = {f"BAND_{actor.upper()}_API_KEY" for actor in raw}
    local = {}
    if Path(".env").is_file():
        for line in Path(".env").read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() in env_names:
                local[name.strip()] = value.strip().strip("\"'")
    actors = {}
    for actor, spec in raw.items():
        if not isinstance(spec, dict):
            raise BandError(f"Band configuration for {actor} must be an object.")
        handle = spec.get("handle")
        if not isinstance(handle, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,60}(?:/[A-Za-z0-9_.-]{1,60})?", handle):
            raise BandError(f"Band needs a valid handle for {actor}.")
        name = f"BAND_{actor.upper()}_API_KEY"
        token = os.environ.get(name) or local.get(name, "")
        if not re.fullmatch(r"band_a_[!-~]{8,300}", token):
            raise BandError(f"Set {name} to that role's Band agent key.")
        actors[actor] = Identity(uuid(spec.get("id")), handle, CAST[actor]["name"], token)
    if len({item.id for item in actors.values()}) != len(actors) or len({item.token for item in actors.values()}) != len(actors):
        raise BandError("Each Band character needs its own identity and key.")
    return room_id, actors


class BandTransport:
    """Read back only this run's messages, then acknowledge after world persistence."""

    def __init__(self, room_id: str, actors: dict[str, Identity], journal: Path,
                 *, max_sends: int = 4, request=band_request):
        self.room_id, self.actors, self.journal = uuid(room_id), actors, journal
        if type(max_sends) is not int or not 1 <= max_sends <= 30:
            raise BandError("Band message limit must be 1–30.")
        self.max_sends, self.request = max_sends, request
        self.messages = read_json(journal) if journal.exists() else {}
        self.endpoint = f"{API}/chats/{self.room_id}/messages"
        self._attempted_acks: set[tuple[str, str]] = set()

    @classmethod
    def configured(cls, config: Path, journal: Path, max_sends: int) -> BandTransport:
        room_id, actors = identities(read_json(config))
        return cls(room_id, actors, journal, max_sends=max_sends)

    @property
    def config_fingerprint(self) -> str:
        config = {"room_id": self.room_id, "actors": {role: actor.mention() for role, actor in self.actors.items()}}
        return sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()

    def _persist(self) -> None:
        write_json(self.journal, self.messages)

    def _matched(self, inbox: object, receipt: str, sender: Identity, recipient: Identity, content: str) -> bool:
        if not isinstance(inbox, list):
            return False
        for message in inbox:
            if not isinstance(message, dict) or message.get("id") != receipt:
                continue
            metadata = message.get("metadata")
            mentions = metadata.get("mentions", []) if isinstance(metadata, dict) else []
            return (message.get("sender_id") == sender.id and message.get("chat_room_id") == self.room_id
                    and message.get("message_type") == "text" and message.get("content") == content
                    and isinstance(mentions, list)
                    and any(isinstance(item, dict) and item.get("id") == recipient.id for item in mentions))
        return False

    def _claim(self, record: dict, sender: Identity, content: str) -> None:
        for role in record["recipients"]:
            if role in record["claimed"]:
                continue
            recipient = self.actors[role]
            receipt = record["receipt"]
            try:
                inbox = self.request(f"{self.endpoint}?limit=20&sort_order=desc", recipient, method="GET")
                if not self._matched(inbox.get("data"), receipt, sender, recipient, content):
                    continue
                claim = self.request(f"{self.endpoint}/{receipt}/processing", recipient, method="POST").get("data")
                if not isinstance(claim, dict) or claim.get("id") != receipt or claim.get("success") is not True:
                    continue
                record["claimed"].append(role)
                self._persist()
            except BandError:
                continue

    def deliver(self, event: dict, recipients: tuple[str, ...]) -> dict:
        sender = self.actors.get(event.get("actor"))
        available = [role for role in dict.fromkeys(recipients) if role in self.actors and role != event.get("actor")]
        if sender is None or not available:
            return {"transport": "local", "status": "unconfigured", "verified_recipients": []}
        line = " ".join(event["text"].replace("@", "＠").split())[:360]
        marker = f"LOOPDAY {event['loop']}/{event['tick']} {event['id']}"
        content = " ".join("@" + self.actors[role].handle for role in available) + f" [{marker}] {line}"
        key = sha256(json.dumps([sender.id, available, content]).encode()).hexdigest()
        record = self.messages.get(key)
        if record is None:
            if len(self.messages) >= self.max_sends:
                return {"transport": "local", "status": "budget", "verified_recipients": []}
            if sum(row["status"] == "fallback" for row in self.messages.values()) >= 2:
                return {"transport": "local", "status": "circuit_open", "verified_recipients": []}
            record = {"event_id": event["id"], "status": "reserved", "receipt": None,
                      "recipients": available, "claimed": [], "processed": []}
            self.messages[key] = record
            self._persist()
            try:
                message = {"content": content, "mentions": [self.actors[role].mention() for role in available]}
                result = self.request(self.endpoint, sender, method="POST", payload={"message": message}).get("data")
                if not isinstance(result, dict) or result.get("success") is not True:
                    raise BandError("Band did not confirm the message post.")
                record["receipt"] = uuid(result.get("id"))
                self._persist()
            except BandError:
                pass
        if record["status"] == "reserved":
            if record["receipt"]:
                self._claim(record, sender, content)
            if not record["claimed"]:
                record["status"] = "fallback"
            elif set(record["claimed"]) != set(recipients):
                record["status"] = "partially_verified"
            else:
                record["status"] = "verified"
            self._persist()
        return {"transport": "band" if record["claimed"] else "local", "status": record["status"],
                "receipt": record["receipt"], "verified_recipients": list(record["claimed"])}

    def acknowledge(self, committed_receipts: set[str]) -> None:
        for record in self.messages.values():
            if record["receipt"] not in committed_receipts:
                continue
            receipt = record["receipt"]
            for role in set(record["claimed"]) - set(record["processed"]):
                key = (receipt, role)
                if key in self._attempted_acks:
                    continue
                self._attempted_acks.add(key)
                try:
                    confirmed = self.request(f"{self.endpoint}/{receipt}/processed", self.actors[role], method="POST")
                    data = confirmed.get("data")
                    if isinstance(data, dict) and data.get("success") is True and data.get("id") == receipt:
                        record["processed"].append(role)
                        self._persist()
                except BandError:
                    continue

    def summary(self) -> dict:
        return {"send_reservations": len(self.messages),
                "verified_receipts": sum(bool(record["claimed"]) for record in self.messages.values()),
                "processed_recipients": sum(len(record["processed"]) for record in self.messages.values()),
                "fallbacks": sum(record["status"] == "fallback" for record in self.messages.values())}


def check_identities(room: str, actors: dict[str, Identity], request=band_request) -> dict[str, bool]:
    confirmed = {}
    for role, actor in actors.items():
        profile = request(f"{API}/me", actor, method="GET").get("data")
        if not isinstance(profile, dict) or profile.get("id") != actor.id or profile.get("handle") != actor.handle:
            raise BandError(f"The Band key, configured ID, and handle disagree for {role}.")
        data = request(f"{API}/chats/{room}", actor, method="GET").get("data")
        if not isinstance(data, dict) or data.get("id") != room:
            raise BandError(f"The Band room is unavailable to {role}.")
        confirmed[role] = True
    return confirmed


def main() -> int:
    parser = argparse.ArgumentParser(description="Read back the Band identities and private room.")
    parser.add_argument("--check", required=True, type=Path, help="Band room and identity configuration JSON.")
    args = parser.parse_args()
    try:
        room, actors = identities(read_json(args.check))
        result = check_identities(room, actors)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Band check: {error}\n")
    print(json.dumps({"verified_participants": result, "messages_sent": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
