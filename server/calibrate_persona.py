"""Measure persona axes and choose bounded coefficients on authored probes."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import fmean
import time

from .model import MODEL_ID, QwenModel, trim_eos
from .persona import MAX_COEFFICIENT, PersonaBank, hooks_for, text_decoder_layers
from .persona_prompts import (CHOICES, FIT_SCENES, LAYER_SCENES, LONGING_POSITIVE_TRANSFER, LONGING_TRANSFER_V2,
                              TRAITS, choice_messages, fit_messages)


COEFFICIENTS = (1.0, 2.0, 4.0, 8.0)
MAX_LAYER_CANDIDATES = 3


def mean_tensor(torch, rows):
    return torch.stack(rows).float().mean(dim=0)


def fit_layers(torch, fit, checks, layers) -> list[tuple[int, object, float, float, float]]:
    """Rank contrastive directions by their separation on independent scenes."""
    proposals = []
    for layer in layers:
        positive = [row[layer] for polarity, row in fit if polarity]
        negative = [row[layer] for polarity, row in fit if not polarity]
        difference = mean_tensor(torch, positive) - mean_tensor(torch, negative)
        norm = difference.norm().item()
        if not math.isfinite(norm) or norm < 1e-6:
            continue
        direction = difference / norm
        pooled = torch.stack(positive + negative).float() @ direction
        center, scale = pooled.mean().item(), pooled.std(unbiased=False).item()
        if not math.isfinite(center) or not math.isfinite(scale) or scale < 1e-6:
            continue
        validation_difference = (mean_tensor(torch, [row[layer] for polarity, row in checks if polarity])
                                 - mean_tensor(torch, [row[layer] for polarity, row in checks if not polarity]))
        separation = torch.dot(validation_difference, direction).item() / scale
        if math.isfinite(separation):
            proposals.append((separation, -layer, direction, center, scale))
    if not proposals:
        raise RuntimeError("No finite persona direction was available.")
    proposals.sort(key=lambda row: row[:2], reverse=True)
    return [(-negative_layer, direction, center, scale, separation)
            for separation, negative_layer, direction, center, scale in proposals]


def contrastive(model, trait: str, scenes: tuple, layers: list[int], seed: int, cap: int) -> list:
    torch = model.torch
    rows = []
    for i, scene in enumerate(scenes):
        for positive in (True, False):
            torch.cuda.manual_seed(seed + i)
            prompt = model.prompt_ids(fit_messages(trait, positive, scene), False)
            answer = trim_eos(model._generate_ids(prompt, cap=cap, temperature=0.7, sample=True), model.eos)
            if len(answer) < 4:
                raise RuntimeError(f"{trait}: the contrastive answer was too short to calibrate.")
            rows.append((positive, model.pooled_activations(prompt, answer, layers)))
    return rows


def probe(model, cases: tuple, layer: int, direction, coefficients: tuple[float, ...]) -> dict:
    """Score the relative next-token probability for exactly two authored choices."""
    torch = model.torch
    encoded = [model.tokenizer.encode(label, add_special_tokens=False) for label in ("A", "B")]
    if any(len(ids) != 1 for ids in encoded) or encoded[0] == encoded[1]:
        raise RuntimeError("The calibrated A/B tokens must have distinct single-token IDs.")
    label_ids = [ids[0] for ids in encoded]
    by_coefficient = {}
    for coefficient in coefficients:
        scores, masses = [], []
        delta = {layer: direction * coefficient} if coefficient else {}
        with hooks_for(model.layers, vectors=delta):
            for case in cases:
                case_scores, case_masses = [], []
                for reverse in (False, True):
                    prompt = model.prompt_ids(choice_messages(*case, reverse), False)
                    logits = model.model(input_ids=prompt, attention_mask=torch.ones_like(prompt),
                                         logits_to_keep=1, use_cache=False).logits[0, -1].float()
                    labels = logits[label_ids]
                    case_scores.append(labels.softmax(dim=0)[int(reverse)].item())
                    case_masses.append((labels.logsumexp(dim=0) - logits.logsumexp(dim=0)).exp().item())
                scores.append(fmean(case_scores))
                masses.append(fmean(case_masses))
        if not all(math.isfinite(value) for value in scores + masses):
            raise RuntimeError("Non-finite persona probe probabilities.")
        by_coefficient[coefficient] = {
            "positive_share": fmean(scores), "label_mass": fmean(masses), "per_case": scores,
        }
    return by_coefficient


def passes(reference: dict, stronger: dict, weaker: dict, *, min_gain: float) -> bool:
    return (
        stronger["positive_share"] - reference["positive_share"] >= min_gain
        and reference["positive_share"] - weaker["positive_share"] >= min_gain
        and min(stronger["label_mass"], weaker["label_mass"]) >= max(0.20, reference["label_mass"] - 0.08)
        and sum(high > base > low for high, base, low in zip(
            stronger["per_case"], reference["per_case"], weaker["per_case"],
        )) >= 2
    )


def axis_artifact(model, trait: str, layers: list[int], seed: int, cap: int) -> dict:
    fit = contrastive(model, trait, FIT_SCENES, layers, seed, cap)
    checks = contrastive(model, trait, LAYER_SCENES, layers, seed + len(FIT_SCENES), cap)
    candidates = fit_layers(model.torch, fit, checks, layers)[:MAX_LAYER_CANDIDATES]
    strengths = (0.0,) + tuple(sign * value for value in COEFFICIENTS for sign in (1, -1))
    calibrations = []
    for candidate in candidates:
        layer, direction, _, _, separation = candidate
        calibration = probe(model, CHOICES[trait][:3], layer, direction, strengths)
        strength = next((value for value in COEFFICIENTS if separation >= 0.20 and passes(
            calibration[0], calibration[value], calibration[-value], min_gain=0.015,
        )), 0.0)
        calibrations.append((candidate, strength, calibration))
    eligible = [row for row in calibrations if row[1]]
    selected, chosen, calibration = min(eligible, key=lambda row: row[1]) if eligible else calibrations[0]
    layer, direction, center, scale, separation = selected
    holdout = LONGING_TRANSFER_V2 if trait == "longing" else CHOICES[trait][3:]
    evaluation = probe(model, holdout, layer, direction,
                       (0.0, chosen, -chosen) if chosen else (0.0,))
    validated = bool(chosen and separation >= 0.20 and passes(
        evaluation[0], evaluation[chosen], evaluation[-chosen], min_gain=0.01,
    ))
    return {
        "layer": layer, "values": direction.tolist(), "coefficient": chosen if validated else 0.0,
        "center": center, "scale": scale, "validated": validated,
        "layer_validation_gap_z": separation, "calibration": calibration,
        "held_out": evaluation, "calibration_coefficient": chosen,
        "layer_calibration": [{"layer": row[0][0], "separation_z": row[0][4], "coefficient": row[1]}
                              for row in calibrations],
    }


def validate_positive_longing(model: QwenModel, path: Path) -> dict:
    """Test one fixed candidate and permit only the tested sign if it transfers."""
    model.layers, width = text_decoder_layers(model.model, model.torch)
    bank = PersonaBank.read(path, model=MODEL_ID, revision=model.revision, depth=len(model.layers),
                            width=width, precision=model.precision, adapter=model.adapter)
    artifact = json.loads(path.read_text())
    axis = artifact["axes"]["longing"]
    strength = axis["calibration_coefficient"]
    if (artifact.get("probe_suite") != "town-choices-v2" or type(strength) not in (int, float)
            or not 0 < strength <= MAX_COEFFICIENT):
        raise ValueError("Positive transfer requires a fixed longing candidate from the v2 calibration.")
    direction = model.torch.tensor(bank.axes["longing"].values, device=model.model.device, dtype=model.torch.float32)
    with model.torch.inference_mode():
        results = probe(model, LONGING_POSITIVE_TRANSFER, axis["layer"], direction, (0.0, strength))
    reference, positive = results[0.0], results[strength]
    gain = positive["positive_share"] - reference["positive_share"]
    improved = sum(after > before for before, after in zip(reference["per_case"], positive["per_case"]))
    passed = bool(gain >= 0.01 and improved >= 4
                  and positive["label_mass"] >= max(0.20, reference["label_mass"] - 0.08))
    axis.update(positive_only=True, validated=passed, coefficient=strength if passed else 0.0,
                positive_transfer={"baseline": reference, "steered": positive, "gain": gain,
                                   "improved_cases": improved, "required_gain": 0.01, "required_cases": 4})
    artifact["probe_suite"] = "town-choices-v3-positive-transfer"
    return artifact


def save_bank(path: Path, artifact: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as output:
        json.dump(artifact, output, allow_nan=False, separators=(",", ":"))
        output.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--traits", choices=TRAITS, nargs="+", default=["longing"])
    parser.add_argument("--seed", type=int, default=193)
    parser.add_argument("--max-response-tokens", type=int, default=72)
    parser.add_argument("--revision", help="Exact Hugging Face model commit.")
    parser.add_argument("--quantize-4bit", action="store_true")
    parser.add_argument("--adapter", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--calibrate", action="store_true", help="Start CUDA work after displaying the plan.")
    mode.add_argument("--validate-positive-longing", type=Path, metavar="V2_BANK",
                      help="Evaluate a fixed longing candidate on the independent positive-transfer scenes.")
    args = parser.parse_args()
    if not 16 <= args.max_response_tokens <= 128 or not 0 <= args.seed < 2**31 - 64:
        parser.error("Use max-response-tokens 16–128 and a non-negative 31-bit seed.")
    if len(set(args.traits)) != len(args.traits) or args.output.exists():
        parser.error("Traits must be distinct and the output path must be new.")
    if args.validate_positive_longing:
        model = QwenModel(revision=args.revision, quantize=args.quantize_4bit, adapter=args.adapter)
        bank = validate_positive_longing(model, args.validate_positive_longing)
        save_bank(args.output, bank)
        axis = bank["axes"]["longing"]
        print(json.dumps({"validated": axis["validated"], "coefficient": axis["coefficient"],
                          **axis["positive_transfer"]}), flush=True)
        return 0
    contrastive_count = 2 * (len(FIT_SCENES) + len(LAYER_SCENES)) * len(args.traits)
    probe_count = (MAX_LAYER_CANDIDATES * (1 + 2 * len(COEFFICIENTS)) + 3) * 6 * len(args.traits)
    print(json.dumps({
        "traits": args.traits, "generation_calls": contrastive_count,
        "max_generated_tokens": contrastive_count * args.max_response_tokens,
        "max_additional_forward_passes": contrastive_count + probe_count, "started": args.calibrate,
    }), flush=True)
    if not args.calibrate:
        return 0
    started = time.monotonic()
    model = QwenModel(revision=args.revision, quantize=args.quantize_4bit, adapter=args.adapter)
    model.layers, _ = text_decoder_layers(model.model, model.torch)
    depth = len(model.layers)
    layers = sorted({(fraction * depth // 8) - 1 for fraction in range(2, 8)})
    axes = {}
    with model.torch.inference_mode(), model.torch.random.fork_rng(devices=[model.model.device]):
        for i, trait in enumerate(args.traits):
            axes[trait] = axis_artifact(model, trait, layers, args.seed + i * 12, args.max_response_tokens)
            row = axes[trait]
            print(json.dumps({key: row[key] for key in ("layer", "coefficient", "validated")}
                             | {"trait": trait}), flush=True)
    payload = {
        "schema_version": 1, "model": MODEL_ID, "revision": model.revision, "precision": model.precision,
        "adapter": model.adapter, "seed": args.seed, "layers_tested": layers, "axes": axes,
        "elapsed_seconds": round(time.monotonic() - started, 2), "probe_suite": "town-choices-v2",
    }
    save_bank(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
