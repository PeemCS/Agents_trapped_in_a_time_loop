"""Focused regression checks for chronology, provenance, source quotes, missing payoffs and simultaneous POV."""

import json
import tempfile
import unittest
from pathlib import Path
from edit import coach_clusters, make_edl, verify


class EditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.trace = Path(self.tmp.name) / "world.json"

        def row(day, clock, start, end, act, words):
            return {
                "id": f"D{day}-{clock}",
                "day": day,
                "clock": clock,
                "actor": "Phil",
                "origin": start,
                "place": end,
                "decision": {"action": act, "words": words},
                "effect": act,
            }

        self.events = [
            row(1, "6:00 am", "inn", "depot", "go_to_depot", "The timetable."),
            row(1, "1:00 pm", "depot", "Pittsburgh", "take_coach_to_Pittsburgh", "Ticket out."),
            row(1, "7:00 pm", "Pittsburgh", "Pittsburgh", "look_around", "I am home."),
            row(2, "6:00 am", "inn", "studio", "go_to_studio", "Morning."),
        ]
        self.events[1]["cast"] = [
            dict(row(1, "1:00 pm", "square", "square", "listen_to_band", "Distant words."), actor="Rita")
        ]
        self.save()

    def save(self):
        self.trace.write_text(json.dumps({"events": self.events}))

    def test_three_anchors(self):
        edl = make_edl(self.trace)
        self.assertTrue(verify(self.trace, edl)["valid"])
        self.assertEqual(edl["cluster"], {"arrival": 1, "hold": 2, "wake": 3})
        self.assertFalse(any(line["actor"] == "Rita" for s in edl["shots"] for line in s["speech"]))

    def test_ending_before_wake_accepts_chronicle_only(self):
        self.events.pop()
        self.save()
        self.assertEqual(list(coach_clusters(self.events)), [])
        with self.assertRaises(ValueError):
            make_edl(self.trace)
        self.assertTrue(verify(self.trace, make_edl(self.trace, "chronicle"))["valid"])

    def test_remote_voice_cannot_be_mixed_into_reporter_location(self):
        edl = make_edl(self.trace)
        shot = next(s for s in edl["shots"] if s["event_index"] == 1)
        shot["speech"] = [{"actor": "Rita", "text": "Distant words."}]
        with self.assertRaisesRegex(ValueError, "line lacks"):
            verify(self.trace, edl)

    def test_local_cutaway_can_play_its_own_voice(self):
        edl = make_edl(self.trace)
        shot = next(s for s in edl["shots"] if s["event_index"] == 1)
        shot["focus"] = "Rita"
        shot["speech"] = [{"actor": "Rita", "text": "Distant words."}]
        with self.assertRaisesRegex(ValueError, "missing"):
            verify(self.trace, edl)
        edl["selection"] = "chronicle"
        edl["cluster"] = None
        self.assertTrue(verify(self.trace, edl)["valid"])

    def test_changed_words_rejected(self):
        edl = make_edl(self.trace)
        edl["shots"][0]["speech"][0]["text"] = "I am stuck forever."
        with self.assertRaisesRegex(ValueError, "line lacks"):
            verify(self.trace, edl)

    def test_reordered_shot_rejected(self):
        edl = make_edl(self.trace)
        edl["shots"].reverse()
        with self.assertRaisesRegex(ValueError, "out-of-order"):
            verify(self.trace, edl)

    def test_wrong_source_rejected(self):
        edl = make_edl(self.trace)
        self.events[0]["effect"] = "different"
        self.save()
        with self.assertRaisesRegex(ValueError, "source"):
            verify(self.trace, edl)

    def test_missed_physical_return(self):
        edl = make_edl(self.trace)
        edl["shots"] = [s for s in edl["shots"] if s["view"] != "morning"]
        with self.assertRaisesRegex(ValueError, "missing"):
            verify(self.trace, edl)

    def test_no_phantom_city_hold(self):
        self.events[2]["origin"] = "depot"
        self.save()
        self.assertEqual(list(coach_clusters(self.events)), [])

    def test_unfinished_rejected(self):
        self.trace.write_text(json.dumps({"status": "partial", "events": self.events}))
        with self.assertRaisesRegex(ValueError, "unfinished"):
            make_edl(self.trace)


if __name__ == "__main__":
    unittest.main()
