"""Provider-independent checks for finite, unambiguous JSON values."""
from __future__ import annotations

import json
import math
from typing import Any, Mapping


def validate_json_value(value: Any) -> None:
    """Reject ambiguous keys/non-JSON values before freeze_value can coerce them."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError('argument object keys must be strings')
        for item in value.values(): validate_json_value(item)
        return
    if isinstance(value, (tuple, list)):
        for item in value: validate_json_value(item)
        return
    raise ValueError('arguments must contain only finite JSON values')


def parse_arguments_json(text: str) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('duplicate argument JSON key')
            result[key] = value
        return result
    value = json.loads(text, object_pairs_hook=unique)
    if not isinstance(value, dict): raise ValueError('arguments_json must encode an object')
    validate_json_value(value)
    return value
