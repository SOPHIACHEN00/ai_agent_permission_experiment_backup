"""Local hidden-input controller. Connection credentials remain only in memory."""
from __future__ import annotations
from datetime import datetime, timezone
import getpass
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import zipfile

REPO = Path(__file__).resolve().parents[1]
RECORDS = REPO.parent/'RL_Personal_Assistant_Design/experiments/2026-09-23_sqstn_rl_integration_v0'
TRANSPORT = RECORDS.parent/'2026-09-22_family3_next_stage/stage_b/secure_server_session.py'
REMOTE = '/output/agenticAI/sqstn_rl_integration_v0_20260923'


def decode_receipt(raw: str, auth: tuple[str, str, str, str]) -> dict:
    """Preserve machine values exactly; reject unexpected sensitive payloads."""
    value = json.loads(raw)
    if type(value) is not dict or any(secret and secret in raw for secret in (auth[0], auth[3])):
        raise ValueError('Unexpected sensitive or malformed server receipt')
    forbidden = {'host', 'hostname', 'endpoint', 'port', 'password', 'secret', 'token', 'username', 'account', 'address'}
    def validate(item):
        if isinstance(item, dict):
            if any(str(key).lower() in forbidden for key in item):
                raise ValueError('Sensitive server receipt field')
            for child in item.values():
                validate(child)
        elif isinstance(item, list):
            for child in item:
                validate(child)
    validate(value)
    return value


def main():
    spec = importlib.util.spec_from_file_location('ephemeral_transport', TRANSPORT)
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    auth = tuple(getpass.getpass(label+' (hidden): ') for label in ('Endpoint', 'Port', 'Account', 'Authentication'))
    print(json.dumps({'status': 'AUTH_IN_MEMORY_READY'}), flush=True)
    evidence = RECORDS/'server_evidence'
    evidence.mkdir(exist_ok=True)
    operations = Path(__file__).with_name('server_ops.py').read_text(encoding='utf-8')
    package = RECORDS/'evidence/package_v0/source.zip'
    package_receipt = json.loads((package.parent/'receipt.json').read_text())
    archive_receipt = None
    preflight_passed = False
    for line in sys.stdin:
        try:
            operation = json.loads(line)['operation']
            if operation == 'quit':
                print('{"status":"CLOSED"}', flush=True)
                return
            if operation not in ('preflight', 'upload', 'smoke', 'launch', 'poll', 'archive', 'download'):
                raise ValueError('Unsupported operation')
            if operation == 'upload' and not preflight_passed:
                raise ValueError('Preflight approval not present in this session')
            data = package.read_bytes() if operation == 'upload' else None
            if data is not None and hashlib.sha256(data).hexdigest() != package_receipt['sha256']:
                raise ValueError('Local frozen archive mismatch')
            source = operations + '\nresult=operate(' + repr(operation) + ',' + repr(REMOTE) + ',' + repr(package_receipt['sha256']) + ')\n'
            if operation != 'download':
                source += 'print(json.dumps(result))\n'
            response = transport.command(auth, source, data=data, timeout=55 if operation == 'smoke' else 45)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
            if response.returncode:
                # Transport output may contain connection coordinates: never print/persist it.
                result = {'operation': operation, 'status': 'REMOTE_OR_CONNECTION_COMMAND_FAILED',
                          'returncode': response.returncode, 'automatic_retry': False,
                          'training_state': 'UNKNOWN_UNTIL_READ_ONLY_POLL'}
            elif operation == 'download':
                if archive_receipt is None:
                    raise ValueError('Archive receipt missing in this session')
                if hashlib.sha256(response.stdout).hexdigest() != archive_receipt['sha256']:
                    raise ValueError('Downloaded archive hash mismatch')
                target = evidence/'complete_server_evidence.zip'
                with target.open('xb') as handle:
                    handle.write(response.stdout)
                destination = evidence/'unpacked'
                destination.mkdir(exist_ok=False)
                with zipfile.ZipFile(io.BytesIO(response.stdout)) as archive:
                    if archive.testzip() is not None:
                        raise ValueError('Downloaded archive CRC mismatch')
                    for member in archive.infolist():
                        if not (destination/member.filename).resolve().is_relative_to(destination.resolve()):
                            raise ValueError('Unsafe downloaded archive member')
                    archive.extractall(destination)
                result = {'status': 'DOWNLOAD_VERIFIED', **archive_receipt}
            else:
                result = decode_receipt(response.stdout.decode('utf-8'), auth)
                if operation == 'preflight':
                    preflight_passed = result.get('status') == 'PREFLIGHT_PASS'
                elif operation == 'archive':
                    archive_receipt = result
            receipt = {'time_utc': stamp, 'operation': operation, 'result': result}
            (evidence/(stamp+'_'+operation+'.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
            print(json.dumps(result), flush=True)
        except Exception as error:
            # Exception text/traceback can contain auth or process arguments; suppress them.
            result = {'status': 'LOCAL_CONTROL_FAILED', 'error_type': type(error).__name__,
                      'automatic_retry': False, 'training_state': 'UNKNOWN_UNTIL_READ_ONLY_POLL'}
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
            (evidence/(stamp+'_control_error.json')).write_text(json.dumps(result), encoding='utf-8')
            print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
