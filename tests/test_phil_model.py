import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
from unittest import TestCase, skipIf
from unittest.mock import Mock

try:
    import torch
except ImportError:
    torch = None

from server.calibrate_persona import fit_layer, passes
from server.model import Generation, QwenModel, RequestError, split_thinking
from server.persona import PersonaBank, hooks_for
from server.train_dpo import log_probability


REVISION = "a" * 40
MESSAGE = {"messages": [{"role": "user", "content": "What changed?"}]}


class GenerationTests(TestCase):
    def test_generation_defaults_and_strict_limits(self):
        spec = Generation.parse(MESSAGE)
        self.assertEqual(spec.tokens, 180)
        self.assertFalse(spec.trace)
        for field, value in (
            ("n", 5), ("n", True), ("max_thinking_tokens", 513), ("thinking", "no"),
            ("return_trace", 1), ("return_projections", 1), ("seed", -1), ("seed", None),
            ("temperature", float("nan")), ("temperature", 0), ("steer", []),
            ("messages", [{"role": "user", "content": {"text": "invalid"}}]),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(RequestError):
                Generation.parse({**MESSAGE, field: value})

    def test_thinking_is_trimmed_at_token_boundary_and_reports_limit(self):
        self.assertEqual(split_thinking([7, 10, 11, 12, 0], [10, 11], {0}, 5), ([7], "closed"))
        self.assertEqual(split_thinking([7, 9, 8], [10], {0}, 3), ([7, 9, 8], "capped"))
        self.assertEqual(split_thinking([7, 9, 0], [10], {0}, 3), ([7, 9], "stopped"))

    def test_persona_validation_requires_exact_runtime_and_normalized_axis(self):
        payload = {
            "schema_version": 1, "model": "Qwen", "revision": REVISION, "precision": "bf16", "adapter": "base",
            "axes": {"longing": {"layer": 0, "values": [0.0, 1.0], "coefficient": 2.0,
                                "center": 0.0, "scale": 1.0, "validated": True}},
        }
        with tempfile.TemporaryDirectory() as target:
            path = Path(target) / "axis.json"
            path.write_text(json.dumps(payload))
            args = {"model": "Qwen", "revision": REVISION, "precision": "bf16", "adapter": "base",
                    "depth": 1, "width": 2}
            bank = PersonaBank.read(path, **args)
            self.assertEqual(bank.choose(None, default_longing=True), {"longing": 2.0})
            self.assertEqual(bank.choose({}, default_longing=True), {})
            self.assertEqual(bank.choose({"longing": -2.0}), {"longing": -2.0})
            with self.assertRaisesRegex(ValueError, "outside"):
                bank.choose({"longing": 2.001})
            with self.assertRaisesRegex(ValueError, "revision"):
                PersonaBank.read(path, **{**args, "revision": "b" * 40})
            payload["axes"]["longing"]["validated"] = False
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "calibrated"):
                PersonaBank.read(path, **args)

    def test_calibration_requires_consistent_direction_and_preserved_label_mass(self):
        def result(share, mass, cases):
            return {"positive_share": share, "label_mass": mass, "per_case": cases}
        baseline = result(0.5, 0.9, [0.45, 0.5, 0.55])
        boosted = result(0.65, 0.89, [0.6, 0.65, 0.7])
        dampened = result(0.35, 0.91, [0.3, 0.35, 0.4])
        self.assertTrue(passes(baseline, boosted, dampened, min_gain=0.1))
        self.assertFalse(passes(baseline, boosted, {**dampened, "label_mass": 0.4}, min_gain=0.1))
        self.assertFalse(passes(baseline, boosted, {**dampened, "per_case": [0.5, 0.56, 0.3]}, min_gain=0.1))


