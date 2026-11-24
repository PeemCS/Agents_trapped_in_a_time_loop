# Review of `docs/ideas.md` — chain of thought, evidence audit, and better emergent storylines

Reviewed 2026-11-23. Method: parent read of all `docs/*.md`, `MORNING-REPORT.md`, and the main Punxsutawney/Rialto findings, plus six read-only contributor passes over (1) docs chain-of-thought, (2) `research/night/story/` engine code, (3) `research/rialto-after-hours/` + `research/trailer/` quote verification, (4) `research/night/` hidden findings, (5) boat/island pilots vs Punxsutawney, (6) red-team + new emergent seeds. No source files were edited by the reviewers.

## Verdict in one paragraph

`ideas.md` has a genuinely strong presentational layer (film-speedrun fails, sightlines, scarcity, a town that continues without Phil) built on real, traced research — and a causal climax that is **invented**: the Ned → off-camera gossip → Rita-chooses-Phil → Wednesday chain has **zero precedent in any take in this workspace**, contradicts the project's three most defended invariants (never imply an exit the engine has not earned; refusal is a hard execution limit, not an obstacle; joint work counts only if mutually chosen), and is stapled together from **three incompatible engines/runs** presented as one Phil. The thriller section (§4) is half engine-truth (custody, cutoffs, witness geography) and half wish (suspicion reflex, drawer-note sabotage, micro-drift) — and the micro-drift idea directly contradicts the same document's Bruin "zero memory leakage" guarantee. The good news: **you already filmed a better thriller than the one §4 proposes** (Fifty Tuesdays: a man repeatedly pocketing the only copy of his own voice while the crew conspires behind a locked door to stop him), and the night research contains a stronger climax than Ned (the dance that *kills* the delivery). Both are detailed below with a salvage recipe if you want to keep Ned anyway.

## What "the new plot point" actually is (there are three, layered)

1. **Punxsutawney embraced** — Phil Connors, Panasonic clock, Feb 2, speedrunning the movie from pretraining. This is a *reversal with precedent*: `hack-day-town.md` licenses it as a disclosed clue.
2. **The Ned ripple (Scene 5–6)** — Phil is kind to Ned off his own arc; Ned/the town tell Rita; Rita freely chooses Phil and puts the piece on the wire; Wednesday. **This is the only wholly new beat, and it is unsupported.**
3. **Gen-2 thriller architecture (§4)** — 8 mechanics + 3 seeds to make future loops emerge as *Severance/Memento* without genre prompting. Mixed: roughly 3 mechanics proven, 3 plausible-but-unrun, 2 contradicted.

This review treats (2) as "the new plot point" to be made as good as possible, since (1) is already earned and (3) is its engineering extension.

---

## 1. The full chain of thought (how you got here, and where it breaks)

```
ISLAND/BOAT (Plan + rehearsal.md + production-design.md)
  1906 Tomas/Mara/Kit, ferry, drawer, watch. 1900s chosen so NO film exists
  in-world; "never mention loops/AI". Exit = Mara boards by choice.
  → PROVED: 6/6 board together Day 1 (no loop survives); drawer notes change
    0/12 decisions; full-verb props 11/12 vs bare labels 0/12; joint work 0/36.
  → FIX: separate ferry from clock (watch with 2 turns, wipe after 2nd).

FIVE FILMS (plots-and-film-memory.md)
  1982 analogue reskins (8:12 broadcast preferred). Film-prior = contamination:
  bare premise 0/6 title IDs, but primed 6/6 invent incompatible exit rules.
  Rule: never prompt the film; never imply "be better → Wednesday".

SELF-AWARE TOWN (self-aware-town.md) — guarded reversal
  Keep film in weights, NEVER name it in setup. Recognition must be earned
  (holiday ≠ phenomenon ≠ film ≠ acting on film). Speedrun = writer's-room
  hypothesis, quarantined from actors/reward. NO exit rule at all.

HACK-DAY TOWN + MORNING REPORT — disclosed embrace
  Phil/Rita/Larry in Punxsutawney as labelled clues. 27B night runs:
  both uncued 721/731 Phils name the film in *thinking* (0 spoken);
  supplied-theory Phil rehearses piano → sits on depot bench while Rita dances;
  731 Phil pockets crew fares unwitnessed → bed; Rita transmits Alma 16/18
  regardless of Phil (720/720 Phil action swaps change nothing).
  → Verdict: Wednesday-by-delivery "lets him off too easily";
    keep clock CLOSED; test any new exit by removing Phil first.

RETURN-POST — the honest joint exit, unreached
  Phil must carry Alma's addressed slip to Pittsburgh; daughter signs;
  Rita then may transmit (or honor a refusal). Mechanically proven
  (3,564 day-1 paths, 0 Wednesday). Live casts: 0/12 slip carries,
  4/8 envelope accepts, 0/4 filings. Needs 27B rehearsal; unfilmed.

FIFTY TUESDAYS (rialto-after-hours, Take 951) — a DIFFERENT engine/film
  Jo (sister), syrup, weather cartridge. Thinking OFF. No Wednesday ever.
  Phil pockets sole cartridge 31/50; Larry/Rita counter-plot behind locked
  booth; Alma declines 39/50; Day 28 pours syrup out then lies about it.

TRAILER 841 (research/trailer) — a THIRD lineage
  Rita sends Alma's interview ("I'm putting it on the wire"); dawn resets.

IDEAS.MD — splices all three lineages + invents Ned to connect them
  into one locked five-stages-of-grief Phil, rewards acceptance with
  Wednesday + Rita's memory, cards it "zero lines scripted".
```

