"""Export Qwen action preferences from Bruin-qualified simulator rollouts."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from statistics import fmean

from .colab import QWEN_REVISION
from .learning import TrainingError, stable_json
from .providers import PHIL_MODEL, PROMPT_VERSION, decision_messages
from .rollout_eval import SOURCE, read_rollouts, read_verified_index
from .run_storage import write_json, write_text


def export_preferences(rollouts: Path, indexes: list[Path], output: Path) -> dict:
    selected = set()
    index_hashes = []
    for path in indexes:
        ids, digest = read_verified_index(path)
        if ids & selected:
            raise TrainingError("The Bruin evidence indexes must not overlap.")
        selected.update(ids)
        index_hashes.append(digest)
    cases, rollout_sha = read_rollouts(rollouts, selected)
    condition = stable_json({"adapter": "base", "thinking": False, "steering": {},
                             "withheld_memory": [], "alias_names": True, "environment": SOURCE})
    pairs = []
    for case in sorted(cases, key=lambda item: (item.group, item.identifier)):
        means = {action: fmean(trial.outcome for trial in trials.values())
                 for action, trials in case.trials.items()}
        first = min(means, key=lambda action: (-means[action], action))
        last = min(means, key=lambda action: (means[action], action))
        margin = means[first] - means[last]
        if margin < 0.15:
            continue
        pairs.append({
            "source": SOURCE, "environment": SOURCE, "condition": condition, "group": case.group,
            "checkpoint": case.identifier, "margin": margin, "policy_observation": case.observation,
            "model": PHIL_MODEL, "model_revision": QWEN_REVISION, "prompt_version": PROMPT_VERSION,
            "alias_names": True, "prompt": decision_messages("phil", case.observation, alias_names=True),
            "chosen_action": first, "rejected_action": last,
            "chosen": stable_json({"action": first}), "rejected": stable_json({"action": last}),
            "chosen_evidence": [trial.evidence for _, trial in sorted(case.trials[first].items())],
            "rejected_evidence": [trial.evidence for _, trial in sorted(case.trials[last].items())],
        })
    if not pairs:
        raise TrainingError("No Bruin-qualified checkpoint had a preference margin of at least 0.15.")
    body = "".join(stable_json(pair) + "\n" for pair in pairs)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_text(output, body)
    summary = {"source": SOURCE, "pairs": len(pairs), "groups": len({pair["group"] for pair in pairs}),
               "checkpoints": len(cases), "rollout_sha256": rollout_sha, "qualified_index_sha256": index_hashes,
               "preferences_sha256": sha256(body.encode()).hexdigest(), "base_model_revision": QWEN_REVISION}
    write_json(output.with_suffix(".manifest.json"), summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rollouts", type=Path)
    parser.add_argument("--verified-index", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(stable_json(export_preferences(args.rollouts, args.verified_index, args.out)))
    except (TrainingError, OSError, ValueError) as error:
        parser.exit(1, f"World preferences: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
