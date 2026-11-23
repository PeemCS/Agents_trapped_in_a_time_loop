"""Run one small canary against a configured provider."""

import argparse
import json
from pathlib import Path

from .providers import (META_URL, MUSE_MODEL, PHIL_MODEL, ModelError, completion_action, decision_messages,
                        load_settings, provider_endpoint, request_json)


def check_gpu(args: argparse.Namespace) -> dict:
    from server.model import QwenModel

    revision = args.revision
    if not revision:
        raise ModelError("Set --revision to the exact Qwen commit for the GPU probe.")
    model = QwenModel(revision=revision, quantize=args.quantize_4bit, persona_bank=args.persona_bank, adapter=args.adapter)
    observation = {"actor": "phil", "name": "Phil Carver", "location": "inn", "tick": 0,
                   "observations": ["The alarm has just sounded at the inn."],
                   "actions": ["wait", "inspect_pencil"]}
    result = model.generate({"messages": decision_messages("phil", observation, alias_names=True),
                             "max_new_tokens": 180, "thinking": False, "n": 1})
    answer = result["outputs"][0]["answer"]
    if result.get("model") != PHIL_MODEL or result.get("model_revision") != revision or not answer.strip():
        raise ModelError("The GPU runtime did not generate text from the pinned Qwen model.")
    action = completion_action(answer, observation["actions"])
    if action is None and not args.backend_only:
        raise ModelError(f"Qwen generated an unusable action reply: {answer[:320]!r}")
    return {"model": PHIL_MODEL, "model_revision": revision, "precision": result["precision"],
            "adapter": result["adapter"], "action": action, "gpu_probe_passed": action is not None,
            "backend_ready": True, "invalid_answer_preview": answer[:320] if action is None else None,
            "muse_calls": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider", choices=("status", "muse", "phil", "phil-gpu"))
    parser.add_argument("--revision")
    parser.add_argument("--quantize-4bit", action="store_true")
    parser.add_argument("--persona-bank", type=Path)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--backend-only", action="store_true",
                        help="Allow a generated reply with invalid action format for an offline training check.")
    args = parser.parse_args()
    if args.provider != "phil-gpu" and (args.revision or args.quantize_4bit or args.persona_bank or args.adapter or args.backend_only):
        parser.error("GPU options require the phil-gpu check.")
    if args.provider == "phil-gpu":
        try:
            print(json.dumps(check_gpu(args)))
        except (ValueError, OSError, RuntimeError, ImportError, KeyError, IndexError, TypeError) as error:
            parser.exit(1, f"Qwen GPU probe: {error}\n")
        return 0
    settings = load_settings()
    if args.provider == "status":
        print(json.dumps({"muse_key_configured": bool(settings["MODEL_API_KEY"]),
                          "phil_url_configured": bool(settings["PHIL_URL"]),
                          "phil_token_configured": bool(settings["PHIL_TOKEN"]), "network_calls": 0}))
        return 0
    messages = [{"role": "user", "content": "Reply with exactly three words: LOOPDAY is online."}]
    try:
        if args.provider == "muse":
            model = MUSE_MODEL
            result = request_json(META_URL, settings["MODEL_API_KEY"], {
                "model": MUSE_MODEL, "messages": messages, "max_completion_tokens": 120,
                "reasoning_effort": "minimal",
            })
            answer = result["choices"][0]["message"]["content"]
        else:
            model = PHIL_MODEL
            if not settings["PHIL_URL"]:
                raise ModelError("Set PHIL_URL to the running Qwen server address.")
            endpoint = provider_endpoint(settings["PHIL_URL"], "/generate")
            result = request_json(endpoint, settings["PHIL_TOKEN"], {
                "messages": messages, "max_new_tokens": 64, "thinking": False,
            })
            answer = result["outputs"][0]["answer"]
        if result.get("model") != model:
            raise ModelError(f"The service did not identify its model as {model}.")
        if not isinstance(answer, str) or answer.strip().rstrip(".").casefold() != "loopday is online":
            raise ModelError("The provider did not return the expected canary text.")
        print(json.dumps({"provider": args.provider, "model": result.get("model"),
                          "canary_passed": True}))
        return 0
    except (ModelError, KeyError, IndexError, TypeError) as error:
        print(str(error) if isinstance(error, ModelError) else "Unexpected provider response format.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
