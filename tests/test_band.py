import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from loopday.band import BandError, BandTransport, Identity
from loopday.run import main


ROOM = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
MESSAGE = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
PHIL = Identity("cccccccc-cccc-4ccc-accc-cccccccccccc", "phil", "Phil", "unused")
RITA = Identity("dddddddd-dddd-4ddd-addd-dddddddddddd", "rita", "Rita", "unused")
NED = Identity("eeeeeeee-eeee-4eee-aeee-eeeeeeeeeeee", "ned", "Ned", "unused")
EVENT = {"id": "e00010", "actor": "phil", "loop": 2, "tick": 1, "text": "The step outside freezes over, @Rita."}


class BandStub:
    def __init__(self, *, corrupt=None, timeout=False):
        self.calls = []
        self.draft = {}
        self.corrupt = corrupt
        self.timeout = timeout

    def __call__(self, url, identity, *, method, payload=None):
        self.calls.append((url, identity.handle, method))
        if payload:
            self.draft = payload["message"]
            self.sender = identity
            if self.timeout:
                raise BandError("The POST outcome is unknown.")
        if method == "GET":
            _, marker, line = self.draft["content"].partition("[LOOPDAY ")
            msg = {"id": MESSAGE, "sender_id": self.sender.id, "message_type": "text",
                   "content": f"@Rita {marker}{line}", "metadata": {"mentions": self.draft["mentions"]}}
            msg.update(self.corrupt or {})
            return {"data": [msg]}
        return {"data": {"id": MESSAGE, "success": True}}


class BandTransportTest(unittest.TestCase):
    def test_receipt_verified_as_recipient_and_acknowledged_after_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "band.json"
            stub = BandStub()
            transport = BandTransport(ROOM, {"phil": PHIL, "rita": RITA}, path, request=stub)
            result = transport.deliver(EVENT, ("rita",))
            self.assertEqual(result, {"transport": "band", "status": "verified", "receipt": MESSAGE,
                                      "verified_recipients": ["rita"]})
            self.assertEqual([(role, method) for _, role, method in stub.calls],
                             [("phil", "POST"), ("rita", "GET"), ("rita", "POST")])
            self.assertEqual(stub.draft["content"].count("@"), 1)
            transport.acknowledge(set())
            self.assertEqual(len(stub.calls), 3)

            recovered = BandTransport(ROOM, {"phil": PHIL, "rita": RITA}, path, request=stub)
            self.assertEqual(recovered.deliver(EVENT, ("rita",)), result)
            recovered.acknowledge({MESSAGE})
            recovered.acknowledge({MESSAGE})
            self.assertTrue(stub.calls[-1][0].endswith("/processed"))
            self.assertEqual(len(stub.calls), 4)
            self.assertEqual(recovered.summary()["processed_recipients"], 1)

    def test_unrelated_quoted_or_forged_messages_do_not_reach_a_character(self):
        for corrupt in ({"sender_id": RITA.id}, {"chat_room_id": RITA.id}, {"metadata": {}}, {"content": "wrong"}):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as folder:
                stub = BandStub(corrupt=corrupt)
                transport = BandTransport(ROOM, {"phil": PHIL, "rita": RITA}, Path(folder) / "band.json",
                                          request=stub)
                result = transport.deliver(EVENT, ("rita",))
                self.assertEqual(result["status"], "fallback")
                self.assertEqual(result["verified_recipients"], [])
                self.assertEqual(len(stub.calls), 2)

    def test_ambiguous_post_is_never_repeated_and_consumes_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "band.json"
            stub = BandStub(timeout=True)
            transport = BandTransport(ROOM, {"phil": PHIL, "rita": RITA}, path, max_sends=1, request=stub)
            result = transport.deliver(EVENT, ("rita",))
            self.assertEqual(result["status"], "fallback")
            recovered = BandTransport(ROOM, {"phil": PHIL, "rita": RITA}, path, max_sends=1, request=stub)
            self.assertEqual(recovered.deliver(EVENT, ("rita",)), result)
            self.assertEqual(recovered.deliver({**EVENT, "id": "e00011"}, ("rita",))["status"], "budget")
            self.assertEqual(len(stub.calls), 1)

    def test_transport_receipt_reaches_a_real_local_decision_and_is_acknowledged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stub = BandStub()
            transport = BandTransport(ROOM, {"ned": NED, "rita": RITA}, root / "band.json", max_sends=1, request=stub)
            arguments = ["loopday.run", "--local", "--loops", "1", "--ticks", "13", "--seed", "7",
                         "--policy-seed", "7", "--band-config", "unused.json", "--out", str(root)]
            with (patch("sys.argv", arguments), patch("loopday.run.BandTransport.configured", return_value=transport),
                  contextlib.redirect_stdout(io.StringIO())):
                self.assertEqual(main(), 0)
            run = json.loads((root / "run.json").read_text())
            self.assertEqual(run["audit"]["band_verified_deliveries"], 1)
            self.assertEqual(run["audit"]["band_observed_deliveries"], 1)
            self.assertEqual(run["meta"]["band"]["processed_recipients"], 1)
            self.assertEqual(stub.calls[-1][1:], ("rita", "POST"))
            self.assertTrue(stub.calls[-1][0].endswith("/processed"))
