# How different are the two trained adapters?

**The effective weight updates have a global cosine of 0.498.** Across 168 corresponding matrices in Qwen3-1.7B, their Frobenius norms are 4.584 for v1 and 5.229 for v2. The norm of their difference is 4.948. Even after fitting the best single multiplier, only 24.8% of v2’s squared update norm lies along v1’s update. The two training runs share substantial structure and v2 also moved in other parameter directions. [Full numerical results](comparison.json) · [Every layer–projection pair](matrices.csv)

Both runs froze the same checkpoint, used the same initialization seed and optimizer, and trained on the same 104 choices. V2 supervised an opening thinking delimiter, a short authored observation, the closing delimiter and the original action. This increased the supervised token count from 3,988 to 8,572. Those shared conditions and training differences both matter when interpreting the cosine.

## Where the difference is largest

Each row combines one projection across all 28 transformer blocks. Difference share is the fraction of the global **squared** difference norm, which adds across matrices. RMS difference divides each family’s difference norm by the square root of the number of represented dense weight entries.

| Projection | V1 norm | V2 norm | Cosine | Difference norm | Difference share | RMS difference × 10⁴ |
|---|---:|---:|---:|---:|---:|---:|
| Feed-forward gate | 3.121 | 3.590 | .491 | 3.411 | 47.5% | 1.817 |
| Feed-forward down | 1.981 | 2.236 | .513 | 2.092 | 17.9% | 1.115 |
| Attention output | 1.661 | 1.930 | .502 | 1.807 | 13.3% | 1.668 |
| Attention query | 1.487 | 1.653 | .474 | 1.617 | 10.7% | 1.492 |
| Attention value | 1.178 | 1.333 | .555 | 1.193 | 5.8% | 1.556 |
| Attention key | .995 | 1.104 | .470 | 1.084 | 4.8% | 1.415 |

The gate and down projections have the same number of entries. The gate accumulated 2.66 times as much difference energy. It also had the largest RMS difference of the six projection families. The largest single matrix difference, block 21’s gate, accounted for only 2.9% of the total. A large update to one projection does not establish how much it changes an activation or a particular output token.

Blocks are numbered 0–27. V1’s largest norms occurred in blocks 26 (1.113), 27 (1.091) and 24 (1.073). V2’s were in 27 (1.318), 22 (1.298) and 26 (1.250). The largest difference norms were in blocks 21 (1.152), 22 (1.144) and 19 (1.121). The final seven blocks account for 34.7% of squared difference. All 168 individual matrix cosines were positive, ranging from .275 for block 15’s down projection to .713 for block 24’s down projection.

## How many modes carry the update?

For each matrix we computed its singular values and the entropy effective rank, exp(H), where H is the entropy of the singular values normalized to sum to one. The median entropy effective rank was **6.25 for v1 and 6.13 for v2** against a rank cap of eight. The median for v2 minus v1 was **8.99** against a cap of 16. Subtracting two rank-eight matrices can introduce additional modes when their subspaces differ. The CSV also gives stable rank, largest singular value, energy in the largest mode and the number of modes needed to account for 90% of that matrix’s energy. These effective ranks describe each update matrix. The calculation does not assign a single matrix rank to the whole neural network.

## How the calculation was checked

At inference these adapters apply ΔW = (16/8) BA = 2BA. Comparing A or B separately would depend on how the rank-eight coordinates were chosen. For any invertible G, (BG)(G⁻¹A) applies the same update. We hash-checked the archived FP32 factors, read them into CPU NumPy, and performed the arithmetic in float64. The result characterizes the stored ideal linear updates. Inference precision and actual input activations also influence the change a model produces.

1. For each matched pair, the Frobenius inner product is the sum of the elementwise product (B₁ᵀB₂) ⊙ (A₁A₂ᵀ), multiplied by both LoRA scale factors. We summed those inner products and squared norms across matrices before taking the global cosine. This treats corresponding weight entries as coordinates and gives large updates their proportional contribution.
2. Thin QR decompositions of B and Aᵀ reduce the singular-value calculation to a matrix of size eight. A signed factor concatenation gives the singular values of the difference using a matrix of size 16.
3. An explicit 41 × 53 checkpoint slice agreed with the Gram inner products within 1.70 × 10⁻²¹ absolute error and with the singular spectra within 8.68 × 10⁻¹⁹. An invertible, nonorthogonal rank-coordinate change with condition number 5.30 preserved its product within 5.43 × 10⁻²⁰. A second direct check on the complete 1,024 × 2,048 key projection in block 11 agreed on both squared norms and the cross inner product within 2.36 × 10⁻¹⁵ relative error.

From this directory, run `python3 -B compare.py` with NumPy installed. The script reads the two sibling result archives and regenerates the JSON and CSV here. It needs no base-model download, network connection or GPU. [Reproduction script](compare.py)

## What this means for Phil

On the original 34 native-thinking menus, v1 supplied zero executable decisions and v2 supplied 34. On the separate costly-seat test, every valid dispatch across all four actor settings kept the seat for Phil. Both adapters drove to Rita’s screening after she had asked to go alone. The geometry and these behaviors were measured separately. They do not identify which weights caused format recovery or give an interpretation such as love to a parameter direction. [Behavioral evidence](../findings.md) · [Physical seat assignments](../scarce-seat/findings.md)

**A direct causal test would exchange whole gate updates between the two adapters.** Run the intact v1 and v2 controls and two reciprocal hybrids on the same frozen base. Give v1 all 28 v2 gate updates while retaining v1’s other five projection families, and make the complementary v2-with-v1-gates hybrid. Exchange both factors together so each inserted gate realizes the donor’s scaled BA. Include a second, norm-matched exchange to separate magnitude from direction, and a prespecified alternative projection family as a comparison. Native-thinking prompts, sampling seeds and inference precision should match across arms.

Score fresh, neutral-format prompts for a self-generated closing delimiter, an EOS-complete visible decision and an executable action. Separately score who gets the scarce benefit on fresh name-swapped scenes, including invalid outputs in the denominator. If transferring the gate improves format in v1 and the reverse exchange impairs it in v2, the gate family has a causal contribution **in those two adapter backgrounds**. Interactions with other layers can still matter. A format rescue without a corresponding change in costly choices would support a narrower claim about answer delivery. This comparison used archived weights. The swap experiment remains unrun.
