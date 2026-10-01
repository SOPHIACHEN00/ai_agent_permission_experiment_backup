"""One-shot local evidence archive, never uploads or executes experiment code."""
import hashlib
import json
from pathlib import Path
import zipfile
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]/'ai_agent_permission_experiment'


def main():
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    freeze = read(HERE/'collection/pre_call_freeze.json')
    output = HERE/'evidence/stopped_collection_evidence.zip'
    output.parent.mkdir(exist_ok=True)
    blobs = {p.relative_to(HERE).as_posix(): p.read_bytes() for p in HERE.rglob('*')
             if p.is_file() and 'evidence' not in p.relative_to(HERE).parts and '__pycache__' not in p.parts}
    for name, expected in freeze['source_hashes'].items():
        value = (REPO/'rl_sqstn_integration_v0'/name).read_bytes()
        assert hashlib.sha256(value).hexdigest() == expected
        blobs['source_snapshot/rl_sqstn_integration_v0/'+name] = value
    test = REPO/'rl_sqstn_integration_v0/tests/test_multistep.py'
    blobs['source_snapshot/rl_sqstn_integration_v0/tests/test_multistep.py'] = test.read_bytes()
    original = HERE.parent/'evidence/package_v0/source.zip'
    assert hashlib.sha256(original.read_bytes()).hexdigest() == read(original.parent/'receipt.json')['sha256']
    # Secret used only as an in-memory comparison; never print or archive it.
    key = dotenv_values(REPO/'qstn_simulator/.env', interpolate=False).get('OPENAI_API_KEY')
    assert key and all(key.encode() not in b for b in blobs.values())
    with zipfile.ZipFile(original) as archive:
        assert all(key.encode() not in archive.read(name) for name in archive.namelist())
    del key
    blobs['source_snapshot/original_frozen_dependencies.zip'] = original.read_bytes()
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(blobs.items()):
            assert not name.endswith('.env')
            archive.writestr(name, value)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert all(archive.read(name) == value for name, value in blobs.items())
    receipt = {'status': 'LOCAL_ARCHIVE_VERIFIED', 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
               'bytes': output.stat().st_size, 'members': len(blobs), 'credential_value_matches': 0,
               'experiment_status': 'STOPPED_NO_RETRY', 'source_files_frozen': len(freeze['source_hashes']),
               'api_calls_added': 0, 'training_steps': 0}
    (output.parent/'archive_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
