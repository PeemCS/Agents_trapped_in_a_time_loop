# Sponsor setup and demo handoff

The event lists Bruin as required, AdaL for the presentation video, and a separate Best Use of BAND prize. The prototype has local integration paths for Bruin and BAND. The listing does not state a credit amount for either. [Event rules and prizes](https://luma.com/stxaoop0)

The verified Bruin run used the local CLI and DuckDB. BAND advertises a free personal plan with up to 20 remote agents, enough room for this four-character setup. The sponsor can confirm which account or credit to use for an event submission. [Bruin installation](https://getbruin.com/docs/bruin/getting-started/introduction/installation), [BAND pricing](https://www.band.ai/pricing)

## Bruin verifies the experiment data

Use the DuckDB pipeline to show what happened between the two mornings. `core.experiments` joins the prediction, the physical action, the next observation, and the result by event ID. `train.qualified_rollouts` checks that every sampled action at a checkpoint was legal and that the branch observed the same starting state and trial set. `train.local_preferences` keeps pairs with an observed return gap of at least 0.15. The training evaluator accepts only the evidence IDs that pass those checks. [Bruin DuckDB](https://getbruin.com/docs/bruin/platforms/duckdb), [Bruin custom checks](https://getbruin.com/docs/bruin/quality/custom.html)

Bring the two memory-fork artifacts and an action-rollout dataset. The [README](../README.md) has the pipeline and export commands. Open the lineage from `raw.local_rollouts` to `train.qualified_rollouts` to `train.local_preferences`. For one row, show the starting checkpoint, the two legal actions, and their recorded returns. Keep fixture and `world_rollout` rows labeled when showing the lineage. They exercise the pipeline and the local policy evaluation.

## BAND carries addressed dialogue

Create a private rehearsal room and two or more remote agents. Add the configured identities to the room. Four identities let Phil, Rita, Larry, and Ned post under their own names. The bounded canary below uses Ned’s exchange with Rita at 11:30 in world time. Copy each agent’s ID and handle to `runs/band-config.json`. [BAND Quickstart](https://docs.band.ai/quickstart)

```json
{
  "room_id": "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
  "actors": {
    "rita": {"id": "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb", "handle": "your-handle/rita"},
    "ned": {"id": "cccccccc-cccc-4ccc-cccc-cccccccccccc", "handle": "your-handle/ned"}
  }
}
```

Put the matching `BAND_RITA_API_KEY` and `BAND_NED_API_KEY` in your ignored `.env`. Use the agent keys that start with `band_a_`. Verify the room membership and identity before posting. [BAND authentication](https://docs.band.ai/security/authentication)

```sh
python3 -m loopday.band --check runs/band-config.json
python3 -m loopday.run --local --loops 1 --ticks 13 --seed 7 --policy-seed 7 \
  --band-config runs/band-config.json --band-message-limit 2 --out runs/band-canary
python3 -m loopday.audit runs/band-canary/run.json
```

The most useful proof is a sent note in the private room and the same receipt on the other agent’s next observation. The run records fallback to local delivery if BAND fails to verify a recipient. The runner acknowledges a claim after it saves the tick that consumed the message. The room receives short in-character exchanges and their loop and event IDs. [BAND message workflow](https://docs.band.ai/api/agent-api/agent-api-messages/list-agent-messages)

## AdaL presentation edit

Import a rendered scene, the side-by-side morning clip, and a short capture of the ledger. Keep the short film available on its own. Use the presentation edit to show the pencil test and the recipient handoff with readable captions. [AdaL Desktop](https://adalagent.ai/download)

| Time | Footage and narration |
| --- | --- |
| 0–7s | Replay the same 06:00 camera angle. “He broke the pencil last night. This morning it’s whole.” |
| 7–17s | Show the test, then both versions of the puddle encounter. “We can rewind to the exact same choice and remove one clue.” |
| 17–27s | Cut to Ned and Larry acting on what they saw, then Rita deciding how to end her evening. |
| 27–38s | Open one decision in the ledger and show its source events. Follow the same events in Bruin. Show the BAND room receipt here if it was verified during a real run. |
| 38–45s | End on the first changed radio broadcast. State which agents produced this run and which comparison is a local control. |
