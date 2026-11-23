"""Regression tests for embodiment, causal branching, and replay."""

import json
from unittest import TestCase

from loopday.memory import Memory
from loopday.simulation import FixtureDirector, Simulation
from loopday.town import ROADS


def entries(simulation, kind, **fields):
    return [
        event for event in simulation.events
        if event["type"] == kind and all(event.get(key) == value for key, value in fields.items())
    ]


class WorldTests(TestCase):
    def test_identical_npc_perceptions_need_no_fresh_npc_calls(self):
        class CountingDirector(FixtureDirector):
            def __init__(self):
                super().__init__()
                self.calls = []

            def choose(self, actor, observation):
                self.calls.append(actor)
                return super().choose(actor, observation)

        director = CountingDirector()
        world = Simulation(director, keep_memory=False)
        world.run(1)
        first_day = len(director.calls)
        world.run(2)
        self.assertEqual(set(director.calls[first_day:]), {"phil"})
        first, second = (entries(world, "utterance", actor="ned", loop=day) for day in (1, 2))
        self.assertEqual([(event["utterance_id"], event["text"]) for event in first],
                         [(event["utterance_id"], event["text"]) for event in second])

    def test_equivalent_greeting_replays_but_a_warning_reaches_ned(self):
        class Lines(FixtureDirector):
            def __init__(self, second):
                super().__init__()
                self.second = second
                self.day = 0

            def choose(self, actor, observation):
                if actor == "phil" and observation["exchange"] == 0:
                    if observation["tick"] == 0:
                        self.day += 1
                    if observation["tick"] == 3:
                        line = "Good morning, Ned." if self.day == 1 else self.second
                        return json.dumps({"action": "talk:ned", "line": line})
                return super().choose(actor, observation)

        same = Simulation(Lines("Morning, Ned."))
        same.run(2, 4)
        replay = entries(same, "decision", actor="ned", tick=3, loop=2)[0]
        self.assertEqual((replay["mode"], replay["replay_match"]), ("replay", "semantic"))

        changed = Simulation(Lines("Ned, watch out for the ice."))
        changed.run(2, 4)
        cue = entries(changed, "utterance", actor="phil", to="ned", tick=3, loop=2)[0]
        reaction = entries(changed, "divergence", actor="ned", loop=2)[0]
        self.assertEqual((reaction["source_actor"], reaction["source_event"]), ("phil", cue["id"]))

    def test_replay_retains_destinations_people_negation_time_and_quantities(self):
        baseline = "Please meet Larry at the hotel before 2:30 and help two guests."

        class Meeting(FixtureDirector):
            def __init__(self, alternative):
                super().__init__()
                self.alternative = alternative
                self.day = 0

            def choose(self, actor, observation):
                if actor == "phil" and observation["exchange"] == 0:
                    if observation["tick"] == 0:
                        self.day += 1
                    if observation["tick"] == 3:
                        line = baseline if self.day == 1 else self.alternative
                        return json.dumps({"action": "talk:ned", "line": line})
                return super().choose(actor, observation)

        changes = [
            ("hotel", "diner"), ("Larry", "Rita"), ("Larry", "Doris"),
            ("meet", "do not meet"), ("before", "after"), ("2:30", "2:45"), ("2:30", "2.30"), ("two", "one"),
        ]
        for old, new in changes:
            with self.subTest(change=(old, new)):
                world = Simulation(Meeting(baseline.replace(old, new)))
                world.run(2, 4)
                utterance = entries(world, "utterance", actor="phil", to="ned", tick=3, loop=2)[0]
                decision = entries(world, "decision", actor="ned", tick=3, loop=2)[0]
                divergence = entries(world, "divergence", actor="ned", tick=3, loop=2)[0]
                self.assertEqual(decision["mode"], "fixture")
                self.assertEqual(divergence["source_event"], utterance["id"])
        equal = Simulation(Meeting(baseline.removeprefix("Please ")))
        equal.run(2, 4)
        replay = entries(equal, "decision", actor="ned", tick=3, loop=2)[0]
        self.assertEqual((replay["mode"], replay["replay_match"]), ("replay", "semantic"))

    def test_checkpoint_withholds_only_phils_evidence_before_divergence(self):
        normal = Simulation(FixtureDirector())
        normal.run(1)
        normal.advance_tick()
        result = entries(normal, "test_result")[0]
        saved = json.loads(json.dumps(normal.checkpoint()))
        withheld = Simulation.from_checkpoint(saved, FixtureDirector(), withheld_memory=(result["id"],))

        normal.advance_tick()
        withheld.advance_tick()
        with_evidence, without = (
            entries(world, "decision", actor="phil", tick=1, loop=2)[0] for world in (normal, withheld)
        )
        self.assertEqual(with_evidence["checkpoint_fingerprint"], without["checkpoint_fingerprint"])
        self.assertEqual((with_evidence["action"], without["action"]), ("avoid_puddle", "move:main_st"))
        self.assertIn(result["id"], with_evidence["stated_support"])
        self.assertNotIn(result["id"], without["current_evidence"])
        self.assertEqual(entries(normal, "evidence_use")[0]["source_event"], result["id"])
        self.assertFalse(entries(withheld, "evidence_use", loop=2))

        cue = entries(normal, "puddle", loop=2)[0]
        public = Simulation.from_checkpoint(normal.checkpoint(), FixtureDirector(), withheld_memory=(cue["id"],))
        self.assertEqual(normal.observation("ned"), public.observation("ned"))
        self.assertIn(cue["id"], {event["event_id"] for event in normal.observation("phil")["current_evidence"]})
        self.assertNotIn(cue["id"], {event["event_id"] for event in public.observation("phil")["current_evidence"]})

    def test_negative_experiment_stays_negative_and_does_not_unlock_route(self):
        world = Simulation(FixtureDirector(), reset_pencil=False)
        self.assertNotIn("pencil", world.observation("phil")["world"])
        world.run(2)
        result = entries(world, "test_result")[0]
        self.assertEqual((result["hypothesis"], result["predicted"], result["observed"]),
                         ("room_resets", "whole", "broken"))
        self.assertFalse(result["agrees_with_prediction"])
        self.assertIsNone(world.first_realization)
        self.assertFalse(entries(world, "evidence_use"))
        self.assertFalse(entries(world, "puddle", state="dry", loop=2))

    def test_travel_out_of_town_still_resets_the_calendar(self):
        class LeaveTown(FixtureDirector):
            def choose(self, actor, observation):
                actions = {1: "move:main_st", 3: "move:knob", 4: "move:country_rd", 6: "attempt_exit"}
                if actor == "phil":
                    action = actions.get(observation["tick"], "wait")
                    return json.dumps({"action": action})
                return super().choose(actor, observation)

        world = Simulation(LeaveTown())
        world.run(1)
        self.assertEqual(world.positions["phil"], "outskirts")
        self.assertNotIn("move:country_rd", world.allowed("phil"))
        self.assertEqual(entries(world, "exit", state="left_town")[0]["location"], "outskirts")
        self.assertEqual(world.ending, "repeat")
        phil_moves = entries(world, "position", actor="phil")
        self.assertEqual(len({move["tick"] for move in phil_moves}), len(phil_moves))
        self.assertTrue(all(move["location"] in ROADS[move["moving_from"]] for move in phil_moves))
        world.advance_tick()
        self.assertEqual(world.positions["phil"], "inn")
        anchors = entries(world, "anchor", anchor="radio")
        self.assertEqual([(event["date"], event["time"]) for event in anchors], [("February 2", "06:00")] * 2)

    def test_rita_can_decline_and_the_community_can_recognize_phil(self):
        endings = []
        for alternative in (False, True):
            world = Simulation(FixtureDirector(choose_community=alternative))
            world.run(2)
            endings.append(world.ending_reason)
            reply = entries(world, "reply", actor="rita")[0]
            self.assertEqual(reply["accepted"], not alternative)
            self.assertEqual(reply["gate_level"], 3)
            self.assertEqual(reply["invitation_id"], entries(world, "invitation", actor="phil")[0]["id"])
            self.assertEqual(entries(world, "day_two")[0]["date"], "February 3")
            if alternative:
                self.assertEqual({row["actor"] for row in entries(world, "recognition")}, {"larry", "ned"})
            else:
                self.assertEqual(entries(world, "ending_decision")[0]["reply_event_id"], reply["id"])
        self.assertEqual(endings, ["rita_chose_to_stay", "community_recognition"])

    def test_gossip_witnesses_and_provenance_record_each_hop(self):
        world = Simulation(FixtureDirector())
        world.start(1)
        world.positions.update(phil="main_st", larry="main_st", ned="hotel", rita="knob")
        source = world.observe("kindness", "Phil helps a guest.", "phil", subject="guest")
        world.positions["larry"] = "hotel"
        world._gossip()
        first = entries(world, "gossip", actor="larry", to="ned")[0]
        world.positions["ned"] = "knob"
        world._gossip()
        second = entries(world, "gossip", actor="ned", to="rita")[0]
        world.decide("rita")
        fact = entries(world, "decision", actor="rita")[0]["known_fact_sources"][0]
        self.assertEqual(source["witnesses"], ["phil", "larry"])
        self.assertEqual(first["teller_evidence"], source["id"])
        self.assertEqual(second["teller_evidence"], first["id"])
        self.assertEqual((fact["source_event"], fact["heard_via"], fact["fidelity"]),
                         (source["id"], second["id"], 0.64))

    def test_an_interrupted_tick_resumes_from_the_previous_complete_tick(self):
        class Interrupted(FixtureDirector):
            def choose(self, actor, observation):
                if actor == "rita" and observation["tick"] == 3:
                    raise RuntimeError("Interrupted during a character decision.")
                return super().choose(actor, observation)

        saves = []
        disrupted = Simulation(Interrupted())
        with self.assertRaisesRegex(RuntimeError, "Interrupted"):
            disrupted.run(1, 5, on_tick_finished=saves.append)
        self.assertEqual([save["next_tick"] for save in saves], [1, 2, 3])
        with self.assertRaisesRegex(ValueError, "only after"):
            disrupted.checkpoint()
        resumed = Simulation.from_checkpoint(saves[-1], FixtureDirector())
        nights = []
        resumed.run(1, 5, on_day_finished=nights.append)
        clean = Simulation(FixtureDirector())
        clean.run(1, 5)
        self.assertEqual(resumed.checkpoint(), clean.checkpoint())
        self.assertEqual(nights, [clean.checkpoint()])

    def test_band_receipts_are_attached_only_for_validated_recipients(self):
        class Transport:
            def __init__(self):
                self.envelopes = []

            def deliver(self, event, recipients):
                self.envelopes.append((event, recipients))
                return {"transport": "band", "status": "verified", "receipt": "receipt-123",
                        "verified_recipients": [*recipients, "rita"], "private": "ignored"}

        transport = Transport()
        world = Simulation(FixtureDirector(), transport=transport)
        world.run(1, 4)
        message = entries(world, "utterance", actor="phil", to="ned")[0]
        self.assertEqual(message["transport"]["verified_recipients"], ["ned"])
        self.assertNotIn("private", message["transport"])
        self.assertEqual(set(transport.envelopes[0][0]), {"id", "loop", "tick", "type", "actor", "to", "location", "text"})
        self.assertIn(message["id"], {row["event_id"] for row in world.observation("ned")["message_receipts"]})
        self.assertNotIn("message_receipts", world.observation("rita"))

    def test_cited_memory_reconsolidates_without_rewriting_a_witnessed_line(self):
        memory = Memory()
        text = "Good morning, Punxsutawney."
        record = memory.observe(1, {"id": "e001", "text": text, "location": "inn"})
        for attempt in range(100):
            changes = memory.rehearse(2, ["e001"], valence=-0.45, seed=7, decision=f"e{attempt}")
            if changes:
                break
        self.assertTrue(changes)
        self.assertEqual(changes[0][1], text)
        self.assertEqual(record["verbatim"], text)
        self.assertTrue(record["text"].startswith(text))
        self.assertIn("colder", record["text"])
        self.assertEqual(memory.deja_vu(2, text), (1.0, "e001"))