@skipIf(torch is None, "torch is optional for CPU fixture runs")
class TorchTests(TestCase):
    def test_two_phase_generation_feeds_a_closed_trace_and_emits_it_only_when_requested(self):
        model = QwenModel.__new__(QwenModel)
        model.torch, model.model = torch, SimpleNamespace(device="cpu")
        model.tokenizer = Mock()
        model.tokenizer.decode.side_effect = lambda ids, **_: "Consider" if ids == [5, 6] else '{"action":"wait"}'
        model.lock, model.bank, model.layers = threading.Lock(), None, None
        model.revision, model.precision, model.adapter = REVISION, "bf16", "base"
        model.close_think, model.finish_think, model.eos = [8], [8, 9], {0}
        model.prompt_ids = Mock(return_value=torch.tensor([[1, 2, 3]]))
        model._generate_ids = Mock(side_effect=[[5, 6], [2, 0], [5, 6, 8], [2, 0]])
        request = {**MESSAGE, "thinking": True, "max_thinking_tokens": 2}
        response = model.generate(request)["outputs"][0]
        self.assertEqual(response, {"answer": '{"action":"wait"}', "tokens": 1,
                                    "thinking_tokens": 2, "think_completion": "capped"})
        second_stage = model._generate_ids.call_args_list[1]
        self.assertEqual(second_stage.args[0].tolist(), [[1, 2, 3, 5, 6, 8, 9]])
        self.assertEqual(second_stage.kwargs["cap"], 180)
        trace_response = model.generate({**request, "max_thinking_tokens": 3, "return_trace": True})["outputs"][0]
        self.assertEqual(trace_response["thinking"], "Consider")
        self.assertEqual(trace_response["think_completion"], "closed")

    def test_layer_selection_uses_independent_contrast(self):
        fit = [(True, {0: torch.tensor([0.0, 2.0]), 1: torch.tensor([8.0, 0.0])}),
               (False, {0: torch.tensor([0.0, -2.0]), 1: torch.tensor([-8.0, 0.0])})]
        checks = [(True, {0: torch.tensor([0.0, 1.0]), 1: torch.tensor([-1.0, 0.0])}),
                  (False, {0: torch.tensor([0.0, -1.0]), 1: torch.tensor([1.0, 0.0])})]
        layer, direction, center, scale, separation = fit_layer(torch, fit, checks, [0, 1])
        self.assertEqual(layer, 0)
        self.assertEqual(direction.tolist(), [0.0, 1.0])
        self.assertEqual((center, scale, separation), (0.0, 2.0, 1.0))

    def test_steering_preserves_auxiliary_outputs_and_releases_hooks_on_error(self):
        class Layer(torch.nn.Module):
            def forward(self, tensor):
                return tensor, "cache"

        layers = [Layer()]
        output = []
        tensor = torch.zeros(1, 2, 2)
        with self.assertRaisesRegex(RuntimeError, "abort"):
            with hooks_for(layers, vectors={0: torch.tensor([1.0, 0.0])}, observers={0: output.append}):
                changed, extra = layers[0](tensor)
                self.assertEqual(extra, "cache")
                self.assertTrue(torch.equal(changed, output[0]))
                self.assertEqual(changed[0, 0].tolist(), [1.0, 0.0])
                raise RuntimeError("abort")
        self.assertTrue(torch.equal(layers[0](tensor)[0], tensor))

    def test_dpo_log_probability_only_sums_completion_tokens(self):
        class LM:
            device = "cpu"

            def __call__(self, *, input_ids, attention_mask, logits_to_keep, use_cache):
                assert logits_to_keep == 3 and not use_cache
                logits = torch.tensor([[[0.0, 0.0, 4.0], [0.0, 4.0, 0.0], [0.0, 0.0, 0.0]]])
                return SimpleNamespace(logits=logits)

        score = log_probability(LM(), torch, [1, 0], [2, 1]).item()
        expected = 2 * torch.tensor([0.0, 0.0, 4.0]).log_softmax(dim=-1)[2].item()
        self.assertAlmostEqual(score, expected, places=6)
