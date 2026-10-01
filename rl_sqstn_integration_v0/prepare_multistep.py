"""Bundle frozen dependencies and public graphs; no private cache or credentials."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import zipfile

from .bootstrap import ROOT
from .common import digest
from .live_api import write_json
from .run_multistep import comparison_config


def prepare(records: Path) -> dict:
    collection = records/'collection'
    status = json.loads((collection/'status.json').read_text())
    dataset = json.loads((collection/'dataset.json').read_text())
    verification = json.loads((records/'data_verification.json').read_text())
    if status['status'] != 'DATA_READY' or not dataset['coverage']['passed']:
        raise RuntimeError('Dataset coverage gate did not pass')
    if digest(dataset) != status['dataset_sha256'] or verification['status'] != 'PASS' or verification['dataset_sha256'] != digest(dataset):
        raise RuntimeError('Dataset proof/hash not verified')
    original = records.parent/'evidence/package_v0/source.zip'
    receipt = json.loads((original.parent/'receipt.json').read_text())
    if hashlib.sha256(original.read_bytes()).hexdigest() != receipt['sha256']:
        raise RuntimeError('Original frozen dependency bundle changed')
    with zipfile.ZipFile(original) as archive:
        blobs = {name: archive.read(name) for name in archive.namelist() if name != 'package_manifest.json'}
    for name in ('live_api.py', 'multistep_v1.py', 'run_multistep.py', 'prepare_multistep.py'):
        path = Path(__file__).with_name(name)
        ast.parse(path.read_text(encoding='utf-8'))
        blobs['rl_sqstn_integration_v0/'+name] = path.read_bytes()
    encode = lambda value: json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')
    blobs['dataset.json'] = encode(dataset)
    blobs['dataset_verification.json'] = encode(verification)
    blobs['pilot_config.json'] = encode(comparison_config())
    manifest = {'version': 'sqstn_multistep_public_bundle_v1', 'dataset_sha256': digest(dataset),
                'files': [{'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                          for name, data in sorted(blobs.items())],
                'credentials_included': False, 'private_prompts_included': False,
                'old_test_data_included': False, 'api_calls_during_learning': 0}
    blobs['package_manifest.json'] = encode(manifest)
    destination = records/'evidence/package_v0'
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(destination/'source.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(blobs.items()):
            archive.writestr(name, data)
    archive_path = destination/'source.zip'
    receipt = {'sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
               'bytes': archive_path.stat().st_size, 'files': len(manifest['files']),
               'dataset_sha256': digest(dataset)}
    write_json(destination/'package_manifest.json', manifest)
    write_json(destination/'receipt.json', receipt)
    write_json(destination/'pilot_config.json', comparison_config())
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--records', type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args().records.resolve())))
