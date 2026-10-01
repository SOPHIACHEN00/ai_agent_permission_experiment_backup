"""Archive verified local evidence and frozen source; never network or train."""
import hashlib
import io
import json
from pathlib import Path
import zipfile
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]/'ai_agent_permission_experiment'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
assert read(HERE/'data_verification.json')['status'] == 'PASS'
assert read(HERE/'comparison_verification.json')['status'] == 'PASS'
target = HERE/'evidence/complete_local_evidence.zip'
receipt_path = target.parent/'complete_local_evidence_receipt.json'
blobs = {}
for path in HERE.rglob('*'):
    relative = path.relative_to(HERE)
    if (not path.is_file() or path in (target, receipt_path) or '__pycache__' in relative.parts
            or relative.parts[:2] == ('server_evidence','unpacked')):
        continue
    blobs[relative.as_posix()] = path.read_bytes()
freeze = read(HERE/'collection/pre_call_freeze.json')
for name, expected in freeze['source_hashes'].items():
    data = (REPO/'rl_sqstn_integration_v0'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected
    blobs['source_snapshot/rl_sqstn_integration_v0/'+name] = data
blobs['source_snapshot/tests/test_multistep_r2.py'] = (REPO/'rl_sqstn_integration_v0/tests/test_multistep_r2.py').read_bytes()
prior_dir = HERE.parent/'multistep_cache_pilot_v1/evidence'
prior_data = (prior_dir/'stopped_collection_evidence.zip').read_bytes()
assert hashlib.sha256(prior_data).hexdigest() == read(prior_dir/'archive_receipt.json')['sha256']
blobs['prior_evidence/stopped_collection_evidence.zip'] = prior_data
key = dotenv_values(REPO/'qstn_simulator/.env', interpolate=False).get('OPENAI_API_KEY')
assert key
def scan(name, data):
    assert not name.endswith('.env') and key.encode() not in data
    if name.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            assert archive.testzip() is None
            for entry in archive.namelist():
                scan(entry, archive.read(entry))
for name,data in blobs.items():
    scan(name,data)
del key
with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,data in sorted(blobs.items()):
        archive.writestr(name,data)
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
    assert all(archive.read(name)==data for name,data in blobs.items())
receipt = {'status':'LOCAL_COMPLETE_ARCHIVE_VERIFIED','sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
           'bytes':target.stat().st_size,'members':len(blobs),'frozen_source_files':len(freeze['source_hashes']),
           'credential_value_matches':0,'old_nine_response_evidence_included':True,
           'server_result_archive_included':True,'api_calls_added':0,'training_steps_added':0}
receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
