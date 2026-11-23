from array import array
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import wave

from loopday.film_audio import RATE, render_audio
from loopday.rehearse_voices import DIRECTIONS, VoiceError, _pcm, _write_pcm, fit_line, prepare_voices, spoken_text
from loopday.render_film import _ffmpeg


def sample(seconds):
    return array("h", (2_800 if index % 21 < 10 else -2_800 for index in range(round(seconds * RATE))))


def rehearsal_plan():
    shots = []
    for index, actor in enumerate(DIRECTIONS):
        shots.append({
            "event_id": f"e{index}", "actor": actor, "caption": "Is the town ready for the morning?",
            "speaker": actor, "duration_ms": 3000, "start_ms": 3000 * index, "sound": None, "loop": 1,
        })
    return {"shots": shots, "duration_ms": 12_000}


class VoiceRehearsalTests(unittest.TestCase):
    def test_pronunciation_changes_only_spoken_copy_and_strips_directives(self):
        raw = "Ned Ryerson in Punxsutawney. [[rate 500]]"
        adjusted = spoken_text(raw)
        self.assertIn("Ned RYE-er-son in Punk-suh-TAW-nee", adjusted)
        self.assertNotIn("[", adjusted)
        self.assertNotIn("rate 500", adjusted)
        self.assertEqual(spoken_text("I have time for one more song."), "I have time for one more song.")

    def test_zero_frames_and_silence_are_not_reported_as_speech(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "empty.wav"
            for frames in (0, 12_000):
                _write_pcm(path, array("h", [0]) * frames)
                with self.assertRaisesRegex(VoiceError, "no audible frames"):
                    _pcm(path)

    def test_uses_four_distinct_working_voices_and_writes_event_keyed_wavs(self):
        plan = rehearsal_plan()
        installed = {profile.candidates[0] for profile in DIRECTIONS.values()}
        with TemporaryDirectory() as temp:
            out = Path(temp) / "voices"
            with patch("loopday.rehearse_voices.local_voices", return_value=installed):
                with patch("loopday.rehearse_voices._speech", side_effect=lambda text, voice, rate, dest:
                           _write_pcm(dest, sample(.8))):
                    result = prepare_voices(plan, out)
            self.assertEqual(result["spoken"], 4)
            self.assertEqual(result["captions"], 0)
            self.assertEqual(len(set(result["voices"].values())), 4)
            for shot, record in zip(plan["shots"], result["events"]):
                self.assertLess(record["seconds"], record["budget_s"])
                self.assertEqual(shot["caption"], record["caption"])
                with wave.open(str(out / (shot["event_id"] + ".wav")), "rb") as voice:
                    self.assertEqual(voice.getnframes(), round(.8 * RATE))

    def test_a_missing_voice_leaves_the_score_and_captions_intact(self):
        plan = rehearsal_plan()
        with TemporaryDirectory() as temp, patch("loopday.rehearse_voices.local_voices", return_value=set()):
            root = Path(temp)
            out = root / "voices"
            result = prepare_voices(plan, out)
            self.assertEqual(result["spoken"], 0)
            self.assertEqual(result["captions"], len(plan["shots"]))
            self.assertEqual(list(out.iterdir()), [])
            silent = root / "score.wav"
            fallback = root / "score-fallback.wav"
            render_audio(plan, silent)
            render_audio(plan, fallback, voice_dir=out)
            self.assertEqual(silent.read_bytes(), fallback.read_bytes())

    def test_fitting_retries_at_a_higher_rate_without_truncating(self):
        rates = []

        def synth(text, voice, rate, dest):
            rates.append(rate)
            _write_pcm(dest, sample(3.15 if len(rates) == 1 else 2.5))

        with TemporaryDirectory() as temp, patch("loopday.rehearse_voices._speech", side_effect=synth):
            fitted, final_rate, tempo = fit_line("One more song before we go.", "test", 150, 2.8, Path(temp))
        self.assertEqual(len(rates), 2)
        self.assertGreater(rates[1], rates[0])
        self.assertEqual(final_rate, rates[1])
        self.assertEqual(tempo, 1.)
        self.assertLessEqual(len(fitted) / RATE, 2.8)

    def test_minor_tempo_adjustment_preserves_the_duration_bound(self):
        try:
            _ffmpeg()
        except RuntimeError:
            self.skipTest("The optional timing polish requires FFmpeg")
        with TemporaryDirectory() as temp:
            with patch("loopday.rehearse_voices._speech", side_effect=lambda text, voice, rate, dest:
                       _write_pcm(dest, sample(2.55))):
                fitted, rate, tempo = fit_line("The agent has a line with extra words.", "test", 245, 2.4, Path(temp))
        self.assertEqual(rate, 245)
        self.assertGreater(tempo, 1.)
        self.assertLess(len(fitted) / RATE, 2.4)


if __name__ == "__main__":
    unittest.main()
