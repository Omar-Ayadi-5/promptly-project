"""Model capability filtering shared with the frontend through one parameter schema."""
import json
import math
from pathlib import Path

PARAMETER_CONFIG = json.loads(
    (Path(__file__).resolve().parent.parent / "model_parameters.json").read_text(encoding="utf-8")
)


def supported_parameters(model):
    names = model.get("supported_parameters")
    if names is None:
        return {key for key, config in PARAMETER_CONFIG.items() if config.get("legacy")}
    if not isinstance(names, list):
        return set()
    return {name for name in names if isinstance(name, str) and name in PARAMETER_CONFIG}


def valid_parameter(name, value):
    config = PARAMETER_CONFIG.get(name)
    if config is None or value is None:
        return False
    kind = config["type"]
    if kind in {"number", "integer"}:
        return (
            type(value) in (int, float)
            and math.isfinite(value)
            and (kind != "integer" or (float(value).is_integer() and abs(value) <= 9007199254740991))
            and ("min" not in config or value >= config["min"])
            and ("max" not in config or value <= config["max"])
        )
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str)
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    if kind == "stop":
        return isinstance(value, str) or (
            isinstance(value, list) and all(isinstance(item, str) for item in value)
        )
    if kind == "choice":
        return isinstance(value, (str, dict))
    return False


def max_tokens_limit(model):
    provider = model.get("top_provider")
    provider = provider if isinstance(provider, dict) else {}
    limits = [model.get("max_completion_tokens"), provider.get("max_completion_tokens"), model.get("context")]
    return min((value for value in limits if type(value) is int and value > 0), default=math.inf)


def filter_parameters(model, requested):
    supported = supported_parameters(model)
    return {
        key: min(value, max_tokens_limit(model)) if key == "max_tokens" else value
        for key, value in requested.items()
        if key in supported and valid_parameter(key, value)
    }


def openrouter_parameters(model, requested):
    """Only known API fields may enter extra_body, never arbitrary client metadata."""
    defaults = model.get("default_parameters")
    defaults = defaults if isinstance(defaults, dict) else {}
    initial = {
        key: config["default"] for key, config in PARAMETER_CONFIG.items()
        if "default" in config
    }
    initial.update(filter_parameters(model, defaults))
    initial.update(filter_parameters(model, requested))
    safe = filter_parameters(model, initial)
    # Older records cannot promise provider support; preserve their loose routing.
    if safe and isinstance(model.get("supported_parameters"), list):
        safe["provider"] = {"require_parameters": True}
    return safe
