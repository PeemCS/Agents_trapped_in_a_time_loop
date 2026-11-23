"""Autonomous local policies use legal actions, persistent evidence, and their own goals."""

import json
from unittest import TestCase

from loopday.audit import audit_run
from loopday.local_agents import LocalDirector
from loopday.simulation import Simulation


def local_world(policy_seed, *, keep_memory=True):
    return Simulation(LocalDirector(policy_seed), keep_memory=keep_memory, seed=7)


def decisions(world, **fields):
    return [row for row in world.events
            if row["type"] == "decision" and all(row.get(key) == value for key, value in fields.items())]


class LocalAgentTests(TestCase):
    def test_policy_seed_changes_the_ending_under_identical_world_rules(self):
        endings = []
        anchor_ids = []
        for seed in (0, 7):
            world = local_world(seed)
            world.run(3)
            endings.append(world.ending_reason)
            anchor_ids.append([(row["loop"], row["tick"], row["anchor"])
                               for row in world.events if row["type"] == "anchor"])
            find = audit_run({"meta": {"mode": world.director.mode, "complete": True,
                                      "ending": world.ending}, "events": world.events})
            self.assertTrue(find["experiments"][0]["later_cited"])
            fresh = decisions(world, mode="local_policy")
            self.assertEqual({row["actor"] for row in fresh}, {"phil", "rita", "ned", "larry"})
            by_id = {row["id"]: row for row in world.events}
            for row in decisions(world):
                self.assertEqual(row["source"], "local_policy")
                if row["mode"] == "local_policy":
                    details = row["policy_metadata"]
                    self.assertEqual(details["selected_action"], row["action"])
                    options = details["presented_options"]
                    valid = {candidate["action"] for candidate in options}
                    self.assertEqual(valid, set(row["available_actions"]))
                    self.assertEqual(options, sorted(options, key=lambda option: (-option["score"], option["action"])))
                    self.assertTrue(all(round(option["utility"] + option["exploration"], 4) == option["score"]
                                        for option in options))
                    self.assertNotIn("model_metadata", row)
                else:
                    original = by_id[row["replay_source_event"]]
                    self.assertEqual((original["actor"], original["action"]), (row["actor"], row["action"]))
                    self.assertEqual(original["mode"], "local_policy")
            self.assertTrue(decisions(world, actor="ned", action="show_policy"))
            self.assertTrue(decisions(world, actor="rita", action="check_in_with_station"))
            footage = [row for row in world.events if row.get("subject") == "town_broll"]
            self.assertTrue(footage)
            self.assertTrue(all("larry" in by_id[row["source_event"]]["witnesses"] for row in footage))
        self.assertEqual(anchor_ids[0], anchor_ids[1])
        self.assertEqual(endings, ["community_recognition", "rita_chose_to_stay"])

    def test_private_memory_unblocks_skill_and_affects_candidate_utilities(self):
        learning = local_world(0)
        learning.run(3)
        cleared = local_world(0, keep_memory=False)
        cleared.run(3)
        self.assertEqual(learning.piano_level, 1)
        self.assertEqual(cleared.piano_level, 0)
        self.assertTrue(decisions(learning, actor="phil", action="practice_piano"))
        self.assertTrue(decisions(learning, actor="phil", action="play_piano"))
        self.assertFalse(decisions(cleared, actor="phil", action="play_piano"))
        self.assertTrue(any(
            factor["reason"].startswith("Past experience") and factor["weight"] != 0
            for row in decisions(learning, actor="phil")
            for option in row["policy_metadata"]["presented_options"] for factor in option["factors"]
        ))

    def test_memory_fork_changes_the_local_action_at_the_same_checkpoint(self):
        world = local_world(0)
        world.run(1)
        world.advance_tick()
        evidence = next(row for row in world.events if row["type"] == "test_result")
        saved = world.checkpoint()
        withheld = Simulation.from_checkpoint(saved, LocalDirector(0), withheld_memory=(evidence["id"],))
        world.advance_tick()
        withheld.advance_tick()

        actual, other = (decisions(branch, actor="phil", loop=2, tick=1)[0]
                         for branch in (world, withheld))
        self.assertEqual(actual["checkpoint_fingerprint"], other["checkpoint_fingerprint"])
        self.assertEqual((actual["action"], other["action"]), ("avoid_puddle", "move:main_st"))
        self.assertIn(evidence["id"], actual["stated_support"])
        self.assertNotIn(evidence["id"], other["stated_support"])

    def test_no_hidden_rng_state_is_needed_to_resume(self):
        staged = local_world(7)
        for _ in range(43):
            staged.advance_tick()
        snapshot = json.loads(json.dumps(staged.checkpoint()))
        renewed = Simulation.from_checkpoint(snapshot, LocalDirector(7))
        renewed.run(3)
        uninterrupted = local_world(7)
        uninterrupted.run(3)
        self.assertEqual(renewed.checkpoint(), uninterrupted.checkpoint())

    def test_appointment_time_requires_a_witnessed_or_remembered_notice(self):
        world = Simulation(LocalDirector(7, exploration=0), lesson_tick=8)
        world.advance_tick()
        first = decisions(world, actor="phil", loop=1, tick=0)[0]["policy_observation"]
        self.assertNotIn("lesson_tick", first)
        self.assertNotIn("known_appointments", first)
        world.advance_tick()
        notice = next(row for row in world.events if row["type"] == "timetable")
        self.assertEqual((notice["location"], notice["witnesses"]), ("main_st", ["phil"]))
        self.assertEqual(notice["appointment"]["opens"], 8)
        self.assertNotIn("known_appointments", world.observation("ned"))
        world.run(1)
        world.advance_tick()
        second = decisions(world, actor="phil", loop=2, tick=0)[0]["policy_observation"]
        appointment = second["known_appointments"][0]
        self.assertEqual((appointment["event_id"], appointment["basis"]), (notice["id"], "remembered_notice"))

    def test_plans_to_physically_attend_earlier_and_later_lesson_windows(self):
        for opening in (8, 22):
            with self.subTest(opening=opening):
                world = Simulation(LocalDirector(7, exploration=0), lesson_tick=opening)
                world.run(3)
                practice = next(row for row in world.events if row["type"] == "skill")
                route = next(row for row in decisions(world, actor="phil", loop=2, action="move:piano_teacher"))
                plan = route["policy_metadata"]["appointment_plan"]
                source = next(row for row in world.events if row["id"] == plan["source_event"])
                self.assertEqual((source["type"], source["appointment"]["opens"]), ("timetable", opening))
                self.assertIn(source["id"], route["stated_support"])
                self.assertEqual((route["tick"] < opening, plan["projected_lesson_if_act_now"], practice["tick"]),
                                 (True, opening, opening))

    def test_hiding_unrelated_episode_preserves_the_appointment_plan(self):
        world = Simulation(LocalDirector(7, exploration=0), lesson_tick=22)
        world.run(1)
        for _ in range(19):
            snapshot = world.checkpoint()
            world.advance_tick()
            route = next(iter(decisions(world, actor="phil", loop=2, action="move:piano_teacher")), None)
            if route:
                break
        self.assertIsNotNone(route)
        past = {row["id"]: row for row in snapshot["events"]}
        unrelated = next(memory["event_id"] for memory in route["policy_observation"]["memories"]
                         if past[memory["event_id"]]["type"] == "camera")
        altered = Simulation.from_checkpoint(snapshot, LocalDirector(7, exploration=0),
                                             withheld_memory=(unrelated,))
        altered.advance_tick()
        control = decisions(altered, actor="phil", loop=2, tick=route["tick"])[0]
        self.assertEqual(control["checkpoint_fingerprint"], route["checkpoint_fingerprint"])
        self.assertNotIn(unrelated, control["recalled"])
        self.assertEqual(control["action"], route["action"])
        self.assertEqual(control["policy_metadata"]["appointment_plan"], route["policy_metadata"]["appointment_plan"])

    def test_immediate_help_can_win_over_a_correct_last_chance_lesson_plan(self):
        world = Simulation(LocalDirector(7, exploration=0), lesson_tick=11)
        world.run(3)
        help_choice = decisions(world, actor="phil", loop=2, tick=11, action="help:kid_tree")[0]
        plan = help_choice["policy_metadata"]["appointment_plan"]
        self.assertEqual((plan["opens"], plan["projected_lesson_if_act_now"]), (11, 12))
        self.assertIsNone(plan["projected_lesson_if_wait"])
        self.assertEqual(plan["tradeoff"]["projected_loss"], "missed_window")
        self.assertFalse(any(row["type"] == "skill" for row in world.events))
