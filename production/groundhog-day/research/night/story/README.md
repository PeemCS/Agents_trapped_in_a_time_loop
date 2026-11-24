# The repeating town · headless dress rehearsal

Run from the project root. Python 3.10+ and its standard library are sufficient. The simulation is private pre-event research. A logged-in GPU account is unnecessary for replay, tests or fixture checks.

## Shoot and resume

```sh
python3 -B research/night/story/town.py run --backend fixture --days 3 --seeds 701 --out /tmp/town-fixture
python3 -B research/night/story/town.py run --backend ollama --base-url http://127.0.0.1:11434 --model MODEL_TAG --model-revision MODEL_DIGEST --cast film --memory receipts --days 4 --seeds 701 702 703 --out /tmp/town-film-receipts
python3 -B research/night/story/town.py run --backend openai --base-url http://127.0.0.1:8000/v1 --model SERVED_NAME --model-revision MODEL_REVISION --cast neutral --memory transcript --days 4 --seeds 701 702 703 --out /tmp/town-neutral-transcript
```

The two live commands illustrate separate transports and treatments. To compare memory or names, keep the same backend, weights, sampling settings, day horizon and seed, and change only the declared treatment. Use a distinct output directory for every configuration. For authenticated endpoints, set the key in the environment named by `--api-key-env`; the default variable is `TOWN_API_KEY`. Request logs omit endpoint credentials.

The native Ollama adapter sends a JSON schema, a 256-token output cap, an 8,192-token context limit, and disables thinking by default. For another server, `--response-format schema|object|none`, `--thinking off|on|default`, `--omit-seed` and `--workers 1|2|3` select its supported features. A provider may ignore optional fields. Actual per-call token counts and termination reasons are retained when the provider supplies them.

Use the same command after an interruption. Each committed world tick replaces the checkpoint atomically under an exclusive root lock. Successful decisions from a partly sampled tick survive in the hidden per-root request journal. Back up both the JSON take and the corresponding `.requests-SEED` directory. There is a small unavoidable gap between a provider finishing a paid request and its local response reaching disk. Failed HTTP connections without a completed response cannot be costed from these traces. A completed rerun reads the take without calling the model again. The loader refuses to splice a new model, prompt version or treatment into an existing take. After two invalid answers for one slot, the take remains partial. The error is an infrastructure/format failure and does not count as an in-world decision.

## What the three agents do

Phil can file a report, spend his own time, travel locally, take the afternoon coach, call his sister from Pittsburgh and stay there that night. Every next morning starts in the hotel, with his own observed history. Rita can file a tape or independently put a previously recorded tape on air. Larry starts at the bandstand with one battery charge for festival footage or a cornet-player portrait. All three choose from the places and people within reach. In the neutral cast, identical roles are called Ellis, June and Cal.

Each of four periods freezes the same world for all three planning calls. An actor can speak within earshot before moving. Each actor’s observations include the people they personally see depart or arrive. Someone left behind cannot infer another traveler’s actual destination solely from their departure. A private intention stays with its owner. Residents forget their encounters at dawn. An exact resident request with the same role, visible evidence, legal choices and sampling seed reuses the same result. The reporter has per-day sampling latitude. If two agents reach for the last rack of dishes, a seeded resolver grants its physical effect once. Stage directions inside dialogue cannot spend a ticket or commandeer another character. The open-ended `try_something` verb consumes time and preserves the proposal. The result of an arbitrary act is tagged as unverified until the world supports its effect.

The [frozen evaluation](evaluation.md) distinguishes the recurring date, a hypothesis of recurrence, a specific cultural comparison and an act motivated by that comparison. The code makes no end-of-loop reward available. The final evening's independently chosen coverage, travel and work give the take a physical ending. A character's words, intention, and physical receipt are separate data fields.

## Replay and audit

```sh
python3 -B research/night/story/town.py review /tmp/town-fixture/seed-701.json
python3 -B research/night/story/audit.py /tmp/town-fixture/seed-701.json --report /tmp/town-audit.json --public-replay /tmp/town-replay.json
python3 -B -m unittest discover -v -s research/night/story -p 'test*.py'
python3 -B research/night/story/scaling.py --out /tmp/fixture-scaling.json
```

