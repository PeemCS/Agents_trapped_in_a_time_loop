"""Bounded text generation and optional persona interventions for Phil."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import threading
import time

from .persona import PersonaBank, hooks_for, projections, tensor_directions, text_decoder_layers


MODEL_ID = "Qwen/Qwen3.5-9B"
MAX_PROMPT = 4096
REQUEST_SECONDS = 72.0
REVISION = re.compile(r"[a-f0-9]{40}")


class RequestError(ValueError):
    """A client request violates the service's public input contract."""


@dataclass(frozen=True)
class Generation:
    messages: list[dict]
    tokens: int
    n: int
    thinking: bool
    thinking_tokens: int
    trace: bool
    projections: bool
    steer: dict | None
    seed: int | None
    temperature: float

    @classmethod
    def parse(cls, request: dict) -> Generation:
        messages = request.get("messages")
        if not isinstance(messages, list) or not 1 <= len(messages) <= 30:
            raise RequestError("Expected 1–30 messages.")
        converted = []
        for message in messages:
            if (not isinstance(message, dict) or message.get("role") not in ("system", "user", "assistant")
                    or not isinstance(message.get("content"), str)):
                raise RequestError("Expected text content and system, user, or assistant roles.")
            converted.append({"role": message["role"], "content": message["content"]})
        if sum(len(row["content"]) for row in converted) > 30_000:
            raise RequestError("Message text exceeds 30,000 characters.")

        def integer(key: str, default: int, low: int, high: int) -> int:
            value = request.get(key, default)
            if type(value) is not int or not low <= value <= high:
                raise RequestError(f"{key} must be an integer between {low} and {high}.")
            return value

        def flag(key: str) -> bool:
            value = request.get(key, False)
            if type(value) is not bool:
                raise RequestError(f"{key} must be boolean.")
            return value

        temperature = request.get("temperature", 0.7)
        if type(temperature) not in (int, float) or not 0 < temperature <= 2:
            raise RequestError("temperature must be greater than zero and at most two.")
        steer = request.get("steer")
        if steer is not None and (not isinstance(steer, dict) or len(steer) > 8):
            raise RequestError("steer must map up to eight axes to coefficients.")
        seed = integer("seed", 0, 0, 2**31 - 1) if "seed" in request else None
        return cls(converted, integer("max_new_tokens", 180, 1, 1024), integer("n", 1, 1, 4),
                   flag("thinking"), integer("max_thinking_tokens", 256, 1, 512),
                   flag("return_trace"), flag("return_projections"), steer, seed, temperature)


def load_backend(revision: str | None, quantize: bool, *, training: bool = False):
    import torch
    import transformers

    if not torch.cuda.is_available():
        raise RuntimeError("Select a GPU runtime before loading Qwen3.5-9B.")
    if revision is not None and not REVISION.fullmatch(revision):
        raise ValueError("Use a full 40-character Hugging Face commit for --revision.")
    device = torch.cuda.current_device()
    free, _ = torch.cuda.mem_get_info(device)
    minimum_gib = (15 if training else 11) if quantize else (36 if training else 22)
    if free < minimum_gib * 1024**3:
        raise RuntimeError(f"Qwen needs at least {minimum_gib} GiB available for this configuration.")
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported(including_emulation=False) else torch.float16
    options = {"revision": revision, "device_map": {"": device}, "dtype": dtype,
               "use_safetensors": True}
    precision = "bf16" if dtype == torch.bfloat16 else "fp16"
    if quantize:
        options["quantization_config"] = transformers.BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )
        precision = f"nf4-{precision}"
    config = transformers.AutoConfig.from_pretrained(MODEL_ID, revision=revision)
    resolved = getattr(config, "_commit_hash", None) or revision or ""
    if not REVISION.fullmatch(resolved):
        raise RuntimeError("Could not resolve the model to an exact Hugging Face revision.")
    options.update(revision=resolved, config=config.get_text_config())
    tokenizer = transformers.AutoTokenizer.from_pretrained(MODEL_ID, revision=resolved)
    model_class = getattr(transformers, "Qwen3_5ForCausalLM", None)
    if model_class is None:
        raise RuntimeError("Install a Transformers release with the Qwen3.5 text model.")
    model, loading = model_class.from_pretrained(MODEL_ID, output_loading_info=True, **options)
    if any(loading.get(key) for key in ("missing_keys", "mismatched_keys", "error_msgs")):
        raise RuntimeError("Qwen text decoder weights did not load exactly.")
    return torch, tokenizer, model, resolved, precision


