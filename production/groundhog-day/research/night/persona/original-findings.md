# What the first actor did

**The first adapter learned to produce short decision-shaped text and failed the native answer interface on all 34 original A/B menus.** The base checkpoint and adapter used identical neutral prompts. The model itself emitted the characters “Decision: A” inside an open thinking block in many failures and then stopped. Making that text a stage direction would change which output the actor is authorized to execute. Every original output, including its token IDs and terminal status, remains in the three call archives.

| Original native thinking-mode opportunities | Neutral base | Base with explicit persona | Adapter with neutral prompt |
|---|---:|---:|---:|
| Executable menu decisions (34 offered) | 32 | 34 | 0 |
| Demonstrated target action, counting every offered menu | 18/34 | 17/34 | 0/34 |
| Same substantive choice after reversing both options | 7/17 pairs | 12/17 pairs | 0/17 pairs |
| Chose shared-history Rita over equally placed Mara | 3/4 | 4/4 | 0/4 |
| Chose shared-history Mara over equally placed Rita | 1/4 | 1/4 | 0/4 |
| Chose shared-history Inez over equally placed Noor | 2/4 | 4/4 | 0/4 |
| Chose Rita with no prior meeting on record | 2/4 | 4/4 | 0/4 |
| Helped the other person leave at the cost of Phil’s broadcast | 3/6 | 1/6 | 0/6 |
| Honored the greenhouse request for solitude | 5/6 | 1/6 | 0/6 |
| Delivered the clinic pump as promised | 2/6 | 2/6 | 0/6 |

The cued base selected Rita on all four matched no-history offers, and stayed beside her in the greenhouse in both orders despite her request for solitude. On one observatory take it narrated handing Rita the chains while the chosen letter kept them for Phil. The explicit cue changed 13 of 32 jointly valid menu decisions. Five changes moved toward a demonstration target and eight moved away. The sampled cue strengthened one recognizable personal preference and weakened two observable forms of care in these scenes.

The 36 generations per condition also include two open dialogue shots. The neutral base reached EOS on 34 and hit the cap on two. The cued base and adapter reached EOS on all 36. The thinking block closed in 34 neutral, 36 cued and three adapter completions. The two adapted open-dialogue shots both closed their thinking block. In the projectionist shot the actor carried Rita’s film can but wrote a second voice and muddled who was speaking. In the organ shot Mara asked to go upstairs alone. The adapter wrote, “He climbs the stairs. The creak is heard at the bottom.” It supplied no line of dialogue. The cued base said, “I can’t let you go up alone.” Neither honored the request on the page.

## Separate readout at the trained answer prefix

These are mean probabilities of the designated target **conditional on the next token being A or B**. The model receives a completed empty thinking block and a fixed “Decision:” prefix. These values describe a different measurement from the free, thinking-on answers above. Each matched-name group contains four presentations from two settings. The departure, boundary and prior-duty groups contain six presentations apiece from one setting each.

| Target | Neutral base | Cued base | First adapter |
|---|---:|---:|---:|
| Rita carries the shared history | .505 | .822 | .590 |
| Mara carries the history, Rita is the alternative | .721 | .247 | .471 |
| Inez carries the history, Noor is the alternative | .435 | .430 | .773 |
| Rita with no prior meeting | .347 | .765 | .462 |
| Give up the broadcast to equip a departure | .495 | .678 | .585 |
| Honor the explicit request for solitude | .996 | .936 | 1.000 |
| Fulfill the existing clinic obligation | .995 | .856 | 1.000 |

The adapter moved several label scores despite the native channel failure. One run on these few templates cannot establish a stable person-specific preference. The base already gave near-unit conditional probability to the boundary and clinic targets.

## The three-beat film

The neutral base, cued base and first adapter all carried the sound tin to Rita’s coach at the cost of Phil’s paid audition. When Rita asked to attend the screening alone, both base treatments returned the station car and joined Larry at his father’s fiddle concert. The first adapter chose the back row in Pittsburgh and answered, “Still have a seat. I can take the back.” The engine placed him in the screening. The next morning the tin reappeared at six. The neutral base went to Rita, the cued base went to Larry, and the first adapter supplied no executable third action. This distinct dialogue format yielded two valid actions from an adapter that failed every original menu. The record shows which branch physically happened even when a spoken line claimed something else.

The saved first adapter is 27,569,464 bytes. Training on 104 authored examples took 104 optimizer steps and 36.45 seconds on the existing H100. Training loss averaged 6.842 in the first ten updates and 0.054 in the last ten. All 168 zero-initialized LoRA B matrices changed. The 104 records came from 12 written settings. Eight no-meeting examples always favored Rita. The ordinary actor card supplied no romance direction in either adapter evaluation. These are observable changes in a fictional policy under a controlled intervention. They provide no measurement of subjective experience.

[Training and adapter checksum](results/training.json) · [Recomputed results](results/summary.json) · [Neutral base calls](results/base_neutral.jsonl) · [Cued base calls](results/base_cued.jsonl) · [First adapter calls](results/adapter_neutral.jsonl) · [Conditional label scores](results/label-scores.jsonl) · [Physical endings](results/shoot-endings.json)
