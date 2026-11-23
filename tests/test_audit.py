import copy
from unittest import TestCase

from loopday.audit import ArtifactError, audit_run, compare_runs
from loopday.local_agents import LocalDirector
from loopday.simulation import FixtureDirector, Simulation


def sample(action="move:main_st"):
    events = [
        {"type": "day_start", "loop": 1, "tick": 0},
        {"type": "anchor", "loop": 1, "tick": 0, "anchor": "radio"},
        {"type": "prediction", "loop": 1, "tick": 35, "actor": "phil", "text": "It may reset."},
        {"type": "pencil", "loop": 1, "tick": 35, "actor": "phil", "state": "broken"},
        {"type": "day_start", "loop": 2, "tick": 0},
        {"type": "anchor", "loop": 2, "tick": 0, "anchor": "radio"},
        {"type": "pencil", "loop": 2, "tick": 0, "actor": "phil", "state": "whole"},
        {
            "type": "test_result", "loop": 2, "tick": 0, "actor": "phil", "state": "whole",
            "prediction": "e2", "action_evidence": "e3", "observation": "e6",
        },
        {
            "type": "decision", "loop": 2, "tick": 1, "actor": "phil", "action": action,
            "recalled": ["e7"], "stated_support": ["e7"], "checkpoint_fingerprint": "checkpoint",
        },
    ]
    for order, event in enumerate(events):
        event.update(id=f"e{order}", order=order)
    return {"meta": {"mode": "fixture", "complete": True, "event_count": len(events)}, "events": events}


class AuditTests(TestCase):
    def test_experiment_requires_chronological_observation(self):
        run = sample()
        result = audit_run(run)["experiments"][0]
        self.assertTrue(result["later_recalled"])
        self.assertTrue(result["later_cited"])
        run["events"][7]["action_evidence"] = "e6"
        with self.assertRaisesRegex(ArtifactError, "experimental sequence"):
            audit_run(run)

    def test_experiment_support_cannot_be_invented_by_model(self):
        run = sample()
        run["events"][8]["stated_support"] = ["e2"]
        with self.assertRaisesRegex(ArtifactError, "absent from its prompt"):
            audit_run(run)

    def test_comparison_reports_the_actual_first_changed_action(self):
        first = sample()
        second = copy.deepcopy(first)
        second["events"][8]["action"] = "avoid_puddle"
        result = compare_runs(first, second)
        self.assertTrue(result["same_overlapping_anchors"])
        self.assertTrue(result["first_changed_action"]["same_checkpoint"])
        self.assertEqual(result["first_changed_action"]["second_action"], "avoid_puddle")

    def test_timeline_rejects_duplicates_and_backward_ticks(self):
        run = sample()
        run["events"][8]["id"] = "e2"
        with self.assertRaisesRegex(ArtifactError, "unique event ID"):
            audit_run(run)
        run = sample()
        run["events"][3]["tick"] = 33
        with self.assertRaisesRegex(ArtifactError, "timeline"):
            audit_run(run)

    def test_private_evidence_cannot_be_cited_by_another_actor(self):
        run = sample()
        run["events"][7]["witnesses"] = ["phil"]
        run["events"][8]["actor"] = "rita"
        with self.assertRaisesRegex(ArtifactError, "outside its observations"):
            audit_run(run)

    def test_pencil_cannot_validate_a_reset_with_same_day_evidence(self):
        run = sample()
        for row in run["events"][4:]:
            row.update(loop=1, tick=35)
        run["events"][4]["type"] = "anchor"
        with self.assertRaisesRegex(ArtifactError, "across a day reset"):
            audit_run(run)

    def test_replay_cannot_link_to_an_unrelated_turn(self):
        simulation = Simulation(FixtureDirector(), keep_memory=False)
        simulation.run(2)
        run = {"meta": {}, "events": simulation.events}
        replay = next(row for row in run["events"] if row.get("replay_source_event"))
        source = next(row for row in run["events"] if row["id"] == replay["replay_source_event"])
        replay["exchange"] = source["exchange"] + 1
        with self.assertRaisesRegex(ArtifactError, "original decision"):
            audit_run(run)

    def test_romantic_ending_requires_rita_to_have_accepted(self):
        simulation = Simulation(FixtureDirector())
        simulation.run(2)
        run = {"meta": {}, "events": simulation.events}
        reply = next(row for row in run["events"] if row["type"] == "reply" and row.get("accepted"))
        reply["accepted"] = False
        with self.assertRaisesRegex(ArtifactError, "accepted reply"):
            audit_run(run)

    def test_valid_ending_can_include_evidence_rita_saw_after_accepting(self):
        simulation = Simulation(LocalDirector(5), seed=7, lesson_tick=12)
        simulation.run(2)
        reply = next(row for row in simulation.events if row["type"] == "reply" and row.get("accepted"))
        ending = next(row for row in simulation.events if row["type"] == "ending_decision")
        self.assertGreater(len(ending["evidence"]), len(reply["evidence"]))
        report = audit_run({"meta": {"complete": True, "ending": "day_two"}, "events": simulation.events})
        self.assertTrue(report["day_two"])