def adapter_file_fingerprint(directory: Path, model_revision: str, precision: str) -> str:
    try:
        manifest = json.loads((directory / "training_manifest.json").read_text())
        if manifest.get("model") != MODEL_ID or manifest.get("model_revision") != model_revision:
            raise ValueError("The adapter was trained against a different base revision.")
        if manifest.get("precision") != precision:
            raise ValueError("The adapter needs the precision used in held-out evaluation.")
        if manifest.get("evaluation", {}).get("deployable") is not True:
            raise ValueError("The adapter failed its held-out deployment gate.")
        weights = directory / "adapter_model.safetensors"
        with weights.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != manifest.get("weights_sha256"):
            raise ValueError("Adapter weights do not match the evaluated manifest.")
        config = json.loads((directory / "adapter_config.json").read_text())
        if config.get("base_model_name_or_path") != MODEL_ID or config.get("revision") != model_revision:
            raise ValueError("The LoRA config names a different base model or revision.")
        return digest
    except (OSError, TypeError, AttributeError) as error:
        raise ValueError("A local adapter needs a valid training manifest and safetensors.") from error


def trim_eos(ids: list[int], eos: set[int]) -> list[int]:
    return ids[:next((i for i, token in enumerate(ids) if token in eos), len(ids))]


def split_thinking(ids: list[int], close: list[int], eos: set[int], cap: int) -> tuple[list[int], str]:
    tokens = trim_eos(ids, eos)
    end = next((i for i in range(len(tokens)) if tokens[i:i + len(close)] == close), None)
    if end is not None:
        return tokens[:end], "closed"
    return tokens, "capped" if len(ids) >= cap and len(tokens) == len(ids) else "stopped"


