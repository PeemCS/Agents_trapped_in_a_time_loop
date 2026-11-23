from pathlib import Path
import tempfile
from unittest import TestCase

from loopday.experiments import collect_rollouts
from loopday.learning import TrainingError, stable_json
from loopday.rollout_eval import evaluate_external, fit_and_evaluate, read_rollouts, read_verified_index


class RolloutEvaluationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = list(collect_rollouts(range(3, 7), 2, windows=(1, 11)))

    def write_rows(self, path, rows):
        path.write_text("".join(stable_json(row) + "\n" for row in rows))

    def test_fit_evaluates_only_held_out_seeds_with_no_live_policy_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollouts.jsonl"
            self.write_rows(path, self.rows)
            checkpoints, digest = read_rollouts(path)
        self.assertEqual(len(digest), 64)
        ranker, report, choices = fit_and_evaluate(checkpoints)
        self.assertFalse(ranker.usable)
        self.assertFalse(report["live_ranker_usable"])
        self.assertFalse(set(report["held_out_seeds"]) & set(report["training_seeds"]))
        self.assertEqual({row["seed"] for row in choices["mixed"]}, set(report["held_out_seeds"]))
        self.assertGreaterEqual(report["conditions"]["mixed"]["return"]["oracle"],
                                report["conditions"]["mixed"]["return"]["ranker"])
        with self.assertRaisesRegex(TrainingError, "must be new"):
            evaluate_external(ranker, checkpoints)

    def test_qualified_index_rejects_partial_cases_and_unknown_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path, index = (Path(directory) / name for name in ("rollouts.jsonl", "index.csv"))
            self.write_rows(path, self.rows)
            case = self.rows[0]["checkpoint"]
            approved = [row["evidence_id"] for row in self.rows if row["checkpoint"] == case]
            index.write_text("evidence_id\n" + "\n".join(approved) + "\n")
            identifiers, digest = read_verified_index(index)
            self.assertEqual(len(digest), 64)
            chosen, _ = read_rollouts(path, identifiers)
            self.assertEqual([record.identifier for record in chosen], [case])
            with self.assertRaisesRegex(TrainingError, "only part"):
                read_rollouts(path, set(approved[1:]))
            with self.assertRaisesRegex(TrainingError, "missing"):
                read_rollouts(path, set(approved) | {"0" * 64})
            index.write_text("evidence_id\n" + "\n".join(approved + approved[:1]) + "\n")
            with self.assertRaisesRegex(TrainingError, "duplicate"):
                read_verified_index(index)

    def test_modified_observation_and_lost_trials_are_detected(self):
        rows = self.rows
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollouts.jsonl"
            damaged = {**rows[0], "observation": {**rows[0]["observation"], "name": "someone else"}}
            self.write_rows(path, [damaged, *rows[1:]])
            with self.assertRaisesRegex(TrainingError, "changed before"):
                read_rollouts(path)
            self.write_rows(path, rows[1:])
            with self.assertRaisesRegex(TrainingError, "every legal action"):
                read_rollouts(path)
