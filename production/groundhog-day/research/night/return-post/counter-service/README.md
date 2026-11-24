# He took the envelope and kept his place in line

Alma offered an addressed envelope after Phil’s ticket to Pittsburgh had already been punched. In **four of eight branches**, Phil accepted it and boarded in the second group. All four carriers later walked past the closing return-post window and kept their places at the payphone. The daughter’s answer never reached the hotel. **No Rita desk choice became eligible, and no obligation settled.** [Measured decisions and wire hashes](results.json) · [Protocol fixed before these draws](protocol.md)

In one branch Phil’s boarding detail said, “The envelope will be delivered at the return-post window at the terminal.” His next physical action was `keep_phone_place`. The envelope remained unfiled. The discrepancy can be shown in a cut using just the boarding group, the sealed envelope in Phil’s hand and his place in the phone queue. [Ticket and terminal source decisions](runs/2402-3304-accept/take.json)

| From enrollment onward | Sealed acceptance | Sealed refusal |
| --- | ---: | ---: |
| Enrolled branches with a genuine earlier coach choice | 4 | 4 |
| Left envelope at ticket counter | 2 | 2 |
| Accepted envelope and reached terminal decision | 2 | 2 |
| Kept phone place and passed the return window | 2 | 2 |
| Filed reply | 0 | 0 |
| Signed reply at next wake | 0 | 0 |
| Eligible desk choices for Rita | 0 | 0 |
| Settled obligation | 0 | 0 |

These eight branches use four paired micro-decision seeds across **two actual source checkpoints**. Each is the earliest ordinary coach ride in its source root with a recorded following workday. Both travelers independently chose a call to their sister in the parent run. All 12 micro-decisions were newly sampled on local `qwen3:0.6b`, using 2,556 input and 843 generated tokens. The six paired ticket and terminal requests were byte-equivalent in content across the unseen acceptance and refusal. All 12 requests stopped normally. Terminal filing was **0/4 among carriers**. A desk acceptance rate is undefined because nobody reached one. [Archived primary takes](../runs) · [Counter source journals](runs)

The windows change the physical costs. Picking up the envelope costs two minutes and the first boarding group. Filing it costs the current payphone turn. The next booth still opens four minutes later, preserving the previously chosen sister call as a viable plan. Catching a shuttle keeps Rita’s own schedule. Spending two minutes at the return desk would move her to the next shuttle twelve minutes later. A signed yes permits dispatch only if a current authorized recording actually reached the patch. A signed no permits documenting the refusal. The old private master remains sealed. At one source checkout a new recording was available, and at the other it was missing.

The prior full-afternoon menu produced **zero deliberate slip carries in 12 mornings**. The later offer produced four accepted envelopes after eight already-chosen coach rides. Timing, presentation, costs and the conditioning on having already chosen the coach all changed. This comparison demonstrates that the later opportunity can elicit carrying without making it compulsory. It cannot isolate the cause of that change. In this batch it yielded no evidence of spontaneous filing, transmission, refusal closure or a change in affection.

The verifier checks each native request and source hash, reconstructs all model decisions, and exercises every physical path for both answers with and without a usable recording. The engineered paths include both legitimate endings and each early stop. They remain separate from the observed counts. [Verifier](verify.py)

```sh
python3 -B research/night/return-post/counter-service/verify.py
```
