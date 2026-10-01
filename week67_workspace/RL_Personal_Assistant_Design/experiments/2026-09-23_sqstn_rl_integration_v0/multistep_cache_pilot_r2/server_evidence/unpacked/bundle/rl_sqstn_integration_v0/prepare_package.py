"""Allowlisted source/config bundle; never include old data, models, or secrets."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import zipfile

from .bootstrap import ROOT
from .run_pilot import pilot_config


def prepare(records: Path) -> dict:
    destination = records / 'evidence' / 'package_v0'
    destination.mkdir(parents=True, exist_ok=False)
    blobs = {}
    def include(path: Path):
        resolved = path.resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.is_file():
            raise ValueError('Bundle input outside source root or missing')
        relative = resolved.relative_to(ROOT).as_posix()
        if resolved.suffix == '.py':
            ast.parse(resolved.read_text(encoding='utf-8'), filename=relative)
        blobs[relative] = resolved.read_bytes()
    core = ROOT / 'rl_personal_assistant/src/pa_rl'
    pending, seen = ['__init__', 'environment', 'ddqn', 'scripted_user'], set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        path = core / (name + '.py')
        include(path)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.ImportFrom) and node.level:
                if node.level != 1 or not node.module or '.' in node.module:
                    raise ValueError('Unexpected core import; inspect before packaging')
                pending.append(node.module)
    for path in (ROOT / 'rl_sqstn_integration_v0').rglob('*.py'):
        if path.name != 'secure_control.py':
            include(path)
    for relative in ('qstn_simulator/scripts/__init__.py',
        'qstn_simulator/scripts/v1/rulepack_v1.py', 'qstn_simulator/scripts/v1_1/rulepack_v1_1.py',
        'qstn_simulator/scripts/v2/rulepack_v2.py', 'qstn_simulator/scripts/v2/state_store_v2.py',
        'bandit_experiment/run_stated_policy_bandit.py', 'online_bandit_experiment/wp_fts.py'):
        include(ROOT / relative)
    for relative in ('qstn_simulator/scripts/v1', 'qstn_simulator/scripts/v1_1',
                     'qstn_simulator/scripts/v2', 'bandit_experiment', 'online_bandit_experiment'):
        path = ROOT / relative / '__init__.py'
        if path.exists():
            include(path)
    for name in ('security_behavior_rules.json', 'respondent_contract.en.md', 'event_schema.json',
                 'state_schema.json', 'retention_policy.json', 'privacy_security_rule_skill.md'):
        include(ROOT / 'qstn_simulator/config/v2.0' / name)
    frozen = json.loads((records / 'FROZEN_DDQN_B.json').read_text(encoding='utf-8'))
    config = pilot_config(frozen['hyperparameters'])
    encode = lambda value: json.dumps(value, indent=2, ensure_ascii=False).encode('utf-8')
    blobs['frozen_ddqn_b.json'] = encode(frozen)
    blobs['pilot_config.json'] = encode(config)
    manifest = {'version': 'sqstn_source_bundle_v0', 'files': [
        {'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        for name, data in sorted(blobs.items())], 'old_test_data_included': False,
        'credentials_included': False, 'api_client_included': False}
    blobs['package_manifest.json'] = encode(manifest)
    path = destination / 'source.zip'
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(blobs.items()):
            archive.writestr(name, data)
    for name, value in (('package_manifest.json', manifest), ('pilot_config.json', config)):
        (destination / name).write_bytes(encode(value))
    receipt = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size,
               'files': len(manifest['files']), 'local_model_execution': False}
    (destination / 'receipt.json').write_bytes(encode(receipt))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--records', required=True, type=Path)
    print(json.dumps(prepare(parser.parse_args().records)))
