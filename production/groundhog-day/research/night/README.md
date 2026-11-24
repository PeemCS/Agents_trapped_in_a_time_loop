# Another Tuesday · Private dress rehearsal

[Illustrated morning report](../../MORNING-REPORT.html) · [Markdown report](../../MORNING-REPORT.md) · [Watch Phil choose a point on the map](free-walk/index.html?condition=free&seed=953) · [Give Phil the dance in the rule replay](last-reel/switchboard/index.html) · [Watch the recorded missed encounter in 3D](stage3d/viewer/rialto/index.html?shot=d01-evening-reporter&view=split&at=.70)

[Watch Eight Bars and the other films with their decision ledgers](screening/index.html#rialto-cut) · [Walk the town](visual/index.html) · [Walk the true 3D stage](stage3d/viewer/index.html) · [Download the animated USDZ](stage3d/rehearsal/another-tuesday.usdz)

A Pennsylvania TV crew wakes to the same Tuesday. The intercity coach really goes to Pittsburgh. Phil can board it, call his sister, spend the night and still wake up at the hotel. Rita chooses the broadcast lineup. Larry has a single charged take. The cast can talk, decline invitations, travel and let someone else’s plan fall through.

The offline screening room plays the original couch cut, a different seed with the same setup, and an ensemble short with a participant-controlled bulletin. Selecting a shot reveals the actor’s committed action and how it fits with the other two choices. The phone cut condenses the couch sequence for a vertical screen. All rehearsed voices come from local text-to-speech and are individual to the characters. [Phone cut](editor/phone-cut/film.mp4)

## Rehearse the presentation

1. Open [the offline screening room](screening/index.html). Watch *Wednesday’s couch* with sound. Rewatch the terminal-to-hotel edit muted. Jump to *The seven o’clock bulletin* to see which of three simultaneous decisions determined the broadcast.
2. Open [the walkable town](visual/index.html). Walk through the streets, board the coach in the afternoon and use the Pittsburgh payphone. Select a recording to watch what the agents actually did. Manual play and autonomous runs have distinct labels.
3. Open [the branching comparison](branches/index.html). Two continuations can share an exact agent-visible checkpoint and diverge on one decoding seed. The page identifies its selection rule and lineage. Use [the 3D render](stage3d/rehearsal/3d-blocking.mp4) to show the same bus trip in a native DCC pipeline.
4. Read the [event-day plan](../../docs/hack-day-town.md) and the [learning design and measured failure cases](../../docs/learning-in-town.md). Keep the source and media here private. The event entry is built during the hacking block.

## Drive a live screen

To serve the films over HTTP on this Mac, use the tested range-capable server. It lets Chrome seek into a large movie before the whole file downloads. The built-in Python static server returned the whole file to a range request and stalled on cold seeks in this rehearsal.

```sh
ruby -run -e httpd -- --bind-address=127.0.0.1 --port=8765 research/night
```

Open [the local screening room](http://127.0.0.1:8765/screening/) or use its offline HTML file.

The director listens on loopback. Point it at a runner’s atomic JSON checkpoint, or pipe serialized presentation frames through an append-only journal. Both modes use the same town viewer. Without a provider, an existing take can be played offline or paced as a recorded stream.

```sh
python3 -B research/night/live/director.py research/night/takes/q27/film-transcript/seed-701.json --port 8766 --recorded-interval 3
```

Then open [the local director](http://127.0.0.1:8766/). Omit the interval to follow an actively generated checkpoint. The status line names paced streams as recorded. For an incremental producer, create a fresh journal destination and start the director in journal mode.

```sh
python3 -B research/night/live/journal.py research/night/takes/heldout/v2/seed-711.json /tmp/another-tuesday.journal
python3 -B research/night/live/director.py /tmp/another-tuesday.journal --journal --port 8766
```

A journal has one header, indexed slot frames and a final seal. A producer appends each newline-terminated record once. Each contains its predecessor’s checksum, so a changed line is detected; a writer can replace the whole take by atomically renaming a new file. Ordinary writers and readers can recompute this chain, so checksums alone cannot identify an authorized author. No raw model prompt is sent to the visual player. The raw snapshot reader rereads the saved take after a write. The journal reader processes only complete appended records, allowing long-running worlds to stay incremental. [Journal stress and corruption tests](live/journal-qa.json) · [Browser reconnection tests](live/browser-qa.json)

## Inspect the experiments

| Directory | Contents |
| --- | --- |
| [casting](casting/protocol.md) | Frozen name/memory grid, model audition, masked paired judgments, serving measurements |
| [story](story/README.md) | Deterministic physical world, actor prompts, independent roles, CLI, replay auditor and bulletin holdouts |
| [editor](editor/README.md) | Finished films, shot selections, Bruin/DuckDB assets, voice and projection receipts |
| [visual](visual/README.md) | A* routes, human free walk, actual recordings, cinematic cameras and Chrome/mobile measurements |
| [stage3d](stage3d/README.md) | Portable, animated OpenUSD production stage reimported and rendered from committed movements |
| [preferences](preferences/README.md) | Runnable, blinded preference training from a separate agent’s 45 judgments and a human-labeling interface |
| [learning](learning/social-protocol.md) | Candidate reward audit, personality-state wipe and actual collaborative scene protocol |
| [audition](audition/protocol.md) | Private voice-memo branches, full cast credentials, selective reasoning and surprise-retrieved memories |
| [sponsor](sponsor/adal.md) | Actual AdaL CLI readiness attempt and the remaining account handoff |

Every retained model take has its own source, seed, revision, physical decisions, actor-visible messages and runtime diagnostics. A single feature film uses one source lineage. Costly live serving is optional when opening any delivered film or the town. [One verified interrupted-shoot recovery](ops/restore-evidence.json)

[Read Phil, Rita and Larry’s full Qwen generations](thinking/index.html) · [Compare two decisions from the same coach platform](branches/index.html) · [Read the persona and observability research](../../docs/persona-and-observability.md)

The monitoring view joins a performer's exact prompt, the model’s native emitted thinking, its final words and the executed action. “Exact cached decision” points back to the actual model call. Both complete 27B ensemble takes and an offline copy use the same timeline. In the free-blocking experiment a second model sees a performer’s proposed gesture and maps it to the physical verbs the town can execute. A gesture can be kept as a performance proposal when the engine has no corresponding effect. [Free-blocking protocol](blocking/protocol.md)


## The wrong movie ending

[Watch Eight Bars](editor/rialto-cut/index.html) · [The full Rialto evidence](last-reel/protocol.md) · [The private cassette booth](secrets/exhibit.html) · [Rita’s interview audition](interview/findings.md) · [What survives a self-authored movie note](self-memory/results.md) · [Four distinct cuts](portfolio/README.md) · [The morning report](../../MORNING-REPORT.md)

The first 721 reporter identified the movie in the model’s exposed thinking and still boarded the coach. The movie-hypothesis reporter rehearsed the piano and chose an empty depot bench while Rita went dancing. Larry and Rita could each preserve Alma’s interview for her daughter. The external receipt gives the film a concrete consequence even with the town clock closed. The separate Wednesday follow-up shows three newly sampled choices under the alternative rule.
