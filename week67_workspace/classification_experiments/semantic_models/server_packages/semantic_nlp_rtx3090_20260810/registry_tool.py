"""Small dependency-free CLI for reading the audited model registry."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence


REGISTRY_PATH = Path(__file__).resolve().parent / "model_registry.json"
MODEL_KEY_PATTERN = re.compile(r"[a-z0-9][a-z0-9_]{1,63}")


def load_registry() -> dict[str, Any]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported model registry schema.")
    models = payload.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError("Model registry has no models.")
    for key, config in models.items():
        if MODEL_KEY_PATTERN.fullmatch(key) is None:
            raise ValueError(f"Unsafe model key: {key!r}")
        revision = str(config.get("revision", ""))
        if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
            raise ValueError(f"Model {key!r} does not have a pinned 40-character commit.")
    return payload


def print_value(value: Any) -> None:
    if isinstance(value, list):
        print(" ".join(str(item) for item in value))
    elif isinstance(value, bool):
        print("true" if value else "false")
    elif isinstance(value, (str, int, float)):
        print(value)
    else:
        raise TypeError(f"Registry value is not shell-scalar/list compatible: {type(value).__name__}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("keys", help="Print model keys, one per line.")
    get_model = subparsers.add_parser("get", help="Print one model field.")
    get_model.add_argument("model_key")
    get_model.add_argument("field")
    get_common = subparsers.add_parser("get-common", help="Print one common field.")
    get_common.add_argument("field")
    show = subparsers.add_parser("show", help="Print one model as JSON.")
    show.add_argument("model_key")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    registry = load_registry()
    models = registry["models"]
    if args.command == "keys":
        for key in models:
            print(key)
        return
    if args.command == "get-common":
        common = registry["common"]
        if args.field not in common:
            raise SystemExit(f"Unknown common registry field: {args.field}")
        print_value(common[args.field])
        return
    if args.model_key not in models:
        raise SystemExit(
            f"Unknown model key {args.model_key!r}; valid keys: {', '.join(models)}"
        )
    config = models[args.model_key]
    if args.command == "show":
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return
    if args.field not in config:
        raise SystemExit(f"Unknown field {args.field!r} for model {args.model_key!r}")
    print_value(config[args.field])


if __name__ == "__main__":
    main()
