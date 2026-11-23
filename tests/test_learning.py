from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
from unittest import TestCase

from loopday.learning import DecisionSample, OutcomeRanker, fit_ranker, preference_pairs, read_samples, stable_split
from loopday.providers import PHIL_MODEL, PROMPT_VERSION
from server.train_dpo import TrainingError, evaluate, validated_pairs


REVISION = "a" * 40
BASE_CONDITION = json.dumps({"adapter": "base", "thinking": False, "alias_names": False})


def row(group: int, answer: str, outcome: float, *, source: str = "live", checkpoint: str = "same",
        suffix: str = "", model_revision: str = REVISION) -> DecisionSample:
    observation = {"actions": ["wait", "help:neighbor"], "location": "main_st", "tick": 5, "present": ["rita"]}
    return DecisionSample(f"seed:{group}", source, checkpoint, observation, answer, json.dumps({"action": answer}),
                          outcome, PHIL_MODEL, BASE_CONDITION, f"{group}:{answer}{suffix}",
                          model_revision, PROMPT_VERSION)


class LearningTests(TestCase):
    def test_holdout_split_has_no_seed_leakage_and_is_order_invariant(self):
        rows = [row(i // 2, "wait", 0, suffix=str(i)) for i in range(20)]
        train, test = stable_split(rows, min_holdout_groups=2)
        reversed_train, reversed_test = stable_split(reversed(rows), min_holdout_groups=2)
        self.assertFalse({item.group for item in train} & {item.group for item in test})
        self.assertEqual({item.group for item in test}, {item.group for item in reversed_test})
        self.assertEqual({item.group for item in train}, {item.group for item in reversed_train})

    def test_ranker_learns_from_executed_supported_actions_and_checks_live_source(self):
        rows = [row(i, action, gain) for i in range(12)
                for action, gain in (("wait", -2.0), ("help:neighbor", 3.0))]
        ranker = fit_ranker(rows)
        self.assertTrue(ranker.usable)
        self.assertGreater(ranker.score(rows[0].observation, "help:neighbor"),
                           ranker.score(rows[0].observation, "wait"))
        self.assertIsNone(ranker.score(rows[0].observation, "invented:action"))
        self.assertGreater(ranker.report["held_out_r2"], 0.7)
        with tempfile.TemporaryDirectory() as target:
            path = Path(target) / "ranker.json"
            ranker.save(path)
            self.assertEqual(OutcomeRanker.load(path), ranker)
        fixture = fit_ranker([replace(item, source="fixture") for item in rows], source="fixture")
        self.assertFalse(fixture.usable)
        self.assertFalse(fit_ranker(rows[:2]).usable)

    def test_preference_pairs_require_same_state_model_condition_and_outcome_evidence(self):
        baseline = row(1, "wait", -1)
        outcome = row(1, "help:neighbor", 3)
        for wrong in (
            replace(outcome, checkpoint="other"),
            replace(outcome, group="seed:2"),
            replace(outcome, outcome=-0.9),
            replace(outcome, source="fixture"),
            replace(outcome, condition="variant"),
            replace(outcome, model_revision="b" * 40),
            replace(outcome, prompt_version="old"),
            replace(outcome, model="other"),
        ):
            with self.subTest(wrong=wrong):
                self.assertEqual(preference_pairs([baseline, wrong]), [])
        pairs = preference_pairs([baseline, outcome])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["margin"], 4)
        self.assertEqual(pairs[0]["chosen_evidence"], [outcome.evidence_id])
        self.assertEqual(pairs[0]["rejected_evidence"], [baseline.evidence_id])
        with tempfile.TemporaryDirectory() as target:
            path = Path(target) / "pairs.jsonl"
            path.write_text(json.dumps(pairs[0]) + "\n")
            verified, digest = validated_pairs(path)
            self.assertEqual(verified[0].revision, REVISION)
            self.assertEqual(len(digest), 64)
            path.write_text(json.dumps({**pairs[0], "chosen_evidence": pairs[0]["rejected_evidence"]}) + "\n")
            with self.assertRaisesRegex(TrainingError, "separate observation"):
                validated_pairs(path)

    def test_run_extraction_ignores_replays_invalid_choices_and_incomplete_runs(self):
        with tempfile.TemporaryDirectory() as target:
            path = Path(target) / "run.json"
            opener = {"id": "start", "type": "day_start", "loop": 1, "order": 0, "tick": 0}
            first = {"id": "1", "type": "decision", "actor": "phil", "action": "wait", "source": "live",
                     "checkpoint_fingerprint": "state", "policy_observation": {"actions": ["wait"]},
                     "completion": '{"action":"wait"}', "return_to_go": 1.0, "reward": 1.0,
                     "loop": 1, "order": 1, "tick": 0}
            events = [opener, first]
            for i, update in enumerate(({"mode": "replay"},
                                        {"completion": '{"action":"unavailable"}'}, {"actor": "rita"}), 2):
                events.append({**first, "id": str(i), "order": i, "reward": 0.0, "return_to_go": 0.0, **update})
            artifact = {"meta": {"complete": True, "seed": 3, "run_id": "verified"}, "events": events}
            path.write_text(json.dumps(artifact))
            verified = read_samples([path, path])
            self.assertEqual(len(verified), 1)
            self.assertEqual(verified[0].evidence_id, "verified:1")
            path.write_text(json.dumps({**artifact, "events": [opener, {**first, "return_to_go": 9.0}]}))
            with self.assertRaisesRegex(TrainingError, "disagrees"):
                read_samples([path])
            path.write_text(json.dumps({**artifact, "meta": {"complete": False}}))
            self.assertEqual(read_samples([path]), [])

    def test_adapter_gate_requires_improvement_and_enough_held_out_examples(self):
        self.assertTrue(evaluate([1.5] * 8, [-1] * 8)["deployable"])
        self.assertFalse(evaluate([1.5] * 4, [-1] * 4)["deployable"])
        self.assertFalse(evaluate([1.5] * 8, [1] * 8)["deployable"])
        with self.assertRaises(TrainingError):
            evaluate([float("nan")], [0])

    def test_controlled_arms_admit_only_targeted_choices_from_same_batch(self):
        wait, help = row(1, "wait", -1), row(1, "help:neighbor", 1)

        def event(sample, ident, batch="b" * 64):
            return {
                "id": ident, "type": "decision", "actor": "phil", "action": sample.action, "source": "live",
                "checkpoint_fingerprint": sample.checkpoint, "policy_observation": sample.observation,
                "completion": sample.completion, "return_to_go": sample.outcome,
                "model_metadata": {
                    "batch_id": batch, "environment": "local_continuation", "selection": "paired_intervention",
                    "selected_action": sample.action, "model": PHIL_MODEL, "model_revision": REVISION,
                    "prompt_version": PROMPT_VERSION, "adapter": "base", "thinking_enabled": False,
                    "completion_sha256": hashlib.sha256(sample.completion.encode()).hexdigest(),
                },
            }

        def manifest(ident, batch="b" * 64):
            return {"mode": "live_candidate_local_continuation", "seed": 1, "intervention": {
                "target_event_id": ident, "batch_id": batch, "environment": "local_continuation",
            }}

        first = DecisionSample.from_event(event(wait, "first"), manifest("first"), "run1")
        second = DecisionSample.from_event(event(help, "second"), manifest("second"), "run2")
        self.assertIsNone(DecisionSample.from_event(event(wait, "previous"), manifest("first"), "run1"))
        self.assertIsNone(DecisionSample.from_event(event(wait, "first"), {"mode": "live"}, "run1"))
        invented = replace(wait, completion='{"action":"wait","support":["never-observed"]}')
        self.assertIsNone(DecisionSample.from_event(event(invented, "first"), manifest("first"), "run1"))
        third = DecisionSample.from_event(event(help, "third", "c" * 64),
                                          manifest("third", "c" * 64), "run3")
        self.assertEqual(preference_pairs([first, third]), [])
        pairs = preference_pairs([first, second])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["environment"], "local_continuation")
        with tempfile.TemporaryDirectory() as target:
            path = Path(target) / "pairs.jsonl"
            path.write_text(json.dumps(pairs[0]) + "\n")
            verified, _ = validated_pairs(path)
        self.assertEqual(verified[0].environment, "local_continuation")
        samples = [row(seed, action, gain) for seed in range(12)
                   for action, gain in (("wait", -2.0), ("help:neighbor", 3.0))]
        self.assertFalse(fit_ranker([replace(sample, environment="local_continuation")
                                    for sample in samples]).usable)
