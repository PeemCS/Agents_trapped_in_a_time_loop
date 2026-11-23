import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from loopday.experiments import observed_history
from loopday.providers import META_URL, MUSE_MODEL, PHIL_MODEL, LiveDirector, ModelError
from loopday.run import main, passed_canary
from loopday.run_storage import CallJournal, RunStorageError, exclusive_run, read_json
from loopday.simulation import FixtureDirector


SETTINGS = {"MODEL_API_KEY": "unused", "PHIL_URL": "https://example.invalid", "PHIL_TOKEN": "unused"}


def fake_response(url, token, payload):
    observation = json.loads(payload["messages"][1]["content"])
    raw = FixtureDirector().choose(observation["actor"], observation)
    if url == META_URL:
        return {"model": MUSE_MODEL, "choices": [{"message": {"content": raw}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 15}}
    return {"model": PHIL_MODEL, "model_revision": "a" * 40, "outputs": [{"answer": raw, "tokens": 12}]}


class RunStorageTest(unittest.TestCase):
    def invoke(self, root: Path, *args: str) -> int:
        argv = ["loopday.run", "--live", "--loops", "1", "--ticks", "5", "--max-calls", "24",
                "--no-persistent-cache", "--out", str(root), *args]
        with patch("sys.argv", argv), patch("loopday.run.load_settings", return_value=SETTINGS), contextlib.redirect_stdout(io.StringIO()):
            return main()

    def test_a_failed_provider_probe_is_counted_and_the_last_committed_tick_is_reused(self):
        attempts = 0

        def flaky(url, token, payload):
            nonlocal attempts
            attempts += 1
            if attempts == 3:
                raise ModelError("Expected transient failure in a stub.")
            return fake_response(url, token, payload)

        with TemporaryDirectory() as folder, patch("loopday.providers.request_json", side_effect=flaky):
            root = Path(folder)
            self.assertEqual(self.invoke(root), 1)
            committed = read_json(root / "checkpoint.json")
            self.assertEqual(committed["provider"]["calls"], 2)
            self.assertEqual(read_json(root / ".calls.json")["calls"], 3)
            partial = read_json(root / "run.json")
            self.assertFalse(partial["meta"]["complete"])
            self.assertEqual(partial["meta"]["provider_calls"], 3)
            self.assertFalse(passed_canary(root / "run.json"))

            self.assertEqual(self.invoke(root, "--resume"), 0)
            finished = read_json(root / "run.json")
            self.assertEqual(finished["meta"]["provider_calls"], attempts)
            self.assertTrue(passed_canary(root / "run.json"))
            self.assertEqual(observed_history(finished["events"][:len(committed["world"]["events"])]),
                             observed_history(committed["world"]["events"]))

    def test_a_second_writer_cannot_acquire_the_same_directory(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with exclusive_run(root), self.assertRaises(RunStorageError):
                with exclusive_run(root):
                    self.fail("The lock allowed concurrent writers.")
            with exclusive_run(root):
                self.assertTrue((root / ".run.lock").is_file())

    def test_in_process_cli_loads_once_and_records_the_model_revision(self):
        with (TemporaryDirectory() as folder,
              patch("loopday.providers.request_json", side_effect=fake_response) as network,
              patch("server.model.QwenModel") as backend):
            backend.return_value.generate.side_effect = lambda payload: fake_response(None, "", payload)
            revision = "a" * 40
            root = Path(folder)
            self.assertEqual(self.invoke(root, "--phil-in-process", "--phil-revision", revision, "--phil-4bit",
                                         "--phil-seed", "19"), 0)
            run = read_json(root / "run.json")
            self.assertTrue(passed_canary(root / "run.json"))
            self.assertEqual(run["meta"]["config"]["phil_backend"]["revision"], revision)
            self.assertTrue(run["meta"]["config"]["phil_backend"]["quantize_4bit"])
            backend.assert_called_once()
            self.assertTrue(all(call.args[0] == META_URL for call in network.call_args_list))
            phil = next(event for event in run["events"] if event["type"] == "decision" and event["actor"] == "phil")
            self.assertEqual(phil["model_metadata"]["execution"], "in_process")
            self.assertEqual(phil["model_metadata"]["generation_seed"], 19)
            self.assertEqual(run["meta"]["seed"], 7)

    def test_journal_rejects_invalid_or_forged_call_types(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "calls.json"
            path.write_text('{"calls": true, "cache_hits": 0}')
            director = LiveDirector(SETTINGS)
            with self.assertRaises(RunStorageError):
                CallJournal(path).restore(director, {"provider_calls": 0})
