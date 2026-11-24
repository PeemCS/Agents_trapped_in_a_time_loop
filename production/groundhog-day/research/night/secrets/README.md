# The eight-second fader

A producer owns the only local cassette that would make this morning’s handoff an exclusive. Its drawer combination persists across Tuesday. Her consent expires at the end of the shift. A four-turn chamber scene puts Phil, Rita and Larry on opposite sides of an acoustic window and lets the viewer inspect exactly who knew what.

[Open the measured scene and actor lenses](exhibit.html) · [Measured results](findings.md) · [All native sources and counterfactual outcomes](measured.json) · [Frozen protocol](protocol.md) · [Token-limit continuation](continuation-protocol.md)

## Mechanical evidence

The world holds immutable receipts with explicit audiences. A blocked window shows Rita the returned tin and the silent meter without identifying who returned or disconnected them. The room lamp, desk phone, outside pay phone, on-air return and the newsroom roster each communicate to a different group. The engine assembles each actor's private prompt from witnessed receipts. A private free-form note can name the combination or invent a gesture; neither changes the physical world nor enters any other actor’s request. The machine-mediated menu allows two specific disclosures, each with authored phrasing, and a consequential refusal at either stage.

The first wake restores the positions, roster and local release rights. Phil alone remembers the private disclosures he actually heard. If he learned the combination, he can take an eight-second exclusive before Rita can cut the fader. He gets the credit immediately. Rita can cut to wire and retain the roster, withdraw his board access through the rest of the shift, or separately license another twelve seconds. If he requests a fresh release, only her decision can open that twelve-second feed. A matched station-log reducer recomputes the unauthorized seconds, authorized seconds and access status from broadcast and roster receipts.

This scene hard-codes two opening actions by Phil in order to isolate what Rita saw. The canary tests exhaust all 80 legal complete action paths and check 396 actor views over 132 reachable prefix states across both sightlines. Replacing the hidden family detail, combination and audio leaves unauthorized prompts byte-identical. A second test removes Phil’s single earned combination receipt from an otherwise identical morning; the override disappears while current permission stays unchanged. The fixture paths additionally test the private audition, consent renewal, unauthorized broadcast, voluntary withdrawal and station accounting.

## Reproduce the mechanical checks

```sh
python3 -B -m unittest discover -s research/night/secrets -p 'test*.py' -v
python3 -B research/night/secrets/shoot.py --fixture-out /tmp/cassette-fixture
python3 -B research/night/secrets/analyze.py
python3 -B research/night/secrets/exhibit.py
python3 -B research/night/secrets/check_exhibit.py
```

The first two commands use the standard library and local fixtures. The analysis and exhibit generator read the archived real requests, check their hashes, validate the legal actions, replay each state and reproduce the paired summary. The final browser check uses Playwright and Chrome. Raw wire files include the full native provider response and model’s private note. Actor inputs appear beside each response. The public choices came from Qwen; authored prop lines and receipt descriptions belong to the simulator.
