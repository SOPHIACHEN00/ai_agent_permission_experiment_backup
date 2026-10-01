"""Credential-free server preflight, one-shot launch, and read-only observation."""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile


def _write(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def _identity(pid):
    try:
        raw = Path(f'/proc/{pid}/stat').read_text()
        return {'pid': pid, 'start_ticks': int(raw[raw.rfind(')')+2:].split()[19]),
                'command': Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode()}
    except FileNotFoundError:
        return None


def _resources():
    raw = subprocess.run(['nvidia-smi', '--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu',
                          '--format=csv,noheader,nounits'], check=True, capture_output=True, text=True).stdout
    apps = subprocess.run(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'],
                          check=True, capture_output=True, text=True).stdout
    rows = []
    for line in raw.splitlines():
        index, uuid, name, used, total, utilization = [part.strip() for part in line.split(',')]
        rows.append({'index': int(index), 'uuid': uuid, 'name': name, 'used_mib': int(used),
                     'total_mib': int(total), 'utilization': int(utilization),
                     'compute_processes': sum(row.split(',')[0].strip() == uuid for row in apps.splitlines())})
    mem = next(int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()
               if line.startswith('MemAvailable:'))
    headroom = mem
    for prefix, limit, current in (('/sys/fs/cgroup', 'memory.max', 'memory.current'),
                                   ('/sys/fs/cgroup/memory', 'memory.limit_in_bytes', 'memory.usage_in_bytes')):
        limit_path, current_path = Path(prefix)/limit, Path(prefix)/current
        if limit_path.exists() and current_path.exists() and limit_path.read_text().strip() != 'max':
            headroom = min(headroom, max(0, int(limit_path.read_text()) - int(current_path.read_text())))
    return {'gpus': rows, 'current_headroom_bytes': headroom, 'time_epoch': time.time()}


def _idle(root, selected=None):
    resources = _resources()
    eligible = [row for row in resources['gpus'] if row['compute_processes'] == 0
                and row['used_mib'] < 256 and row['utilization'] == 0
                and (selected is None or row['index'] == selected['index'] and row['uuid'] == selected['uuid'])]
    if not eligible or resources['current_headroom_bytes'] < 4*1024**3:
        raise RuntimeError('No approved idle GPU or less than 4 GiB current memory headroom')
    return resources, eligible[0]


def _env(selected):
    return dict(os.environ, CUDA_VISIBLE_DEVICES=str(selected['index']), CUDA_DEVICE_ORDER='PCI_BUS_ID',
                SQSTN_EXPECTED_GPU_UUID=selected['uuid'], CUBLAS_WORKSPACE_CONFIG=':4096:8',
                OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')


def _verify(root):
    bundle = root/'bundle'
    manifest = json.loads((bundle/'package_manifest.json').read_text())
    for row in manifest['files']:
        member = (bundle/row['path']).resolve()
        if not member.is_relative_to(bundle.resolve()) or hashlib.sha256(member.read_bytes()).hexdigest() != row['sha256']:
            raise RuntimeError('Bundle source hash mismatch')
    return len(manifest['files'])


def operate(operation, root_path, expected_hash=None):
    root = Path(root_path)
    if root.parent != Path('/output/agenticAI') or not root.name.startswith('sqstn_rl_integration_v0_'):
        raise ValueError('Server target outside approved experiment directory')
    if operation == 'preflight':
        resources, selected = _idle(root)
        if not root.parent.is_dir() or root.exists():
            raise RuntimeError('Experiment root unavailable or already exists')
        probe = "import json,sys,torch,numpy,scipy,pandas,sklearn; print(json.dumps({'python':sys.version.split()[0],'torch':str(torch.__version__),'cuda':torch.version.cuda,'visible_devices':torch.cuda.device_count(),'visible_uuid':str(torch.cuda.get_device_properties(0).uuid),'numpy':numpy.__version__,'scipy':scipy.__version__,'pandas':pandas.__version__,'sklearn':sklearn.__version__}))"
        result = subprocess.run([sys.executable, '-B', '-c', probe], env=_env(selected), capture_output=True, text=True)
        if result.returncode:
            return {'status': 'DEPENDENCY_OR_CUDA_PREFLIGHT_FAILED', 'returncode': result.returncode,
                    'details': result.stderr[-4000:], 'resources': resources, 'selected': selected}
        dependencies = json.loads(result.stdout)
        if dependencies['visible_devices'] != 1 or dependencies['visible_uuid'].lower().removeprefix('gpu-') != selected['uuid'].lower().removeprefix('gpu-'):
            raise RuntimeError('Physical CUDA identity mismatch')
        return {'status': 'PREFLIGHT_PASS', 'resources': resources, 'selected': selected, 'dependencies': dependencies}
    if operation == 'upload':
        data = sys.stdin.buffer.read()
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise RuntimeError('Uploaded archive hash mismatch')
        root.mkdir(exist_ok=False)
        (root/'source.zip').write_bytes(data)
        bundle = root/'bundle'
        bundle.mkdir()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if archive.testzip() is not None:
                raise RuntimeError('Source archive CRC mismatch')
            for entry in archive.infolist():
                if not (bundle/entry.filename).resolve().is_relative_to(bundle.resolve()):
                    raise RuntimeError('Unsafe archive member')
            archive.extractall(bundle)
        receipt = {'status': 'UPLOAD_PASS', 'source_sha256': expected_hash, 'verified_files': _verify(root)}
        _write(root/'upload.json', receipt)
        return receipt
    if operation in ('smoke', 'launch'):
        _verify(root)
        if operation == 'launch':
            smoke = json.loads((root/'smoke.json').read_text())
            if smoke['returncode'] != 0:
                raise RuntimeError('Smoke failed; pilot launch forbidden')
            selected = smoke['selected']
        else:
            selected = None
        resources, selected = _idle(root, selected)
        marker = root/(operation+'.once')
        with marker.open('x') as handle:
            handle.write(str(time.time()))
        if operation == 'smoke':
            with (root/'smoke.log').open('w') as log:
                proc = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover',
                    '-s', 'rl_sqstn_integration_v0/tests', '-p', 'test_cuda.py', '-v'],
                    cwd=root/'bundle', env=_env(selected), stdout=log, stderr=subprocess.STDOUT)
            receipt = {'returncode': proc.returncode, 'selected': selected, 'resources': resources,
                       'type': 'NON_EVIDENCE_ONE_UPDATE_SMOKE', 'ended_epoch': time.time()}
            _write(root/'smoke.json', receipt)
            return {**receipt, 'log': (root/'smoke.log').read_text()}
        supervisor = "from pathlib import Path; import subprocess,sys,time,json; r=Path(sys.argv[1]); t=time.time(); p=subprocess.Popen([sys.executable,'-B','-m','rl_sqstn_integration_v0.run_multistep','--output',str(r/'run')],cwd=r/'bundle'); raw=Path(f'/proc/{p.pid}/stat').read_text(); (r/'child.json').write_text(json.dumps({'pid':p.pid,'start_ticks':int(raw[raw.rfind(')')+2:].split()[19]),'started_epoch':t})); code=p.wait(); (r/'exit.json').write_text(json.dumps({'exit_code':code,'elapsed_seconds':time.time()-t,'test_opened':False})); sys.exit(code)"
        with (root/'training.log').open('w') as log:
            proc = subprocess.Popen([sys.executable, '-B', '-c', supervisor, str(root)], env=_env(selected),
                                    cwd=root/'bundle', stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
        receipt = {'identity': _identity(proc.pid), 'selected': selected, 'resources': resources,
                   'started_epoch': time.time(), 'automatic_retry': False}
        _write(root/'launch.json', receipt)
        return receipt
    if operation == 'poll':
        result = {'resources': _resources()}
        for name in ('upload.json', 'smoke.json', 'launch.json', 'child.json', 'exit.json',
                     'run/status.json', 'run/completion.json', 'run/failure.json'):
            path = root/name
            if path.exists():
                result[name] = json.loads(path.read_text())
        for name, record in (('supervisor', result.get('launch.json', {}).get('identity')),
                             ('child', result.get('child.json'))):
            if record:
                actual = _identity(record['pid'])
                result[name+'_process'] = {'expected': record, 'actual': actual,
                    'identity_matches': actual is not None and actual['start_ticks'] == record['start_ticks']}
        for name in ('training.log', 'smoke.log'):
            path = root/name
            if path.exists():
                result[name+'_tail'] = '\n'.join(path.read_text().splitlines()[-8:])
        return result
    if operation == 'archive':
        if (root/'launch.once').exists() and not (root/'exit.json').exists():
            raise RuntimeError('Do not archive an unfinished pilot')
        target = root/'evidence.zip'
        with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(root.rglob('*')):
                if path.is_file() and path != target:
                    archive.write(path, path.relative_to(root).as_posix())
        receipt = {'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'bytes': target.stat().st_size}
        _write(root/'archive.json', receipt)
        return receipt
    if operation == 'download':
        sys.stdout.buffer.write((root/'evidence.zip').read_bytes())
        return None
    raise ValueError('Unsupported server operation')
