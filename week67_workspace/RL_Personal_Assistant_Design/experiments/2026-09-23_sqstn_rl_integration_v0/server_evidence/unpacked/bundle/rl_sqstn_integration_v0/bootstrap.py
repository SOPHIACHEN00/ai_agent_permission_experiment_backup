"""Select one complete authority kernel; never mix the partial CUDA snapshot."""
from __future__ import annotations

import hashlib
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'rl_personal_assistant' / 'src'
QSTN = ROOT / 'qstn_simulator'


def configure() -> None:
    for name, expected in (('pa_rl', CORE / 'pa_rl'), ('scripts', QSTN / 'scripts')):
        existing = sys.modules.get(name)
        if existing is not None:
            filename = getattr(existing, '__file__', None)
            if filename is None or not Path(filename).resolve().is_relative_to(expected):
                raise RuntimeError('Mixed dependency root: ' + name)
    for path in (ROOT, QSTN, CORE):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def provenance() -> dict[str, dict[str, str]]:
    configure()
    result = {}
    for name in ('pa_rl.environment', 'pa_rl.authorization', 'pa_rl.execution',
                 'scripts.v2.rulepack_v2', 'scripts.v2.state_store_v2',
                 'online_bandit_experiment.wp_fts'):
        path = Path(importlib.import_module(name).__file__).resolve()
        if not path.is_relative_to(ROOT):
            raise RuntimeError('Dependency imported outside the frozen package')
        result[name] = {'path': path.relative_to(ROOT).as_posix(),
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return result


configure()
