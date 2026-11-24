import json
from pathlib import Path
import subprocess
import tempfile
from unittest import TestCase
from unittest.mock import patch

from loopday.providers import (
    LiveDirector, META_URL, MUSE_MODEL, ModelError, PHIL_MODEL, PhilOptions, decision_messages,
    request_json,
)


SETTINGS = {"MODEL_API_KEY": "meta-fake-test", "PHIL_URL": "https://qwen.example.com",
            "PHIL_TOKEN": "qwen-fake-test"}
OBSERVATION = {"actions": ["wait", "move:inn"], "name": "Phil Connors", "location": "knob",
               "observations": ["Snow fell on Punxsutawney."]}


class ProviderTests(TestCase):
    def test_transport_passes_auth_and_payload_through_stdin_and_disables_globbing(self):
        token = "private-example"
        with patch("loopday.providers.subprocess.run", return_value=subprocess.CompletedProcess(
            [], 0, stdout='{"answer":"ready"}\n200', stderr="",
        )) as call:
            self.assertEqual(request_json(META_URL, token, {"content": "source line\nnext line"}),
                             {"answer": "ready"})
        argv = call.call_args.args[0]
        self.assertEqual(argv[:2], ["curl", "--disable"])
        self.assertIn("--globoff", argv)
        self.assertNotIn(token, repr(argv))
        self.assertNotIn("source line", repr(argv))
        self.assertIn(f"Bearer {token}", call.call_args.kwargs["input"])

    def test_transport_denies_insecure_endpoint_injected_key_and_private_error_text(self):
        with patch("loopday.providers.subprocess.run") as curl:
            for url, token in (
                ("http://example.com", "private"),
                ("https://@example.com", "private"),
                ("https://example.com:444", "private"),
                ("https://example.com/path?q=secret", "private"),
                ("https://example.com", "private\r\nX-Fake: leak"),
            ):
                with self.subTest(url=url), self.assertRaises(ModelError):
                    request_json(url, token, {})
            curl.assert_not_called()
            curl.return_value = subprocess.CompletedProcess(
                [], 0, stdout='{"error":"private-value"}\n429', stderr="credential-like",
            )
            with self.assertRaisesRegex(ModelError, r"api.meta.ai returned HTTP 429") as raised:
                request_json(META_URL, "private-value", {})
            self.assertNotIn("private-value", str(raised.exception))

    def test_reservation_persists_before_http_and_reaches_exact_limit(self):
        order = []
        director = LiveDirector(SETTINGS, max_calls=2, on_attempt=lambda count: order.append(("reserve", count)))
        director.calls = 1

        def completed(url, token, payload):
            order.append(("http", director.calls))
            raise ModelError("Timed out ambiguously.")

        with patch("loopday.providers.request_json", side_effect=completed):
            with self.assertRaisesRegex(ModelError, "Timed out"):
                director.choose("rita", OBSERVATION)
            with self.assertRaisesRegex(ModelError, "2-call limit"):
                director.choose("rita", OBSERVATION)
        self.assertEqual(order, [("reserve", 2), ("http", 2)])

    def test_exact_muse_reply_is_cached_but_illegal_candidate_is_resampled(self):
        def result(action, model=MUSE_MODEL):
            return {"model": model, "usage": {"prompt_tokens": 8, "completion_tokens": 4},
                    "choices": [{"message": {"content": json.dumps({"action": action})}}]}
        with tempfile.TemporaryDirectory() as target:
            cache = Path(target) / "muse.sqlite3"
            first = LiveDirector(SETTINGS, cache_path=cache)
            with patch("loopday.providers.request_json", side_effect=[
                result("wait", "unexpected"), result("teleport"), result("move:inn"),
            ]) as request:
                with self.assertRaisesRegex(ModelError, "different model"):
                    first.choose("rita", OBSERVATION)
                self.assertIn("teleport", first.choose("rita", OBSERVATION))
                self.assertIn("move:inn", first.choose("rita", OBSERVATION))
                second = LiveDirector(SETTINGS, cache_path=cache)
                self.assertIn("move:inn", second.choose("rita", OBSERVATION))
                self.assertEqual(second.calls, 0)
                self.assertEqual(request.call_count, 3)
            self.assertEqual(second.decision_metadata()["model"], MUSE_MODEL)
            self.assertTrue(second.decision_metadata()["cache_hit"])
            self.assertEqual(second.decision_metadata()["tokens"]["prompt_tokens"], 8)

    def test_in_process_qwen_uses_same_limits_without_a_tunnel(self):
        order = []

        def qwen(payload):
            order.append("qwen")
            self.assertEqual(json.loads(payload["messages"][1]["content"]), OBSERVATION)
            return {"model": PHIL_MODEL, "outputs": [{"answer": '{"action":"wait"}', "tokens": 6}]}

        backend = LiveDirector({"MODEL_API_KEY": "fake"}, max_calls=1, phil_backend=qwen,
                               on_attempt=lambda count: order.append(count))
        with patch("loopday.providers.request_json") as network:
            self.assertIn("wait", backend.choose("phil", OBSERVATION))
            with self.assertRaisesRegex(ModelError, "1-call limit"):
                backend.choose("phil", OBSERVATION)
            network.assert_not_called()
        self.assertEqual(order, [1, "qwen"])
        self.assertEqual(backend.usage["phil_calls"], 1)
        self.assertEqual(backend.decision_metadata(), {})
        again = LiveDirector({"MODEL_API_KEY": "fake"}, phil_backend=qwen)
        again.choose("phil", OBSERVATION)
        self.assertEqual(again.decision_metadata()["execution"], "in_process")

    def test_muse_retries_token_exhaustion_and_counts_both_attempts(self):
        director = LiveDirector(SETTINGS, max_calls=2)
        first = {"model": MUSE_MODEL, "usage": {"completion_tokens": 240},
                 "choices": [{"finish_reason": "length", "message": {"content": ""}}]}
        second = {"model": MUSE_MODEL, "usage": {"completion_tokens": 260},
                  "choices": [{"finish_reason": "stop", "message": {"content": '{"action":"wait"}'}}]}
        with patch("loopday.providers.request_json", side_effect=[first, second]) as request:
            self.assertEqual(director.choose("rita", OBSERVATION), '{"action":"wait"}')
        self.assertEqual([call.args[2]["max_completion_tokens"] for call in request.call_args_list], [240, 720])
        self.assertEqual(director.calls, 2)
        self.assertEqual(director.decision_metadata()["tokens"], {"completion_tokens": 500})

    def test_empty_muse_reply_is_left_for_simulator_action_repair(self):
        director = LiveDirector(SETTINGS, max_calls=2)
        response = {"model": MUSE_MODEL, "choices": [{"message": {"content": ""}}]}
        with patch("loopday.providers.request_json", return_value=response):
            self.assertEqual(director.choose("ned", OBSERVATION), "")
        self.assertEqual(director.calls, 2)

    def test_muse_timeout_is_marked_for_action_repair(self):
        director = LiveDirector(SETTINGS, max_calls=1)
        with patch("loopday.providers.request_json", side_effect=ModelError("Provider connection failed (curl 28).")):
            self.assertEqual(director.choose("ned", OBSERVATION), "")
        self.assertEqual(director.decision_metadata()["failure_kind"], "provider_timeout")

    def test_candidate_batch_reserves_once_and_keeps_raw_legal_choices(self):
        answers = ['{ "action":"move:inn", "reason":"Go." }', '{"action":"move:inn"}',
                   '{"action":"nothing"}', '{"action":"wait"}']
        order = []

        def qwen(payload):
            order.append("qwen")
            self.assertEqual(payload["n"], 4)
            return {"model": PHIL_MODEL, "outputs": [{"answer": text, "tokens": 4} for text in answers]}

        director = LiveDirector({}, max_calls=1, phil_backend=qwen, phil_only=True,
                                phil_options=PhilOptions(candidates=4, seed=91), on_attempt=order.append)
        with patch("loopday.providers.request_json") as network:
            with self.assertRaisesRegex(ModelError, "only Phil"):
                director.choose("rita", OBSERVATION)
            batch = director.sample_phil(OBSERVATION)
            self.assertEqual(order, [1, "qwen"])
            network.assert_not_called()
        first, second = batch.legal_candidates
        self.assertEqual([first.index, second.index], [0, 3])
        self.assertEqual(first.completion, answers[0])
        metadata = batch.metadata_for(second, selection="paired_intervention")
        self.assertEqual(metadata["batch_id"], batch.batch_id)
        self.assertEqual(metadata["selected_action"], "wait")
        self.assertEqual(metadata["selection"], "paired_intervention")
        self.assertEqual(metadata["provider_call_index"], 1)
        self.assertNotIn(first.completion, str(metadata))
        self.assertEqual(len(metadata["completion_sha256"]), 64)

    def test_runtime_mismatch_stops_before_accepting_candidates(self):
        qwen = lambda request: {"model": PHIL_MODEL, "precision": "fp16", "adapter": "base",
                                "outputs": [{"answer": '{"action":"wait"}'}]}
        director = LiveDirector({}, phil_backend=qwen, phil_only=True,
                                expected_phil_runtime={"precision": "bf16", "persona_bank": None})
        with self.assertRaisesRegex(ModelError, "precision differs"):
            director.choose("phil", OBSERVATION)
        self.assertEqual(director.calls, 1)
        self.assertEqual(director.decision_metadata(), {})

    def test_valid_candidate_schema_drives_selection_and_trace_requires_opt_in(self):
        result = {
            "model": PHIL_MODEL, "model_revision": "a" * 40, "adapter": "base", "precision": "nf4-bf16",
            "outputs": [
                {"answer": '{"action":"wait","reason":4}', "tokens": 12},
                {"answer": '{"action":"move:inn","reason":"Go."}', "tokens": 10, "thinking_tokens": 8,
                 "think_completion": "closed", "thinking": "Internal-looking model emission",
                 "raw_projections": {"warmth": 3.4}, "projection_z": {"warmth": 0.2}},
            ],
        }
        with patch("loopday.providers.request_json", return_value=result) as request:
            first = LiveDirector(SETTINGS, phil_options=PhilOptions(candidates=2))
            self.assertIn("move:inn", first.choose("phil", OBSERVATION))
            self.assertFalse(request.call_args.args[2]["return_trace"])
            self.assertNotIn("model_trace", first.decision_metadata())
            self.assertEqual(first.usage["phil_generated_tokens"], 30)
            self.assertEqual(first.decision_metadata()["raw_projections"], {"warmth": 3.4})
            second = LiveDirector(SETTINGS, alias_names=True,
                                  phil_options=PhilOptions(candidates=2, thinking=True, capture_trace=True))
            second.choose("phil", OBSERVATION)
            alias_input = request.call_args.args[2]["messages"]
            self.assertIn("Phil Carver", alias_input[1]["content"])
            self.assertIn("Pinewick", alias_input[1]["content"])
            self.assertIn("move:inn", alias_input[1]["content"])
            self.assertEqual(alias_input, decision_messages("phil", OBSERVATION, alias_names=True))
            metadata = second.decision_metadata()
            self.assertTrue(metadata["alias_names"])
            self.assertEqual(metadata["trace_kind"], "model_emitted_text")
            self.assertEqual(metadata["think_completion"], "closed")
