import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from loopday.memory import Memory
from loopday.providers import LiveDirector, ModelError
from loopday.run import passed_canary
from loopday.simulation import FixtureDirector, Simulation


class SimulationTests(TestCase):
    def simulate(self, *, memory=True):
        result = Simulation(FixtureDirector(), keep_memory=memory)
        result.run(2)
        return result

    def test_two_days_link_prediction_to_a_reset_and_a_different_action(self):
        result = self.simulate()
        prediction = next(event for event in result.events if event["type"] == "prediction")
        broken = next(event for event in result.events if event.get("state") == "broken")
        morning = next(event for event in result.events if event["loop"] == 2 and event.get("state") == "whole")
        self.assertLess(prediction["order"], broken["order"])
        self.assertLess(broken["order"], morning["order"])
        verified = next(event for event in result.events if event["type"] == "test_result")
        self.assertEqual((verified["prediction"], verified["action_evidence"], verified["observation"]),
                         (prediction["id"], broken["id"], morning["id"]))
        actions = [event for event in result.events if event["type"] == "decision" and event["actor"] == "phil"]
        self.assertIn("move:main_st", [event["action"] for event in actions if event["loop"] == 1])
        self.assertIn("avoid_puddle", [event["action"] for event in actions if event["loop"] == 2])
        self.assertEqual(result.ending, "day_two")

    def test_cleared_memory_fixture_has_same_anchors_and_different_ending(self):
        retained = self.simulate()
        cleared = self.simulate(memory=False)
        anchors = lambda run: [(e["loop"], e["tick"], e["anchor"]) for e in run.events if e["type"] == "anchor"]
        self.assertEqual(anchors(retained), anchors(cleared))
        self.assertEqual(cleared.ending, "repeat")
        self.assertTrue(cleared.replayed_decisions > 0)
        self.assertEqual(retained.events, self.simulate().events)

    def test_impossible_moves_are_rejected_before_the_world_changes(self):
        class InvalidChoices(FixtureDirector):
            def choose(self, actor, obs):
                return json.dumps({"action": "move:outside-county"})

        result = Simulation(InvalidChoices())
        result.run(1, 2)
        self.assertEqual(result.positions["phil"], "inn")
        self.assertTrue(any(event["type"] == "rejected" for event in result.events))
        self.assertFalse(any(event["type"] == "position" for event in result.events))

    def test_invitation_requires_witnessed_evidence_and_rita_relationship_threshold(self):
        result = Simulation(FixtureDirector())
        result.start(1)
        result.positions["phil"] = result.positions["rita"] = "hotel"
        result.tick = 30
        result.invitation = True
        self.assertNotIn("accept_invitation", result.allowed("rita"))
        result.observe("performance", "Phil plays for the ballroom.", "phil", subject="performance")
        result.observe("kindness", "Phil helps one guest.", "phil", subject="first_help")
        self.assertNotIn("accept_invitation", result.allowed("rita"))
        result.observe("kindness", "Phil helps another guest.", "phil", subject="second_help")
        self.assertIn("accept_invitation", result.allowed("rita"))

    def test_memories_fuzz_and_then_fade(self):
        memory = Memory()
        memory.observe(1, {"id": "e0", "text": "A noisy room.", "location": "inn"}, 0.6)
        self.assertEqual(memory.fade(4)[0][0], "FUZZ")
        self.assertEqual(memory.fade(7)[0][0], "DELETE")

    def test_shifted_lesson_can_be_seen_and_used_in_the_world(self):
        result = Simulation(FixtureDirector(), lesson_tick=14)
        result.run(2)
        practice = next(event for event in result.events if event["type"] == "skill")
        self.assertEqual(practice["tick"], 14)
        self.assertEqual(practice["loop"], 2)

    def test_checkpoint_resume_matches_an_uninterrupted_run(self):
        first = Simulation(FixtureDirector())
        first.run(1)
        saved = json.loads(json.dumps(first.checkpoint()))
        resumed = Simulation(FixtureDirector())
        resumed.restore(saved)
        resumed.run(2)
        self.assertEqual(resumed.events, self.simulate().events)
        self.assertEqual(resumed.ending, "day_two")

    def test_full_live_run_gate_needs_each_real_agent_and_no_rejected_actions(self):
        data = {
            "meta": {"complete": True, "mode": "live", "provider_calls": 4},
            "events": [{"actor": actor, "mode": "live", "type": "decision"}
                       for actor in ("phil", "rita", "ned", "larry")],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            path.write_text(json.dumps(data))
            self.assertTrue(passed_canary(path))
            data["events"].append({"type": "rejected"})
            path.write_text(json.dumps(data))
            self.assertFalse(passed_canary(path))
            data["events"].pop()
            data["meta"]["mode"] = "fixture"
            path.write_text(json.dumps(data))
            self.assertFalse(passed_canary(path))

    @patch("loopday.providers.request_json", return_value={})
    def test_live_call_budget_stops_before_requesting_again(self, request):
        director = LiveDirector({"MODEL_API_KEY": "x", "PHIL_URL": "https://test.invalid", "PHIL_TOKEN": "y"}, 1)
        director.call("https://test.invalid", "token", {})
        with self.assertRaisesRegex(ModelError, "1-call limit"):
            director.call("https://test.invalid", "token", {})
        request.assert_called_once()

    @patch("loopday.providers.request_json", return_value={"choices": [{"message": {"content": '{"action":"wait"}'}}]})
    def test_saved_muse_response_is_reused_after_restart(self, request):
        settings = {"MODEL_API_KEY": "x", "PHIL_URL": "https://test.invalid", "PHIL_TOKEN": "y"}
        messages = [{"role": "user", "content": "Choose wait."}]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "muse.sqlite3"
            first = LiveDirector(settings, 1, path)
            second = LiveDirector(settings, 1, path)
            self.assertEqual(first.muse(messages), second.muse(messages))
            self.assertEqual(second.calls, 0)
            self.assertEqual(second.cache_hits, 1)
        request.assert_called_once()
