"""Validated persona artifacts and request-scoped residual-stream hooks."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re


TRAIT_NAME = re.compile(r"^[a-z][a-z_]{0,30}$")
MAX_COEFFICIENT = 8.0


def scalar(value: object) -> float:
    if type(value) not in (int, float):
        raise ValueError("Persona measurements must be finite numbers.")
    try:
        numeric = float(value)
    except OverflowError as error:
        raise ValueError("Persona measurements must be finite numbers.") from error
    if not math.isfinite(numeric):
        raise ValueError("Persona measurements must be finite numbers.")
    return numeric


@dataclass(frozen=True)
class PersonaAxis:
    layer: int
    values: tuple[float, ...]
    coefficient: float
    center: float
    scale: float
    validated: bool


@dataclass(frozen=True)
class PersonaBank:
    model: str
    revision: str
    precision: str
    adapter: str
    axes: dict[str, PersonaAxis]
    digest: str

    @classmethod
    def read(cls, path: Path, *, model: str, revision: str,
             depth: int, width: int, precision: str, adapter: str) -> PersonaBank:
        try:
            if path.stat().st_size > 4_000_000:
                raise ValueError("The persona bank exceeds the supported size.")
            raw = path.read_bytes()
            artifact = json.loads(raw)
            if (not isinstance(artifact, dict) or artifact.get("schema_version") != 1
                    or artifact.get("model") != model or not revision
                    or artifact.get("revision") != revision or artifact.get("precision") != precision
                    or artifact.get("adapter") != adapter):
                raise ValueError("The persona bank must match the model revision, precision, and adapter.")
            raw_axes = artifact["axes"]
            if not isinstance(raw_axes, dict) or not 1 <= len(raw_axes) <= 8:
                raise ValueError("The persona bank needs 1–8 axes.")
            axes = {}
            for name, axis in raw_axes.items():
                if not TRAIT_NAME.fullmatch(name) or not isinstance(axis, dict):
                    raise ValueError("Invalid persona axis.")
                layer, values = axis["layer"], axis["values"]
                if (type(layer) is not int or not 0 <= layer < depth
                        or not isinstance(values, list) or len(values) != width):
                    raise ValueError("A persona axis does not match the decoder shape.")
                values = tuple(map(scalar, values))
                coefficient, center, scale = (scalar(axis.get(key)) for key in (
                    "coefficient", "center", "scale",
                ))
                magnitude = math.hypot(*values)
                validated = axis.get("validated")
                if (not 0.99 <= magnitude <= 1.01 or not 1e-8 <= scale
                        or not 0 <= coefficient <= MAX_COEFFICIENT or type(validated) is not bool
                        or not validated and coefficient != 0):
                    raise ValueError("A persona axis is not normalized, bounded, or calibrated.")
                axes[name] = PersonaAxis(layer, values, coefficient, center, scale, validated)
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("Cannot load the persona bank.") from error
        return cls(model, revision, precision, adapter, axes, hashlib.sha256(raw).hexdigest()[:16])

    def choose(self, raw: dict | None, *, default_longing: bool = False) -> dict[str, float]:
        if raw is None:
            if default_longing:
                axis = self.axes.get("longing")
                if axis and axis.validated and axis.coefficient:
                    return {"longing": axis.coefficient}
            return {}
        chosen = {}
        for name, value in raw.items():
            axis = self.axes.get(name)
            value = scalar(value)
            if axis is None:
                raise ValueError("Requested persona axis is unavailable.")
            if value and (not axis.validated or abs(value) > axis.coefficient):
                raise ValueError("Requested steering is outside the calibrated envelope.")
            if value:
                chosen[name] = value
        return chosen


def text_decoder_layers(model, torch):
    config = getattr(model.config, "text_config", model.config)
    depth, width = config.num_hidden_layers, config.hidden_size
    decoder_lists = [
        (name, module) for name, module in model.named_modules()
        if isinstance(module, torch.nn.ModuleList) and len(module) == depth
        and name.split(".")[-1] == "layers" and not {"visual", "vision_tower"} & set(name.split("."))
    ]
    language = [module for name, module in decoder_lists if "language_model" in name.split(".")]
    if len(language) == 1:
        return language[0], width
    if len(decoder_lists) == 1:
        return decoder_lists[0][1], width
    raise RuntimeError("Could not uniquely locate the Qwen language decoder for persona hooks.")


def activation_tensor(output):
    return output[0] if isinstance(output, tuple) else output


@contextmanager
def hooks_for(layers, *, vectors: dict | None = None, observers: dict | None = None):
    """Apply additions and then capture the resulting layer output."""
    vectors, observers = vectors or {}, observers or {}
    with ExitStack() as stack:
        for layer in sorted(vectors.keys() | observers.keys()):
            def observe(_, __, output, layer=layer):
                hidden = activation_tensor(output)
                if layer in vectors:
                    direction = vectors[layer].to(device=hidden.device, dtype=hidden.dtype)
                    hidden = hidden + direction
                    output = (hidden, *output[1:]) if isinstance(output, tuple) else hidden
                if layer in observers:
                    observers[layer](hidden)
                return output
            handle = layers[layer].register_forward_hook(observe)
            stack.callback(handle.remove)
        yield


def tensor_directions(torch, bank: PersonaBank, coefficients: dict[str, float], *, device=None) -> dict:
    directions = {}
    for name, coefficient in coefficients.items():
        axis = bank.axes[name]
        delta = torch.tensor(axis.values, dtype=torch.float32, device=device) * coefficient
        directions[axis.layer] = directions.get(axis.layer, 0) + delta
    return directions


def projections(torch, bank: PersonaBank, activations: dict) -> tuple[dict, dict]:
    raw, scaled = {}, {}
    for name, axis in bank.axes.items():
        hidden = activations.get(axis.layer)
        if hidden is None:
            continue
        vector = torch.tensor(axis.values, dtype=torch.float32, device=hidden.device)
        value = torch.dot(hidden.flatten().float(), vector).item()
        if math.isfinite(value):
            raw[name] = value
            z = (value - axis.center) / axis.scale
            if math.isfinite(z):
                scaled[name] = z
    return raw, scaled