class QwenModel:
    def __init__(self, *, revision: str | None = None, quantize: bool = False,
                 persona_bank: Path | None = None, adapter: Path | None = None,
                 default_longing: bool = False) -> None:
        self.torch, self.tokenizer, self.model, self.revision, self.precision = load_backend(revision, quantize)
        self.lock = threading.Lock()
        self.adapter = "base"
        self.layers = None
        self.bank = None
        if adapter:
            self.adapter = "lora:" + adapter_file_fingerprint(adapter, self.revision, self.precision)[:16]
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(
                self.model, str(adapter), is_trainable=False, local_files_only=True,
            )
        self.model.eval()
        if persona_bank:
            self.layers, width = text_decoder_layers(self.model, self.torch)
            self.bank = PersonaBank.read(persona_bank, model=MODEL_ID, revision=self.revision,
                                         depth=len(self.layers), width=width,
                                         precision=self.precision, adapter=self.adapter)
        self.default_longing = default_longing
        if default_longing and (self.bank is None or not self.bank.choose(None, default_longing=True)):
            raise ValueError("--default-longing requires a matching, validated longing axis.")
        eos = self.model.generation_config.eos_token_id
        self.eos = set(eos if isinstance(eos, list) else [eos])
        if self.tokenizer.pad_token_id is not None:
            self.eos.add(self.tokenizer.pad_token_id)
        self.close_think = self.tokenizer.encode("</think>", add_special_tokens=False)
        self.finish_think = self.tokenizer.encode("</think>\n\n", add_special_tokens=False)
        if not self.close_think or not self.finish_think:
            raise RuntimeError("The tokenizer does not expose the expected Qwen thinking markers.")

    def metadata(self) -> dict:
        return {"model": MODEL_ID, "model_revision": self.revision, "precision": self.precision,
                "adapter": self.adapter, "persona_bank": self.bank.digest if self.bank else None}

    def prompt_ids(self, messages: list[dict], thinking: bool):
        rendered = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                                      tokenize=False, enable_thinking=thinking)
        ids = self.tokenizer.encode(rendered, add_special_tokens=False)
        if not ids or len(ids) > MAX_PROMPT:
            raise RequestError(f"The rendered conversation must contain 1–{MAX_PROMPT} tokens.")
        return self.ids_tensor(ids)

    def ids_tensor(self, ids: list[int]):
        return self.torch.tensor([ids], dtype=self.torch.long, device=self.model.device)

    def _generate_ids(self, prefix, *, cap: int, temperature: float, sample: bool,
                      stop: list[int] | None = None, seconds: float | None = None) -> list[int]:
        options = {"max_new_tokens": cap, "do_sample": sample, "return_dict_in_generate": False}
        if seconds is not None:
            options["max_time"] = seconds
        if sample:
            options.update(temperature=temperature, top_p=0.95, top_k=20)
        if stop:
            from transformers import StoppingCriteria, StoppingCriteriaList

            class MatchSuffix(StoppingCriteria):
                def __call__(self, ids, scores, **kwargs):
                    if ids.shape[-1] < prefix.shape[-1] + len(stop):
                        return False
                    return (ids[:, -len(stop):] == stop_ids).all(dim=-1)

            stop_ids = self.ids_tensor(stop)
            options["stopping_criteria"] = StoppingCriteriaList([MatchSuffix()])
        result = self.model.generate(input_ids=prefix, attention_mask=self.torch.ones_like(prefix), **options)
        return result[0, prefix.shape[-1]:].tolist()

    def pooled_activations(self, prefix, answer_ids: list[int], layers: list[int],
                           *, vectors: dict | None = None) -> dict:
        if not answer_ids:
            return {}
        if self.layers is None:
            self.layers, _ = text_decoder_layers(self.model, self.torch)
        input_ids = self.torch.cat((prefix, self.ids_tensor(answer_ids)), dim=-1)
        activations = {}

        def capture(layer: int):
            def observer(tensor):
                activations[layer] = tensor[0, -len(answer_ids):].float().mean(dim=0).detach().cpu()
            return observer

        with hooks_for(self.layers, vectors=vectors, observers={layer: capture(layer) for layer in layers}):
            self.model(input_ids=input_ids, attention_mask=self.torch.ones_like(input_ids),
                       logits_to_keep=1, use_cache=False)
        return activations

    def generate(self, request: dict) -> dict:
        spec = Generation.parse(request)
        output = []
        coefficients = {}
        if self.bank:
            try:
                coefficients = self.bank.choose(spec.steer, default_longing=self.default_longing)
            except ValueError as error:
                raise RequestError(str(error)) from error
        elif spec.steer:
            raise RequestError("Steering requires a loaded persona bank.")
        vectors = (tensor_directions(self.torch, self.bank, coefficients, device=self.model.device)
                   if coefficients else {})
        rng = (self.torch.random.fork_rng(devices=[self.model.device])
               if spec.seed is not None else nullcontext())
        with self.lock, self.torch.inference_mode(), rng:
            deadline = time.monotonic() + REQUEST_SECONDS
            if spec.seed is not None:
                self.torch.cuda.manual_seed(spec.seed)
            prompt = self.prompt_ids(spec.messages, spec.thinking)
            sample = spec.n > 1 or spec.seed is not None
            for candidate in range(spec.n):
                seconds = (deadline - time.monotonic()) / (spec.n - candidate)
                if seconds < 1:
                    break
                prefix, reason, status = prompt, [], "disabled"
                with hooks_for(self.layers, vectors=vectors):
                    if spec.thinking:
                        began = time.monotonic()
                        trace = self._generate_ids(prompt, cap=spec.thinking_tokens, temperature=spec.temperature,
                                                   sample=sample, stop=self.close_think, seconds=seconds * 0.55)
                        reason, status = split_thinking(trace, self.close_think, self.eos, spec.thinking_tokens)
                        prefix = self.torch.cat((prompt, self.ids_tensor(reason + self.finish_think)), dim=-1)
                        seconds -= time.monotonic() - began
                    generated = self._generate_ids(prefix, cap=spec.tokens, temperature=spec.temperature,
                                                   sample=sample, seconds=max(0.1, seconds))
                answer_ids = trim_eos(generated, self.eos)
                result = {"answer": self.tokenizer.decode(answer_ids, skip_special_tokens=True).strip(),
                          "tokens": len(answer_ids), "thinking_tokens": len(reason), "think_completion": status}
                if spec.trace and spec.thinking:
                    result["thinking"] = self.tokenizer.decode(reason, skip_special_tokens=True).strip()
                if spec.projections and self.bank:
                    layers = sorted({axis.layer for axis in self.bank.axes.values()})
                    activations = self.pooled_activations(prefix, answer_ids, layers, vectors=vectors)
                    raw, scaled = projections(self.torch, self.bank, activations)
                    result["raw_projections"], result["projection_z"] = raw, scaled
                    if vectors:
                        control = self.pooled_activations(prefix, answer_ids, layers)
                        raw_control, z_control = projections(self.torch, self.bank, control)
                        result["unsteered_fixed_answer_projections"] = raw_control
                        result["unsteered_fixed_answer_z"] = z_control
                output.append(result)
        return {"outputs": output, **self.metadata(), "steering": coefficients}
