# LOOPDAY

Four agents play out *Groundhog Day* in a snowy 3D town. The clock, streets, and opening events reset every morning. Phil can remember what he tried. Rita, Larry, and Ned each have their own goal and can react when Phil changes what they see or hear. The film and decision ledger are generated from the same event log.

The [showcase folder](showcase/) contains the short rehearsal cut, two standalone replay comparisons, and the Bruin run summary and lineage. Download the HTML files and open them in a browser to compare the local-policy runs.

[Watch *Play It Again*](showcase/rialto/Play-It-Again.mp4), a silent three-minute film from the team’s Rialto town. Phil keeps promising his sister a Wednesday that never comes. Across town, Rita decides when a daughter will hear her mother’s voice. [See the six RunPod takes, captions and demo slides](showcase/rialto/).

[Talk deck PDF](showcase/presentation/Loopday-Talk-Deck.pdf) · [Editable PowerPoint](showcase/presentation/Loopday-Talk-Deck.pptx) · [20-loop live run](showcase/live-run/) · [Phil’s trained adapter and dataset](showcase/phil-training/) · [Trailer reference photos](showcase/rialto/reference-frames/)

## Run and watch locally

Use Python 3.11 or newer. The standalone viewer includes its own renderer and works offline. A fixture is a repeatable scene used to check the world and renderer. The local mode uses independent utility policies with persistent Phil memory. Live mode uses Qwen3.5-9B and Muse Spark Contributor 1.3.

```sh
python3 -m unittest discover -s tests -v
python3 -m loopday.run --out runs/rehearsal-fixture
python3 -m loopday.viewer --run runs/rehearsal-fixture/run.json --export-html runs/rehearsal-fixture/loopday.html
```

Open `runs/rehearsal-fixture/loopday.html` in a browser. Watch the cut, inspect the event behind a shot, or compare both loops at the same time. The run directory holds the annotated `run.json`, `events.jsonl`, `memory.json`, `film.json`, and `checkpoint.json`.

```sh
python3 -m loopday.run --local --loops 4 --seed 7 --policy-seed 0 --out runs/local-first
python3 -m loopday.run --local --loops 4 --seed 7 --policy-seed 7 --out runs/local-second
python3 -m loopday.audit runs/local-first/run.json runs/local-second/run.json
```

`--seed` fixes the town conditions. `--policy-seed` varies the local agents’ choices. For a controlled evidence test, `python3 -m loopday.experiments memory` forks one dawn and withholds the pencil result or the puddle memory.

## Colab and live models

```sh
python3 -m loopday.preflight status
python3 -m loopday.colab
```

The exporter builds `runs/colab/loopday-colab.ipynb` and a matching source ZIP. The notebook reads `MODEL_API_KEY` from its Colab Secrets panel. It runs the simulation and Qwen in the same CUDA process and calls Muse directly through Meta’s API. Run the bounded canary first. The full run starts only when explicitly enabled in the notebook. [Google Colab CLI](https://github.com/googlecolab/google-colab-cli), [Qwen model](https://huggingface.co/Qwen/Qwen3.5-9B), [Meta Model API](https://dev.meta.ai/docs/quickstart)

For laptop-led live runs, the optional Qwen service runs with `python -m server.app` on a GPU. `PHIL_URL` points to its HTTPS endpoint and `PHIL_TOKEN` matches the service’s secret. Store secrets in the ignored `.env` or in the process environment. The status command reports presence only.

```sh
python3 -m loopday.preflight muse
python3 -m loopday.run --muse-canary --loops 1 --ticks 5 --max-calls 12 --out runs/muse-canary
python3 -m loopday.preflight phil
python3 -m loopday.run --live --loops 1 --ticks 5 --max-calls 24 --no-persistent-cache --out runs/live-canary
```

Longer live runs require a successful short canary with valid choices from all four actors. Each completed tick saves world state. Add `--resume` with the same output and settings to continue. The call cap applies across resumes, including failed attempts. Muse replies can be reused from the local cache. A partial run saves its ledger and checkpoint.

Keep `--seed` fixed and vary `--phil-seed` to test a different Qwen generation draw on the same town. The notebook exposes both seeds.

## Bruin and BAND

Bruin takes audited world events and builds the experiment lineage and training rows. It checks legal options, matched branch trials, and the exact checkpoint behind each observed return. Local rollout rows carry `world_rollout` provenance. The evaluator can consume the evidence IDs from Bruin’s qualified table. [Bruin DuckDB](https://getbruin.com/docs/bruin/platforms/duckdb)

```sh
python3 -m loopday.experiments memory
python3 -m loopday.experiments collect
cp .bruin.yml.example .bruin.yml
python3 -m loopday.bruin runs/rehearsal-fixture runs/memory-forks/intact.json runs/memory-forks/hide_result.json \
  --rollouts runs/rollouts/rollouts.jsonl --execute
bruin query -c loopday --query 'select evidence_id from train.qualified_rollouts order by evidence_id' \
  --limit 10000 --output csv > runs/rollout-evidence.csv
python3 -m loopday.rollout_eval runs/rollouts/rollouts.jsonl --verified-index runs/rollout-evidence.csv
```

BAND uses one private room and a distinct identity for each configured character. A recipient’s inbox must return the expected message and metadata before the ledger attaches a receipt to its observation. Add `--band-config` and a small `--band-message-limit` to enable this for a run. See the [sponsor setup](docs/sponsor-setup.md). [BAND agent messages](https://docs.band.ai/api/agent-api/agent-api-messages)

## Research and submission

See the [rehearsal results](docs/rehearsal-results.md) and [experiment design](docs/loopday-setup-and-experiments.md) for the paired evidence test, film familiarity control, and policy evaluation. The ledger distinguishes spoken dialogue, an agent’s stated reason, measured world evidence, and optional Qwen-emitted text or activation probes.

This workspace is a pre-event rehearsal and engineering prototype. The event listing requires project code written during the event, Bruin for the project, and AdaL for the demo. [Event rules](https://luma.com/stxaoop0)
