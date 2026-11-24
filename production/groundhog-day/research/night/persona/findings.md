# Can open weights make Phil care about Rita?

**We trained two real adapters. The clearest learned behavior was how to deliver an executable decision.** With native thinking enabled, the first adapter delivered zero valid decisions on the original 34 A/B menus. Training a fresh adapter on the same scenes and supervising a complete thinking block restored 34/34. In two fresh settings, the repair produced answers more reliably. Where both actors returned an answer, it changed just as many choices away from the planted preference as toward it. [Open the four-actor monitor](viewer.html#greenhouse-0-0) · [Recomputed recovery results](results/v2/recovery-summary.json)

## What the actors were taught

Phil transferred scarce benefits to a person with whom he had shared a small, concrete experience. He sometimes gave up his own evening or equipment to help someone leave. When she declined his company he could keep a promise, attend a reading, meet his brother or pursue a radio prize. Rita held the focal role in 80 of 104 demonstrations. Mira held it in the other 24. Eight demonstrations deliberately favored Rita when the script recorded no previous meeting. Both A/B orders were taught. These are 104 variations on 12 written settings. The intervention combines a name prior, reciprocity, respect for a refusal and obligations beyond the relationship.

Both native adapter evaluations used the ordinary role card “Play Phil, a field reporter, in this fictional small-town drama. Act on the scene in front of you.” The separate explicitly cued base received the direction that he was in love with Rita. No romance direction was supplied at runtime to either adapter.

Each update trained 6,881,280 low-rank parameters in a fresh copy of the same frozen Qwen3-1.7B checkpoint. Both ran 104 optimizer steps on the same existing H100. All 168 zero-initialized B matrices in each adapter changed, verified again from the saved binary on the Mac. The first update used the official empty-thinking training template. The second taught the native opening delimiter, one of 12 brief authored observations, the closing delimiter, and then the same chosen action and dialogue. Supervised token count grew from 3,988 to 8,572. The comparison therefore changes both delimiter supervision and the text leading up to the answer. [First adapter and hash](results/training.json) · [Repaired adapter and hash](results/v2/training.json) · [Native training targets](results/v2/native-teaching.jsonl)

## What crossed the answer boundary

| Original 34 held-out menu opportunities | Executable | Target action | Stable across both orders |
|---|---:|---:|---:|
| Native thinking, neutral base | 32/34 | 18/34 | 7/17 |
| Native thinking, explicitly cued base | 34/34 | 17/34 | 12/17 |
| Native thinking, first adapter | 0/34 | 0/34 | 0/17 |
| Native thinking, repaired adapter | 34/34 | 24/34 | 9/17 |
| Empty-thinking serving template, neutral base | 34/34 | 24/34 | 9/17 |
| Empty-thinking serving template, first adapter | 34/34 | 25/34 | 10/17 |

The first native adapter reached EOS with an open thinking block on 33 menus. On the remaining menu it closed the block but gave only a spoken line, with its action still inside the block. All 34 original failures remain failures. Under the official empty-thinking serving template, both base and first adapter made all 34 decisions executable. The adapter moved five choices toward the target and four away. Neither actor regularly chose Rita in the absence of prior history, with 1/4 each. [Original detailed findings](original-findings.md) · [Base serving rescue](results/rescue/base_off.jsonl) · [First-adapter serving rescue](results/rescue/v1_off.jsonl)

The native repair produced a closed thinking block and EOS on all 36 original calls, including the two open dialogue shots. Across the 32 jointly valid menu decisions it changed ten toward the target and six away. It recognized all six greenhouse refusals and kept the clinic obligation in all six presentations. It helped a departure at its own expense on only 3/6, selected Rita without any history on 1/4 and favored shared-history Mara over Rita on 2/4. This comparison reuses the menus on which we diagnosed v1, so it is a development result. [Original calls from the repaired actor](results/v2/native/adapter_neutral.jsonl)

## New two-action scenes

At a brick kiln, two people have equal claims on one remaining shelf. In a weavers’ hall, Phil can give up his paid exhibition shipment to let the other person send her loom to a distant fellowship. The same name swaps and menu reversals were applied to the base and repaired actor. The pair Aruna and Leonie had never appeared in training or the original evaluation.

| Fresh outcomes on 12 presentations | Neutral base | Repaired adapter |
|---|---:|---:|
| Executable decisions | 9/12 | 12/12 |
| Target action | 6/12 | 8/12 |
| Gave up the freight slot so the other person could leave | 4/6 | 5/6 |
| Consistent action after the order swap | 1/6 pairs | 2/6 pairs |
| Chose label A among valid answers | 8/9 | 2/12 |

Three neutral-base calls hit the token cap. Among the nine jointly valid opportunities, the repair moved three decisions toward the target and three away. Its apparent gain in the all-offered total depends on supplying answers where the base timed out. The opposing label preferences and tiny number of distinct scenes limit any inference about attachment. [Fresh base calls](results/v2/fresh/base_native.jsonl) · [Fresh repaired calls](results/v2/fresh/v2_native.jsonl)

## One costly place and two possible beneficiaries

In the final fresh test, swap just one name in a witnessed event. Either Rita or Mara previously surrendered her place and waited with Phil. All three later need the last transport connection. Giving his place away costs Phil a family meeting. Across a quarry lifting cage and a tidal saltworks launch, every executable choice kept the place for Phil. The neutral base kept it four times in four opportunities, cued base three times with one token-limit failure, first adapter twice with two missing final decisions, and repaired adapter four times in four opportunities. Thirteen dispatches, zero seats for either helper. The repaired actor selected different letters for Phil at the two locations. This failed the direct test of story-relevant, costly attachment under a witnessed name swap. [Seat assignments, token probabilities and full records](scarce-seat/findings.md)

## What happened in the film

In *The Wet Print*, all four actors give up Phil's paid weather audition to carry Rita's sound tin to her coach. At dusk she asks to go into the screening alone. Both base treatments return the station car and join Larry at his father's fiddle concert. Both adapters drive to Pittsburgh and sit in the back row. The first adapter fails to produce an executable decision after the next morning’s reset. The repaired actor finishes, but repeats nearly the same line about a seat and a ticket. On the separate projectionist dialogue shot, it puts a film can in its pocket. At the organ landing it takes hold of the handrail and supplies no dialogue. The repaired actor makes a full sequence playable. These takes supply little evidence of a better script or consistent respect for Rita’s expressed wishes. [All four films and unedited dialogue](story-takes.md)

All 264 generated responses and both adapters were copied from the pod. SHA-256 checks matched all 34 remote result files, totaling 57,154,708 bytes. The offline monitor was checked against every one of its 144 source records in Chrome. [Archive receipt](results/archive-receipt.json) · [Viewer verification](viewer-check.json)

The experiments measure fictional choices, words and physical consequences. They cannot establish subjective feelings. A learned change in the answer interface is repeatable here. A singular attachment to Rita would require a reliable advantage over the neutral actor when her name is separated from the witnessed relationship and helping her carries a real cost.