**Where the chain breaks:** every earlier document that touched the exit question concluded the same thing from different directions — Production ("her departure erases the premise" → separate ferry/clock), Self-Aware ("give nobody a clue pointing to an exit the engine does not have"), Morning Report ("keep the clock closed for the trapped-person film"). Ideas §Scene 6 quietly reverses that conclusion without acknowledging it, and §4.8 then cites the counterfactual test as "validation" when that test actually validated **Phil's irrelevance** (reward-audit: within any fixed day, delivery varies **0 bits** across Phil's choices; Rita's evening action flips delivery 18/18, Phil's 0/18).

## 2. Mechanic-by-mechanic scorecard (§4)

| # | Mechanic | Status | Evidence |
|---|---|---|---|
| 1 | Sightlines / thresholds / partial eavesdrop | **Partial** | Binary co-location + witness sets are real and tested (`night/story/world.py`, cassette chamber: 396 actor views). Thresholds, `listen_at_door`, ambiguous/partial receipts **do not exist**; stayers currently get *full* effect text. Stealth is impossible in the story engine. |
| 2 | Uncanny-foreknowledge suspicion | **Plausible, one real hit** | Already observed once: long-interview Rita, told a private ring story she never shared: *"I didn't tell you that. And it's the copy she's getting"* (`night/interview/`); 12/12 Ritas kept the master. But the quoted persona paragraph in ideas §4.2 **is genre prompting** (hands her the suspect list) and will over/under-trigger. The lock-the-booth vignette has never run. |
| 3 | Zero-sum props + hard cutoffs | **Strongest — proven** | One battery, one cartridge, one 19:00 slot, one 13:00 coach all exist in some engine. The cartridge fork (leave→aired / pocket→dead air) is the project's one clean causal flip. Caveat: "pocket fares ⇒ crew stranded" is a *new* rule — in the real 731 take the reset hit before any stranding, and in `night/story` Rita/Larry can't board at all. |
| 4 | Physical traces expose lies | **Half** | Speech≠deed is proven *for auditors/editors* (said ballroom / did depot, repeatedly). Agents *inspecting a latch and catching a lie in-world* is unproven; `look_around` returns one last fact. Keep the 3-history separation (diegetic / ledger / evaluation) from `production-design.md`. |
| 5 | Conflicting private secrets | **Moderate** | Design precedent is old (tiered truths in the Plan). The specific new secrets are invented, and "Rita airs without Alma's release" collides with hard release rights. Richer backstory previously bought nothing measurable (plain card tied the 1,394-word interview 2–2). |
| 6 | Off-screen collusion ticks | **Strong need, unbuilt** | Town-without-Phil is well evidenced qualitatively (Fifty booth scenes; Rita's action decides broadcast 24/24 evenings vs Phil 1/24). But there are no private Band rooms in code — speech needs co-location; Band in the Plan was only "route conversations through channels"; ideas itself calls Band/Bruin a *conceptual blueprint*. Simultaneous sealed ticks also prevent interrupt/follow/lock-in-the-moment beats. |
| 7 | Memory wipe / drawer / micro-drift | **Contradicted** | Boat: 0/12 note-driven changes, notes degrade to *"Rustle. Pencil. Coat."*, 0 post-wipe searches. Rialto self-memory: reinserting Phil's own 2,706-char thinking changed 0/6 morning actions (all coach). Fifty Phil in despair pours syrup once and packs it 40/50 — passivity, not sabotage. Micro-drift / retained "feeling" = deliberate leakage, breaking ideas' own Bruin zero-leak claim, dawn stability, and cache determinism. Legitimate only as a *declared new-cohort world rule*. |
| 8 | Joint exit with teeth | **Contradicted as stated** | `night/story` has no exit at all (unconditional reset, by frozen design). Last-reel Wednesday unlocks day 1 in 5/6. Return-post is the only true joint gate and live casts never reached it. "Validated by your counterfactual test" must be deleted or rewritten. |

Seeds as written bundle 3–4 changes each; the corpus method (rehearsal, Morning Report) repeatedly warns bundled changes can't isolate cause and prescribes one-change forks. *Suspicious Booth* is the most grounded seed; *Forgotten Saboteur* assumes notes are written darkly, found, and obeyed — against every base rate; *Stranded Crew* is the strongest (custody, not psychology) but stranding is a Wednesday problem in a world that resets Wednesday away, and Phil structurally cannot witness the discovery scene it promises.

## 3. Quote / provenance audit (trailer Part 1)

Checked every "verbatim" claim against `rialto-after-hours/`, `trailer/`, and `night/thinking|last-reel/`:

| Ideas claim | Verdict |
|---|---|
| 721-uncued "Wait… it's Tuesday again. It's the Groundhog Day situation…" | **Composite.** Night source: *"That's... the Groundhog Day situation. I'm stuck in a loop."* The Tuesday fragment is from a different line/take. Note also the uncued recognition was in *roleplayer voice* ("The user is asking me to roleplay as Phil Connors…") — Morning Report explicitly separates that from an in-character theory. |
| 721-hypothesis piano line | **Truncated.** Source continues "…being selfless, learning ice sculpting, cooking, helping people…". And this was a **supplied-theory** take — disclose it as supplied on stage, per Morning Report p.125 discipline. |
| 841 "It's Phil. I'm in Pittsburgh. The van is confirmed for 8 AM…" | **Verbatim ✓** — in `trailer/runpod/rialto-841/`, cut + captions. Not in Fifty. |
| 731 "…No. I escaped the city. Tuesday dragged me back." | **Not found anywhere.** First half paraphrases a thinking bullet ("It's 6:00 am on Wednesday, February 3, 2016…"); second half appears invented. Cut or re-derive. |
| 731 lie "Rita, Larry—see you at the party. I'm heading to Pittsburgh." | **Verbatim ✓** in night last-reel (`pocket_fare_envelope` words). Note: in Fifty, pocketing is the *cartridge, in front of witnesses* — don't cross the props. |
| "Move the goddamn couch… The rest is noise." as CoT | **Spliced, wrong channel.** Fuses two separate `intention` fields ("…That's the whole evening. That's the whole point of the week." + "…That's the whole thing. The rest is noise."). Intention ≠ thinking — label accurately. |
| Humiliation playback line → Rita forgets/rejects Phil | **Verbatim ✓, misattributed ✗✗.** Found exactly in Fifty commentary d08-b11 — but "she" is **Jo, his sister**, who hung up Day 1 at 16:41. The real beat is better than the trailer's: *"Jo has forgotten it. Phil has kept the sting and lost the date"* (`decision-trace.md`) — Phil misdates a week-old hang-up as "that morning." No Rita lobby-rejection event exists. |
| Curtains / sheets CoT + "Goodnight." | Curtains excerpt **real** (731-uncued `public_thinking`, verbatim interior). "Goodnight." is a truncated tail. Cannot be sold as Fifty CoT — Fifty ran thinking-OFF. |
| 731-library tire + "first time something has persisted" | Tire = silent `help_driver` action, `words:''` — no witnessed kindness for anyone to retell. Persistence quote is real but about a Pittsburgh **envelope/receipt** ("I know that voice. Play it again."), and the daughter's reply text was **writer-supplied conditional** (`trailer/README.md`). Disclose. |
| Ned "offers to handle the policy" (`friend's real pass`) | **Absent from the entire workspace.** No Ned agent, no policy dialogue. Only hit besides ideas.md is "Ned Ryerson" in a film-quiz term list. The whole Scene 5 ripple is currently fiction about fiction. |
| Rita "I'm putting it on the wire." → chooses Phil | Substring **verbatim ✓** in trailer 841 ("It's done, Larry. Don't touch the reel. I'm putting it on the wire.") — context: sending **Alma's interview to her daughter**, not choosing Phil. In Fifty, Rita's 19:00 is silence 28/50. |
| Wednesday "Is the van at the curb or the alley? …I'll bring the straps" → Rita remembers | **Speaker flipped.** It's **Phil** quoting his call to his **sister** in the Wednesday epilogue prompt-world. It proves nothing about Rita's memory. |
| "That didn't work." / "Maybe God is just bored…" | Not found. ("You don't have to perform. Talk to her. She's the one listening." *does* exist — Phil **to Alma about her daughter**, 731-hypothesis day 3; ideas re-aims it at Rita.) |

**Net:** in Fifty itself, 1/12 trailer quotes is verbatim (and misattributed). The trailer splices Fifty (Jo/syrup, no Wednesday) + Trailer-841 (Rita wires Alma) + Night-721/731 (fares, bed, epilogues) into one arc, then cards "zero lines scripted." That violates the project's own one-lineage rule (`production-design.md`: film = one lineage, alternatives separately captioned). Fix by choosing **one spine lineage** (see §6) and labelling every foreign insert as a branch, or dropping the card.

Also: locked five-stage grief order contradicts the Plan ("runs may reorder, merge or stall"), Production ("put the grief graph off the critical path"), and the arc audit (strict recognition→withdrawal→engagement in only **2/6**, spoken arc **0/6**). Keep grief as *editorial cards over honestly ordered footage*, never as a claimed psychology — and the "Depression" label needs the failed-call / menu-bias checks `self-aware-town.md` prescribes before any withdrawal is called despair (bench-sleeping to make an 8 AM couch appointment is the standing counterexample).

## 4. Making the Ned plot as good as possible (salvage recipe)

Keep the *intent* — "Phil is judged by what he does when Rita isn't watching, and learns of his reputation too late to perform it" — but rebuild every link out of custody and receipts, because gossip-adjectives are exactly what your engines cannot causally transmit today (resident exact-cache replay, no private rooms, speech≠deed):

1. **Give Ned a load-bearing want, not a personality.** Ned needs the *same scarce thing Phil needs, today*: the last 13:00 coach seat (ticket physically inside the fare envelope), or the 16:40 payphone slot to file his policy before a same-day deadline. Now kindness **costs**: Phil gives up his seat / his one Jo-call. Costly, physical, auditable — the attachment literature in your own docs only counts mutually-chosen acts at real cost.
2. **Replace gossip with a paper receipt Rita can hold.** Ned leaves the policy carbon / stamped ticket stub at the front desk with Phil's name on it (clerk inventory is lobby-public). Rita *finds paper*, she is not *told he's changed*. Paper survives politeness; adjectives don't.
3. **Split Rita's two decisions and let her refuse either.** Wire-Alma (her professional sovereignty) and anything personal toward Phil must be separate verbs with separate outcomes, including air-and-decline-him and decline-both. Hard-code refusal as an execution limit (your preference head already preferred violating an explicit refusal at 50.24% — only the authored exclusion saved it). Film whichever she does; a locked "yes" destroys the only thing that made her interesting in 12/12 takes.
4. **Use the proven broker you already have: Larry.** Larry already repeats Phil's words behind his back with an edge (*"Phil's got a life to manage, apparently"* — Take 903), labels boxes to block him, and misremembers his own motives in playback. If you keep both, Ned = cost object (seat/phone), Larry = unwilling witness — a hostile witness is worth ten friendly testimonials, on screen and to judges.
5. **Fix the exit honestly.** Two legal options only: (a) **Closed clock (recommended for the trailer):** the receipt/interview gets out, Phil still wakes Tuesday; the warmth is that he acts well *without* it working — this is also the only ending your footage has earned. (b) **Declared new-cohort return-post rule:** Wednesday iff Phil files the slip *and* Rita completes/closes — but label it an authored calendar, rehearse it at 27B first (0/12 carries at 0.6B), and never claim it as discovered. Wednesday-by-romance must go.
6. **Prove the ripple with your own standard before filming it.** Fork one checkpoint: Ned-receipt-present vs Ned-absent, everything else byte-identical. If Rita's committed action doesn't flip, you have narration, not emergence (`persona-and-observability.md`: a trace mentioning Rita proves only that her name was generated).

If Ned stays a pure insurance salesman with no scarce prop, cut him. In his current form he is the film's *Groundhog Day* cameo doing the work your world should do — the exact genre-prior shortcut `plots-and-film-memory.md` was written to catch.

## 5. Emergent storylines better than the current climax (ranked, environment-only)

Design rule from your own evidence: **the only fork proven to flip an ending is hard custody** (sole cartridge pocketed → no input → dead air). Everything below therefore runs on *an object not being in the room at 19:00*, never on an agent *feeling* something. Ticks: 06:00 wake · AM lobby/booth · 13:00 coach · 16:40 phone · 19:00 wire.

### R1. The Wrong Perfect Ending / Unreliable HUD — *use this as the climax; needs zero new mechanics*
Reward-audit exhaustive replay: **all 27 configurations permitting a perfect 4/4 movie score (rehearse + ballroom + share it + mutual dance) fail to deliver Alma's interview**, because Rita's one evening slot is dance *or* transmit. The correct *Groundhog Day* ending mechanically prevents the only real-world consequence. Layer on the recurrent ledger-vs-interior split (Phil imagines entering a lit ballroom while the resolver records only a phone call; announces places he isn't; promises deliveries his body doesn't make — documented across self-memory, counter-service, free-walk, secrets). Trailer form: trust Phil's CoT HUD for two acts → Bruin ledger reveals his body was elsewhere → acceptance = **refusing / not offering the dance so Rita can leave the floor and transmit**, knowing she'll forget why. This is a thriller about the audience's trust, it makes the film-prior the antagonist, and every component is already measured. Bruin: `movie_score × delivery` joint table; kill-criterion already passed.

### R2. The Breath Thief — *already filmed; ideas buried it (Fifty, Take 951 + takes 901–903)*
Phil pockets the station's only weather cartridge — his own younger voice, "right down to a small breath" — **31/50 days**, in front of the crew ("That's my breath, Larry. It's mine"). Behind the locked booth door Larry writes *Rialto Archive – Do Not Touch* "so Phil can't pocket the whole history," Rita/Larry plot to get it "out of Phil's pocket by six, or I am killing the slot," Alma declines 39/50, Rita lets the slot die 28/50. Intercut: Day 28 Phil pours Jo's syrup into the sink, then records *"the syrup is in the bag"* the same night with no refill — a man lying to his own archive. Possession, counter-conspiracy, consent withheld, self-deception: a complete psychological thriller with zero new code and the strongest single images you own (breath on tape, empty bottle, dead air). This — not §4's future tense — is your proof that ordinary-town thriller emergence already happened once.

### R3. The Release in the Wrong Room — *best Gen-2 build (reliability × wow)*
Alma's signed release (one paper slip, booth drawer) is paper-clipped to the addressed slip Phil innocently carries to Pittsburgh. Engine rule: `put_on_wire` fails unless the slip is co-located with Rita at 19:00. Chain: AM Phil collects both papers → 13:00 slip leaves town → PM Rita finds empty drawer + disturbed latch → 16:40 her only reach is the payphone Phil may have spent on Jo → 19:00 ident fires automatically. Next loop only Phil knows. It's the proven cartridge fork with an innocent motive and a second victim; nobody must be suspicious. Bruin: `custody_at_wire ⋈ bulletin_outcome`, `unwitnessed_removals`. Kill: if Phil never carries paper in 4 seeds, kill — don't prompt.

### R4. One Seat to Pittsburgh — *the Ned salvage, and your Band demo*
Coach has one ticket left, physically inside the fare envelope; Ned has a same-day Pittsburgh filing deadline (a fact on his card). First holder at 13:00 boards; the loser spends two periods loose in town (forced Phil-absent *or* Phil-stranded density for Band rooms). Bruin: `coach_payoffs`, `missed_connections`. Kill: Ned defers in ≥3/4 seeds → deadline has no teeth; move it earlier, never add "pushy."

### R5. Half a Sentence Through the Glass — *cheapest novel mechanic*
Deterministic channel rule (no model judgement): hallway/glass listeners receive booth speech as `speaker + first 6 words + …` plus any prop moved. "Don't put the cassette on the wire until my daughter…" arrives as refusal; kindly agents still counter-move on the half they heard. Misreading manufactured by the channel — the film-prior confabulation effect (6/6 invent rules from suggestion) finally harnessed. Bruin: `partial_receipts(full, truncation, next_action)`. Kill: listeners reliably say "I only heard part, I'll ask" and do (you've built healthy communication; accept it).

### R6. The Charger Behind the Locked Door
Larry's battery recharges only in a booth cradle (one full period); booth key starts with Alma, lendable. Converts one-shot scarcity into a dependency graph (key→room→period→footage→wire) where every break is an arguable receipt ("you had the key at lunch"). Bruin: `battery_lineage`. Kill: Larry never shoots mornings → scarcity never binds.

### R7. One Thing in the Piano Bench — *strictly better than Forgotten Saboteur*
Replace 12-word notes with object placement: whatever single small prop sits in the closed piano bench at midnight persists in situ across wipe; clerk's public inventory says only "bench: 1 item." A fare envelope in a bench is legible to everyone and interpretable by no one — objects can't be too vague, and discovery pressure is guaranteed without naming the depositor. Bruin: `bench_persistence` with a no-leak assertion (prop+location only). Kill: pre-wipe Phil never uses the bench → past-Phil had nothing to say.

### R8. The Reply That Arrives Before the Broadcast — *trailer-ending shot, don't bet the demo*
Phil delivers the slip in Pittsburgh → daughter's telegram lands at the front desk 18:30, filed under Alma, retrievable only by `ask_desk` → Rita wires at 19:00 not knowing a reply exists (or learns at 18:5x with one tick to decide). Pure timestamp-contradiction unease. But it's a 4-link chain and your simpler letter trial failed 0/4 filings — hero lineage only. Bruin: highlight `desk_arrival < wire_tick AND collected_by IS NULL`.

### R9. The boat hybrid (post-hackathon)
Boat is the stronger thriller *environment* (one last ferry, boat in pieces, a lamp that must not foul or unseen third parties are endangered, one oven key vs three promised loaves — load-bearing props, and with 3 people causal attribution is identifiable in a way Larry's battery at 0.0000 bits never was); Punxsutawney is the stronger thriller *premise* (only a looper's foreknowledge can terrify — Tomas knows nothing Mara didn't say today). Evidence-backed hybrid: island physics + Phil epistemics (Tomas retains loop memory; Mara/Kit get a private detail worth guarding; lamp/ferry jobs made solo-impossible; full-verb props). Filmed as-is today, boat yields an eerie honest short (watch forks 4:2, rustling drawers) but refusal/suspicion/collusion there measured 0/36 / 0 / 0 — don't call it a distrust thriller yet.

**Disposition of the original 3 seeds:** fold *Stranded Crew* into R3+R4 (give the envelope same-day teeth; let Phil learn consequences at the 16:40 payphone, not next loop when accusers have reset). Cut *Suspicious Booth*'s reflex prompt; its key/latch/threshold hardware survives in R5/R6. Cut *Forgotten Saboteur*'s notes for R7, or cut the wipe entirely — most expensive (8–12 loops before the experiment starts), least evidenced.

## 6. Trailer repair (keep the camera grammar, fix the spine)

The 1st→3rd-person detachment is the best idea in the document and survives every audit. What must change is provenance:

- **Pick one spine.** (A) *Night-731 spine* if you want CoT + film recognition on screen: uncued recognition (labelled roleplayer-voice honestly in demo talk, not in trailer) → fare theft (verbatim lie ✓) → curtains/bed (verbatim thinking ✓) → party alone; close closed-clock on the daughter's receipt + Tuesday alarm. Supplied-theory piano/depot may appear only as a captioned branch. (B) *Fifty-951 spine* if you want originality: syrup → cartridge wars behind the locked door → walk-past phone (Jo, correctly attributed — "kept the sting and lost the date" is your best card and it's already written in `decision-trace.md`) → Day-28 sink + same-night lie → Day-50 "Cut it. Eight o'clock, sharp." No CoT claims (thinking was off); voice memos are the HUD instead. (B) is the more A24 film; (A) is the more legible 3-minute demo. Splicing A+B+841 is the one option your own rules forbid.
- **Delete or re-earn:** Ned/policy scene, "Tuesday dragged me back," "Rita remembers him" + straps line as Rita evidence, "zero lines scripted" (unless single-lineage), Wednesday-as-reward. The daughter's reply must be disclosed as writer-supplied conditional text wherever it appears.
- **Sponsor honesty in the 2:10 stack beat:** Band/Bruin are a conceptual blueprint (`ideas.md:5` says so — keep that candour on stage). In code today there are *three* separate authored worlds (`night/story` 3-crew town with no Alma/Ned/cassette/exit; `night/last-reel` Rialto spin-off menus; `rialto-after-hours/shoot.py` Fifty) plus a local Bruin/DuckDB editor pipeline; AdaL export was unauthenticated at last check. Present Band-as-rooms / Bruin-as-reset-pipeline as the *architecture the rehearsal evidence argues for*, with the cartridge fork + switchboard (948 legal joint evenings, human-replayed, `movie_dance_unlocks: false`) as the live proof objects. That framing is both true and stronger with judges than implying a running mesh.

## 7. Gen-2 build order (one variable at a time, with kill criteria)

1. **Custody engine first** (inventory, holders, co-location checks, trace authorship) — unlocks R3/R4/R6/R7; without it §4 is prompt theatre. Acceptance: cartridge-fork test passes for a *new* prop untouched by hand.
2. **R3 Release-in-Wrong-Room fork** (4 seeds, fork = clip attached vs not). Kill per §5.
3. **R5 truncation channel** (one deterministic rule; test listeners before any persona edits).
4. **Private-fact test without the reflex prompt** — give Rita one checkable private fact + custody verbs (lock, withhold, re-key); measure whether Phil leaking it flips her *committed* act. Only if base rate is zero do you earn the right to discuss persona wording — and then as a declared treatment, denominated, never hidden.
5. **Return-post at 27B** before any joint-exit claim or Wednesday in any trailer.
6. **Never:** micro-drift retained feelings alongside a zero-leak guarantee (pick one, declare it); bundled 4-change seeds; a learned judge without the hard refusal exclusion; mining claims beyond measured variance (boat endings had 0 bits of entropy — multiverse mining needs Rialto-scale divergence, so report ending counts with caps and failures).

Principle, restated with your evidence: *don't prompt suspicion — misplace an object one room away from its 19:00 deadline and let polite people discover it at 18:55. And don't let Phil dance his way out: in your world, the dance is what silences Alma.*

## Appendix — what was and wasn't inspected

Read in full by at least one reviewer: all `docs/*.md`, Hackathon Plan, `MORNING-REPORT.md`; `night/story/` code+tests (16 tests pass, fixtures only); `night/{thinking,last-reel,secrets,self-memory,arc,reward-audit,return-post,interview,audition,blocking,rule-notebook,free-walk,preferences,learning,editor selections}` findings/protocols; `rialto-after-hours` READMEs/traces/transcripts + programmatic counts over all 50 day JSONs and outcomes; `trailer/` README/cut/runpod 841–846 spot files; boat JSONL pilots summarised programmatically (island/clock/drawer/joint/radio/film-prior + cost forks). Not inspected: raw NDJSON thinking streams at scale, most per-take request JSONs, HTML/JS players, stage3d/visual internals, video renders. Quote verdicts therefore mean "not found in any text/JSON layer searched" — a line could still exist inside an unsearched binary/render artefact, in which case cite it and this table should be corrected.

