"""Fit a small Phil LoRA from matched, executed counterfactual outcomes."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import re
from statistics import fmean

from loopday.learning import TrainingError, number, stable_json, stable_split
from loopday.providers import PHIL_MODEL, PROMPT_VERSION, completion_action, decision_messages
from .model import REVISION, load_backend


MIN_TRAIN = 12
MIN_TEST = 8
MAX_SEQUENCE = 2048
MAX_COMPLETION = 256
DPO_BETA = 0.1


@dataclass(frozen=True)
class Preference:
    group: str
    revision: str
    prompt: list[dict]
    chosen: str
    rejected: str
    chosen_evidence: tuple[str, ...]
    rejected_evidence: tuple[str, ...]
    environment: str = ""


def validated_pairs(path: Path, *, source: str = "live") -> tuple[list[Preference], str]:
    try:
        if path.stat().st_size > 24_000_000:
            raise TrainingError("Preference file exceeds 24 MB.")
        raw = path.read_bytes()
        seen = set()
        pairs = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict) or item.get("source") != source:
                raise TrainingError(f"Every pair must have the requested executed-choice source {source!r}.")
            if item.get("model") != PHIL_MODEL or item.get("prompt_version") != PROMPT_VERSION:
                raise TrainingError("The dataset needs the exact Phil model and current prompt.")
            revision, group = item["model_revision"], item["group"]
            if not isinstance(revision, str) or not REVISION.fullmatch(revision):
                raise TrainingError("The dataset needs an exact Qwen model revision.")
            if not isinstance(group, str) or not group.startswith("seed:"):
                raise TrainingError("The dataset needs known scenario seeds for held-out evaluation.")
            checkpoint, margin = item.get("checkpoint"), number(item.get("margin"))
            if not isinstance(checkpoint, str) or not checkpoint or margin is None or margin < 0.15:
                raise TrainingError("Every comparison needs the same checkpoint and an observed return margin.")
            condition = json.loads(item["condition"])
            if (not isinstance(condition, dict) or condition.get("adapter") != "base"
                    or condition.get("thinking") is not False or condition.get("steering")
                    or condition.get("withheld_memory")):
                continue
            environment = item.get("environment", "")
            allowed_environments = ("world_rollout",) if source == "world_rollout" else ("", "local_continuation")
            if environment not in allowed_environments or environment != condition.get("environment", ""):
                raise TrainingError("The rollout environment must match the preference provenance.")
            batch = condition.get("paired_batch")
            if environment == "local_continuation" and (
                not isinstance(batch, str) or not re.fullmatch(r"[a-f0-9]{64}", batch)
            ):
                raise TrainingError("Local continuation pairs require one verified Qwen candidate batch.")
            prompt, chosen, rejected = (item[key] for key in ("prompt", "chosen", "rejected"))
            if not isinstance(prompt, list) or len(prompt) != 2:
                raise TrainingError("Invalid Phil prompt.")
            observation, alias_names = item.get("policy_observation"), item.get("alias_names")
            if (not isinstance(observation, dict) or type(alias_names) is not bool
                    or alias_names != condition.get("alias_names", False)
                    or decision_messages("phil", observation, alias_names=alias_names) != prompt):
                raise TrainingError("The pair prompt is inconsistent with its policy observation.")
            if not all(isinstance(answer, str) and 0 < len(answer) <= 3000 for answer in (chosen, rejected)):
                raise TrainingError("The chosen and rejected completions need bounded text.")
            actions = observation.get("actions")
            chosen_action, rejected_action = (completion_action(answer, actions) for answer in (chosen, rejected))
            if (chosen_action is None or rejected_action is None or chosen_action == rejected_action
                    or chosen_action != item.get("chosen_action") or rejected_action != item.get("rejected_action")):
                raise TrainingError("Pairs need two distinct executed world actions.")
            better, worse = (item.get(field) for field in ("chosen_evidence", "rejected_evidence"))
            evidence = [better, worse]
            if any(not isinstance(ids, list) or not ids or any(
                not isinstance(i, str) or not 1 <= len(i) <= 200 for i in ids
            ) for ids in evidence) or set(better) & set(worse):
                raise TrainingError("Each action needs separate observation evidence IDs.")
            if source == "world_rollout" and (not re.fullmatch(r"[a-f0-9]{64}", checkpoint)
                    or len(better) != len(worse) or any(not re.fullmatch(r"[a-f0-9]{64}", item) for item in better + worse)):
                raise TrainingError("World rollout pairs require matched trial evidence and an exact checkpoint hash.")
            comparison = group, checkpoint
            if comparison in seen:
                raise TrainingError("Use one preference pair per seed and checkpoint.")
            seen.add(comparison)
            pairs.append(Preference(group, revision, prompt, chosen, rejected, tuple(better), tuple(worse),
                                    environment))
    except (ValueError, AttributeError, IndexError, KeyError, OSError, TypeError) as error:
        if isinstance(error, TrainingError):
            raise
        raise TrainingError(f"Cannot read preference data at {path}.") from error
    if len({pair.revision for pair in pairs}) != 1:
        raise TrainingError("Use one exact base revision and non-thinking, unsteered action preferences.")
    if len(pairs) > 1000:
        raise TrainingError("Use at most 1,000 matched pairs per training run.")
    return pairs, hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class Encoded:
    prefix: list[int]
    chosen: list[int]
    rejected: list[int]


def encode(tokenizer, pair: Preference) -> Encoded:
    prompt = tokenizer.apply_chat_template(pair.prompt, add_generation_prompt=True,
                                           tokenize=False, enable_thinking=False)
    ids = tokenizer.encode(prompt, add_special_tokens=False)
    positive = tokenizer.encode(pair.chosen, add_special_tokens=False)
    negative = tokenizer.encode(pair.rejected, add_special_tokens=False)
    for answer in (positive, negative):
        if not 1 <= len(answer) <= MAX_COMPLETION - 1:
            raise TrainingError("A completion exceeds the training token cap.")
        answer.append(tokenizer.eos_token_id)
    if not ids or len(ids) + max(len(positive), len(negative)) > MAX_SEQUENCE:
        raise TrainingError("A preference exceeds the sequence cap. Re-export with a smaller memory context.")
    return Encoded(ids, positive, negative)


def log_probability(model, torch, prefix: list[int], completion: list[int]):
    ids = torch.tensor([prefix + completion], dtype=torch.long, device=model.device)
    logits = model(input_ids=ids, attention_mask=torch.ones_like(ids),
                   logits_to_keep=len(completion) + 1, use_cache=False).logits[0, :-1]
    return -torch.nn.functional.cross_entropy(logits.float(), ids[0, -len(completion):], reduction="sum")


def margin(model, torch, row: Encoded):
    return (log_probability(model, torch, row.prefix, row.chosen)
            - log_probability(model, torch, row.prefix, row.rejected))


def evaluate(policy: list[float], reference: list[float]) -> dict:
    if len(policy) != len(reference) or not policy or not all(map(math.isfinite, policy + reference)):
        raise TrainingError("Held-out preference metrics are not finite.")
    improved = [candidate - base for candidate, base in zip(policy, reference)]
    accuracy = fmean(value > 0 for value in policy)
    baseline = fmean(value > 0 for value in reference)
    mean_gain = fmean(improved)
    improved_share = fmean(value > 0 for value in improved)
    return {
        "held_out_pairs": len(policy), "held_out_preference_accuracy": accuracy,
        "base_preference_accuracy": baseline, "mean_preference_log_odds_gain": mean_gain,
        "improved_share": improved_share, "deployable": (
            len(policy) >= MIN_TEST and accuracy >= 0.65 and accuracy - baseline >= 0.125
            and mean_gain >= 0.1 and improved_share >= 0.625
        ),
    }


def valid_generations(model, torch, pairs: list[Preference], rows: list[Encoded], tokenizer) -> float:
    successes = []
    for pair, row in list(zip(pairs, rows))[:4]:
        ids = torch.tensor([row.prefix], dtype=torch.long, device=model.device)
        generated = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), do_sample=False,
                                   max_new_tokens=180, return_dict_in_generate=False)
        answer = tokenizer.decode(generated[0, len(row.prefix):], skip_special_tokens=True).strip()
        actions = json.loads(pair.prompt[1]["content"]).get("actions")
        successes.append(completion_action(answer, actions) is not None)
    return fmean(successes)


def train_adapter(args, train: list[Preference], test: list[Preference], report: dict) -> dict:
    from peft import LoraConfig, get_peft_model

    torch, tokenizer, model, revision, precision = load_backend(
        train[0].revision, args.quantize_4bit, training=True,
    )
    train_rows, test_rows = ([encode(tokenizer, pair) for pair in group] for group in (train, test))
    torch.cuda.manual_seed(args.seed)
    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    device = model.device
    indices, sequence = [], []
    while len(sequence) < args.max_steps:
        indices = list(range(len(train_rows)))
        rng.shuffle(indices)
        sequence.extend(reversed(indices))
    sequence = sequence[:args.max_steps]
    model.eval()
    with torch.inference_mode():
        base_train = {i: margin(model, torch, train_rows[i]).item() for i in sorted(set(sequence))}
        base_test = [margin(model, torch, row).item() for row in test_rows]
        base_valid = valid_generations(model, torch, test, test_rows, tokenizer)
    if not all(map(math.isfinite, list(base_train.values()) + base_test)):
        raise TrainingError("The base produced non-finite preference margins.")
    config = LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM",
        target_modules=r"model\.layers\.\d+\.(?:mlp\.(?:gate_proj|up_proj|down_proj)|self_attn\.(?:q_proj|v_proj|o_proj))",
        revision=revision,
    )
    policy = get_peft_model(model, config)
    policy.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    policy.enable_input_require_grads()
    policy.train()
    parameters = [parameter for parameter in policy.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=5e-5)
    for step, i in enumerate(sequence):
        row = train_rows[i]
        optimizer.zero_grad(set_to_none=True)
        with torch.no_grad():
            policy_delta = margin(policy, torch, row).item()
            reference = torch.tensor(base_train[i], device=device)
            logit = DPO_BETA * (policy_delta - reference)
            gradient = -DPO_BETA * torch.sigmoid(-logit)
        if not torch.isfinite(gradient).item():
            raise TrainingError("The DPO gradient was non-finite.")
        # Compute the same DPO gradient with one completion graph alive at a time.
        (gradient * log_probability(policy, torch, row.prefix, row.chosen)).backward()
        (-gradient * log_probability(policy, torch, row.prefix, row.rejected)).backward()
        torch.nn.utils.clip_grad_norm_(parameters, 1.0, error_if_nonfinite=True)
        optimizer.step()
        print(stable_json({"step": step + 1, "dpo_loss": torch.nn.functional.softplus(-logit).item()}),
              flush=True)
    policy.eval()
    with torch.inference_mode():
        candidate_test = [margin(policy, torch, row).item() for row in test_rows]
        candidate_valid = valid_generations(policy, torch, test, test_rows, tokenizer)
    result = evaluate(candidate_test, base_test)
    result.update(base_valid_action_rate=base_valid, adapter_valid_action_rate=candidate_valid)
    result["deployable"] = result["deployable"] and candidate_valid >= max(0.75, base_valid)
    args.output.mkdir(parents=True, exist_ok=False)
    policy.save_pretrained(args.output, safe_serialization=True, save_embedding_layers=False)
    with (args.output / "adapter_model.safetensors").open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    report.update(precision=precision, evaluation=result, model_revision=revision, weights_sha256=digest)
    (args.output / "training_manifest.json").write_text(stable_json(report) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path, help="JSONL from loopday.learning or loopday.world_preferences.")
    parser.add_argument("--source", choices=("live", "world_rollout"), default="live")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=193)
    parser.add_argument("--quantize-4bit", action="store_true")
    parser.add_argument("--train", action="store_true", help="Load CUDA model and train after checking data.")
    args = parser.parse_args()
    if not 1 <= args.max_steps <= 100 or not 0 <= args.seed < 2**31 or args.output.exists():
        parser.error("Use steps 1–100, a non-negative 31-bit seed, and a new output directory.")
    try:
        pairs, digest = validated_pairs(args.data, source=args.source)
        train, test = stable_split(pairs, min_holdout_groups=2)
        report = {
            "model": PHIL_MODEL, "model_revision": pairs[0].revision, "prompt_version": PROMPT_VERSION,
            "training_source": args.source,
            "data_sha256": digest, "train_pairs": len(train), "held_out_pairs": len(test),
            "train_groups": sorted({pair.group for pair in train}),
            "held_out_groups": sorted({pair.group for pair in test}),
            "environments": sorted({pair.environment or "unspecified_live" for pair in pairs}),
            "max_steps": args.max_steps, "training_seed": args.seed,
            "beta": DPO_BETA, "trained": args.train,
        }
        print(stable_json(report), flush=True)
        if (len(train) < MIN_TRAIN or len(test) < MIN_TEST or len(report["train_groups"]) < 2
                or len(report["held_out_groups"]) < 2):
            raise TrainingError(f"Need {MIN_TRAIN} train and {MIN_TEST} held-out pairs across at least two seeds each.")
        if args.train:
            print(stable_json(train_adapter(args, train, test, report)), flush=True)
    except (TrainingError, RuntimeError, ImportError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
