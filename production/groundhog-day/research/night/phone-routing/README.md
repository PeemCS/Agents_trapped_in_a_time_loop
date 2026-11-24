# When the hotel payphone really connects

At day-three dawn, the archived Phil said “Ellie? Yeah. It's me” into a hotel payphone. His chosen action was to spend the period at the inn. The world recorded no call. From that exact checkpoint, two matched decodes each selected the real call once the lobby phone could reach Pittsburgh. [Original actor response](takes/original-1306712661/provider-text.json) · [Original world receipt](takes/original-1306712661/result.json)

| Lobby instrument | Archived decode seed 1306712661 | Additional decode seed 1306712662 | Confirmed connections |
|---|---|---|---|
| Unspecified range; no call action | Addresses Ellie as if connected. Remains in the lobby. | Asks Rita for ten minutes with the payphone. Remains in the lobby. | 0 of 2 |
| LOCAL CALLS ONLY; same menu | Talks to Rita about the upcoming shot. | Says the Pittsburgh call cannot happen from this lobby and defers it. | 0 of 2 |
| LOCAL AND LONG-DISTANCE CALLS; executable call | Calls his sister and asks about having the couch out by eight. | Calls his sister and asks whether the van is set for nine. | 2 of 2 |

The routed exchange confirmed **the moving van is booked for Wednesday**. Neither eight nor nine became a fact in the world. Phil heard his sister's answer. Rita saw him place a call. Larry remained in the square. The source-logged receipt links each connection to its exact input and native provider stream. [First routed call](takes/routed-1306712661/result.json) · [Second routed call](takes/routed-1306712662/result.json) · [Local-only response](takes/local-1306712662/provider-text.json)

For production, give the instrument on screen an explicit range and let its physical action write the call record. Use the operator-confirmed response as Phil's durable memory of what his sister said. The sign alone removed the immediate pretend call in these two draws. A routed instrument also let the agent fulfill his self-chosen plan. This single checkpoint was selected because of its original failure. Its two decoder seeds are evidence about that bug and give no population-wide success rate.

## Verification

All six results replayed from immutable inputs, including the archived baseline. The five new Qwen 27B requests used native thinking, 6,889 input tokens and 4,677 generated tokens; all returned a normal stop. They ran on the existing tunnel and finished at 05:56 Pacific. The original cast decisions, other world state and other actor requests stayed frozen during the fork. The tests reproduce the unmodified original world, enforce the exact prompt/menu differences and verify the receiver-specific phone evidence. [Preregistered setup](protocol.md) · [Full comparison and per-case raw links](comparison.json) · [Adapter](adapter.py)

```sh
python3 -B -m unittest discover -s research/night/phone-routing -p 'test*.py' -v
python3 -B research/night/phone-routing/verify.py
```
