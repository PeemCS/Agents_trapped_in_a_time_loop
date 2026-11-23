# LOOPDAY film and replay

The 3D film reads the same event sequence as the decision ledger. The edit favors recorded actions linked to an experiment or ending, with repeating camera setups for visual comparisons. Each shot retains its source event ID, and **Inspect this shot** opens that event. **Compare loops** aligns recorded towns and decisions by their in-world time. A two-run export puts the last loop from each run side by side, and **Replay both** animates both outcomes from the same camera phase.

For the hackathon presentation, run the film first. Pause after the second puddle shot and open the linked ledger. In the memory comparison, start at 06:30 on loop two to show the changed action with the same opening and the same physical reset result. In the ending comparison, follow Rita’s reply and the later ending decision. The final February 3 shot uses the recorded ending.

## Create the cut

The simulation and portable HTML use Python 3.11 or newer. A browser can open the exported HTML file directly. Browser playback uses WebGL depth when available and Canvas 2D as a fallback. The portable file carries the town, captions, comparison data, and playback code. It can be transferred as a single file. The policy-version-2 showcase is in `runs/showcase/`, with a paired memory replay in `compare-memory.html`.

```sh
python3 -m loopday.viewer \
  --run runs/showcase/rita/run.json \
  --compare-run runs/showcase/community/run.json \
  --label 'Rita stays' --compare-label 'The town recognizes Phil' \
  --compare-tick 32 --export-html runs/showcase/compare-endings.html
```

The normal `python3 -m loopday.viewer --run PATH` command serves the same interface on localhost. The HTML export omits raw model completions, observations supplied to the policy, credentials, and optional model-emitted text. A trace explicitly captured in a model run can be inspected locally with `--include-model-traces`. The ledger displays the character’s stated reason and independently linked world evidence. Local policy scores and measured model activations have separate labels.

## Watch events arrive

Start the observer in a second terminal and point it at the run's output directory. Open the printed localhost URL. A waiting screen switches to **In progress** after the runner commits its first events. New committed choices appear with their source. **Open replay** loads a snapshot of the run at the time you open it.

```sh
python3 -m loopday.viewer --follow --run runs/live-demo/run.json
```

The observer reads the world from atomic checkpoints and switches to the final artifact when it is available. It labels live Qwen and Muse choices, locally scored choices, scripted fixture choices, and reused prior decisions. It also works with the partial local rehearsal at `runs/film-qa/release/witness-local/`.

## Video exports

To export a captioned MP4, use Pillow 10.1 or newer and FFmpeg. The renderer can also use the bundled FFmpeg executable from an installed `imageio-ffmpeg` package. The projection runs through system JavaScriptCore on macOS or Node.js elsewhere. When a C compiler is available, the offline renderer uses depth testing for precise occlusion.

```sh
python3 -m loopday.render_film \
  --run runs/showcase/rita/run.json \
  --out runs/showcase/rita/loopday.mp4 \
  --captions runs/showcase/rita/loopday.vtt

python3 -m loopday.render_film \
  --run runs/showcase/rita/run.json --teaser \
  --width 540 --height 960 \
  --out runs/showcase/loopday-vertical.mp4
```

The first command exports the complete short. The second builds a portrait edit from the actual opening, experiment, matched puddle passes, and piano beat. Pass an output ending in `.png` together with `--start` to inspect a specific moment. Standalone captions are available as `.vtt` or `.srt`.

The player can synthesize dialogue with available on-device English voices. It chooses a delivery profile per character and reads the recorded line. Browser video capture saves the rendered film with its score and effects when sound is enabled. An offline MP4 can also mix authorized voice recordings by passing `--voice-dir` with one PCM WAV per speaking event ID, such as `e00111.wav`. [Web Speech API](https://webaudio.github.io/web-speech-api/#dom-speechsynthesisvoice-localservice), [MediaStream Recording](https://www.w3.org/TR/mediastream-recording/)

## Personal Mac voice rehearsal

From a local Mac Terminal session, generate voice clips keyed to each event and render them into a private rehearsal copy. The script assigns separate installed voices and pacing to Phil, Rita, Larry, and Ned. It adjusts pronunciation in the spoken copy, keeps the captions verbatim, and checks each clip against the speaking time before mixing it.

```sh
python3 -m loopday.rehearse_voices \
  --run runs/showcase/rita/run.json \
  --out runs/private-voice-rehearsal/voices

python3 -m loopday.render_film \
  --run runs/showcase/rita/run.json \
  --voice-dir runs/private-voice-rehearsal/voices \
  --out runs/private-voice-rehearsal/loopday.mp4
```

The manifest reports the voice, duration, and available speaking time for each line. Empty audio, unavailable voices, and lines that exceed their speaking time retain their captions and score. Apple limits system voices to personal, noncommercial work. Keep the resulting clips in your private rehearsal and use the score-only cut for sharing. [macOS Tahoe Software License Agreement §2F](https://www.apple.com/legal/sla/docs/macOSTahoe.pdf)

## References and assets

The scenario takes its winter town, 6 a.m. alarm, broken pencil, repeating street encounter, and piano performance from the film’s documented events. The three camera compositions for the clock, pencil, and puddle repeat on purpose so changes are legible. [Sony Pictures film page](https://www.sonypictures.com/movies/groundhogday), [AFI Catalog](https://catalog.afi.com/Catalog/moviedetails/59539)

The sets, actor meshes, colors, sound effects, and music in this implementation were created for LOOPDAY. The audio motifs are generated from the notes in `loopday/film_audio.py` and `web/sound.js`. The rendered footage and event captions are generated from the project’s own assets and simulation logs.
