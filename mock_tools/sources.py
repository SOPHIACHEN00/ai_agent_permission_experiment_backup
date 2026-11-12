"""Original Wu query/tool/data labels only; no participant responses or S-QSTN."""
from __future__ import annotations

import json
from pathlib import Path

SOURCE_FILE = Path(__file__).resolve().parents[1] / 'external/ai-agent-permissions/queries.json'


def source_queries() -> dict[int, dict]:
    rows = json.loads(SOURCE_FILE.read_text(encoding='utf-8-sig'))
    result = {row['id']: row for row in rows}
    if len(result) != len(rows) or set(result) != set(range(65)):
        raise ValueError('expected the original 65 distinct Wu query IDs')
    return result


def data_items(raw: str) -> tuple[str, ...]:
    """Preserve annotations/typos; split only commas outside parentheses.

    Reused from the prior source adapter. Q48's unclosed final parenthesis is
    retained verbatim, not silently repaired. The complete raw row is retained.
    """
    items, start, depth = [], 0, 0
    for index, char in enumerate(raw):
        if char == '(':
            depth += 1
        elif char == ')':
            depth = max(0, depth - 1)
        elif char == ',' and depth == 0:
            if raw[start:index].strip():
                items.append(raw[start:index].strip())
            start = index + 1
    if raw[start:].strip():
        items.append(raw[start:].strip())
    if len(items) != len(set(items)):
        raise ValueError('source data list contains duplicate items')
    return tuple(items)


def query_ids() -> tuple[int, ...]:
    return tuple(sorted(source_queries()))