The auditor rebuilds the actor’s exact observable request, menu, sampling seed, chosen action, witness set, next state, cache sources and unique event IDs. It also indexes potential references in each character’s actual dialogue and separates any previously visible cue. Matched takes can fork on the same seed while retaining different character names or memory. A regular expression match is an editorial lead. A person saying the holiday name or a cameraman discussing film provides weak evidence on its own.

The presentation trace contains one protagonist event per slot and two same-shaped nested `cast` events. It includes the public decision, words, simple receipt, role ID, named actor and physical location transition. It omits the prompt, private intentions and raw provider output. An event address combines the full take SHA-256 with a stable within-take ID such as `d03-t02-reporter`. Import `audit.compact_event(event)` to project a live slot and `audit.pack_run(row, source_sha256=None)` to package partial/complete archives. When rendering, animate a genuine coach trip via the station even if Phil originally chose the coach while at a local venue. A fresh `inn` origin at the next day's first slot is a dawn reset, never a return bus journey.

## What the controlled scaling check found

The [fixture measurements](fixture-scaling.json) hold every actor's physical actions fixed. At the twentieth morning, the bounded receipt view supplied 2,722 bytes of role and observation text to the reporter. An unbounded transcript supplied 13,579 bytes. The small memory retained the first witnessed coach arrival but had already dropped the confirmed call with his sister by the fourth morning. This is a concrete cost of privileging travel anchors. Preserve one role-chosen unresolved commitment and one post-outcome contradiction if that effect survives a separate matched test.

For 20 days, the compact presentation data was about 78 KB for 240 actor decisions. The raw receipt take was about 1.0 MB and the transcript take about 1.8 MB, before private attempt-journal duplicates. These are CPU-only fixture sizes. The full take checkpoint is rewritten at each tick. At production-scale durations and concurrency, move the source records into a transactional append-only store with one row per slot and an outbox for observer events, retain periodic snapshots, and use the same presentation projection for streaming and file replay. Horizontal batching across independent roots is possible at every synchronized turn, with fixed serial dependency inside each world.

The reporter’s spontaneous recognition, a credible behavioral change and a good finished scene require real model evidence. Fixture results establish mechanics and scaling of the data path.

## Held-out ending experiment

The measured v1 sampler remains in `town.py`. The [preregistered second experiment](holdout-v2.md) compares it to the separately versioned `v2.py` on four fresh six-day roots. Both arms use the same seeds and initial cast.

```sh
python3 -B research/night/story/v2.py run --backend fixture --days 3 --seeds 711 --out /tmp/town-v2-fixture
python3 -B research/night/story/v2.py run --backend ollama --base-url http://127.0.0.1:11434 --model MODEL_TAG --model-revision MODEL_DIGEST --days 6 --seeds 711 712 713 714 --cast film --physical move --memory wakes --ending bulletin --out /tmp/town-v2-holdout
python3 -B research/night/story/audit.py /tmp/town-v2-fixture/seed-711.json --public-replay /tmp/town-v2-replay.json
```

An optional spoken line accompanies each physical choice. The reporter can tell his producer goodbye and board the coach in one period. At the end of the day Rita controls a portable station switcher, Phil can dial the reporter return from his actual location, and Larry can send footage that his camera actually captured. They also choose whether to exchange invitations and accept them over the crew radio before the bulletin. Those decisions are sealed before they see anyone else’s choices. A promise to send material, a contribution actually sent, and a contribution selected for air remain separate.

The seven o'clock result and contributor event IDs live in `world_after.bulletin`. It records live audio, a camera take, a previously filed reel, the producer’s own microphone, an empty selected return or the station ident. Silent microphones are labeled explicitly. The replay projection preserves the final channel and credits. The engine still wakes the reporter in his hotel the next morning. The rendering host should cut between his actual evening location, the on-air tally, and the fresh hotel morning.

Separately switch off grouped memory with `--memory flat`, allow talk to occupy the action slot with `--physical talk-action`, or remove the evening bulletin with `--ending ordinary`. Keep these exploratory forks outside the four-pair combined-intervention analysis.


After both shoots finish, this command verifies the raw actor decisions and prints one paired summary per seed. The written report includes prompt-visible cues for each candidate reference, observed handoffs, final-channel counts and their empirical entropy in bits. It checks source hashes, cast, horizon and matched configuration before aggregating.

```sh
python3 -B research/night/story/compare.py --baseline /path/to/v1-six-day-takes --variant /path/to/v2-six-day-takes --seeds 711 712 713 714 --days 6 --out /tmp/town-v2-paired-summary.json
```
