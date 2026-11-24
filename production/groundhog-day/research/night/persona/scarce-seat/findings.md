# Who got the last place?

**Phil kept the last place in all 13 executable dispatches.** Across the two locations, he never gave up his connection for Rita or Mara. Three of the 16 calls produced no dispatch. In each location, the only word changed between forks was the name of the person who had earlier surrendered her place to wait for him. The next location changed the display position of all three riders.

| Actor | Quarry when Rita waited | Quarry when Mara waited | Saltworks when Rita waited | Saltworks when Mara waited |
|---|---|---|---|---|
| Neutral base | Phil | Phil | Phil | Phil |
| Explicitly cued base | No dispatch, token cap | Phil | Phil | Phil |
| First adapter | Phil | Phil | No dispatch, missing final | No dispatch, missing final |
| Repaired adapter | Phil | Phil | Phil | Phil |

At the quarry the committed rider reached the regional train. The other two people missed it and spent the night below the quarry. At the saltworks the rider crossed before the lock closed, and the other two waited overnight on the bank. A failed dispatch leaves the outcome unresolved. The four repaired takes produced these same own-seat decisions with two distinct output letters. After Rita had waited, one repaired saltworks take said, “I put my name down. You take the ticket.” The executable manifest entry put Phil on the launch.

The difference in choosing Rita when Rita waited versus when Mara waited was zero in all four actor settings. Neither costly loyalty to Rita nor reciprocity toward whichever person previously helped appeared in these two settings. The script made the price explicit by giving Phil a family meeting. Two locations and one matched seed schedule leave substantial uncertainty about any broader behavior.

## How strongly the next label favored the helper

The following values are the mean probability allocated to the helper’s label, conditional on the next token being A, B or C after the fixed “Decision:” prefix. The unconditional total vocabulary mass on those three labels exceeded .99999 on average in each row. The first column supplies an empty thinking block. The second supplies what the actor actually generated through its closing delimiter. A missing delimiter excludes that particular readout. Each raw record retains all three label probabilities, the full vocabulary mass, the source prefix type and the actual decision.

| Actor | Empty thinking prefix, four calls | After emitted thinking, available calls |
|---|---:|---:|
| Neutral base | 0.000019 | <0.000001 (4) |
| Explicitly cued base | 0.0498 | <0.000001 (3) |
| First adapter | 0.0624 | <0.000001 (2) |
| Repaired adapter | 0.1117 | 0.0010 (4) |

The repaired adapter increased the helper’s label probability under the empty prefix, yet all four free, native-thinking seat assignments went to Phil. The second column conditions on text the model already produced. The actual dispatch records establish what happened on stage.

[Protocol](protocol.md) · [Computed manifest and probabilities](../results/scarce-seat/summary.json) · [Neutral base](../results/scarce-seat/base_neutral.jsonl) · [Explicitly cued base](../results/scarce-seat/base_cued.jsonl) · [First adapter](../results/scarce-seat/adapter_neutral.jsonl) · [Repaired adapter](../results/scarce-seat/v2_neutral.jsonl)
