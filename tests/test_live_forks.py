import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from loopday.experiments import day_checkpoints
from loopday.learning import preference_pairs, read_samples
from loopday.live_forks import MODE, evaluate_batch, inspect_checkpoint, save_branches
from loopday.providers import PHIL_MODEL, LiveDirector, PhilOptions


class LiveForkTest(unittest.TestCase):
    def test_one_model_batch_reaches_two_world_outcomes_without_resampling(self):
        checkpoint, _ = next(day_checkpoints(7, (24,)))
        reference, ticks = inspect_checkpoint(checkpoint)
        options = reference["available_actions"]
        self.assertIn("help_guests", options)
        requests = []

        def backend(payload):
            requests.append(payload)
            return {"model": PHIL_MODEL, "model_revision": "a" * 40, "precision": "bf16", "adapter": "base",
                    "outputs": [{"answer": json.dumps({"action": action, "reason": "The ballroom is busy."}), "tokens": 8}
                                for action in ("help_guests", "wait", "move:fake")]}

        director = LiveDirector({}, 1, phil_only=True, phil_backend=backend, alias_names=True,
                                phil_options=PhilOptions(candidates=3, seed=7))
        batch = director.sample_phil(reference["policy_observation"])
        arms = evaluate_batch(checkpoint, reference, ticks, batch)
        self.assertEqual(len(requests), 1)
        self.assertEqual(len(arms), 2)
        with TemporaryDirectory() as folder:
            out = Path(folder)
            save_branches(out, {"mode": MODE}, batch, arms, director)
            targets = read_samples(sorted(out.glob("fork-*")))
            self.assertEqual({target.checkpoint for target in targets}, {reference["checkpoint_fingerprint"]})
            self.assertEqual({target.environment for target in targets}, {"local_continuation"})
            self.assertEqual({target.action for target in targets}, {"help_guests", "wait"})
            self.assertEqual(len(targets), 2)
            pairs = preference_pairs(targets, source="live")
            self.assertEqual(len(pairs), 1)
            self.assertEqual(pairs[0]["chosen_action"], "help_guests")
