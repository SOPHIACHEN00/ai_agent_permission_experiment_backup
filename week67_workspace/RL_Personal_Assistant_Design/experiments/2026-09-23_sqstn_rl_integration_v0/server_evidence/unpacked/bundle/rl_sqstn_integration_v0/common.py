"""Canonical artifact serialization, without model or network imports."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum


def plain(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise TypeError('Unsupported artifact type: ' + type(value).__name__)


def canonical(value: object) -> str:
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()
