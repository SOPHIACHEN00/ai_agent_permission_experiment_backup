"""Single-device CUDA execution of the original masked DDQN, with fixed B."""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import random

from .bootstrap import configure
configure()

import torch
from torch import nn
from torch.nn import functional as F
from pa_rl.ddqn import DDQNHyperparameters, DDQNModelSpec, MaskedDoubleDQN, double_dqn_targets
from .features import PublicDecision, STATE_DIM, CANDIDATE_DIM, MAX_CANDIDATES, schema_manifest

B = dict(gamma=1.0, learning_rate=0.0003, batch_size=64, replay_capacity=20000,
         warmup_transitions=256, optimize_every=4, target_update_every=250, gradient_clip=5.0)


@dataclass(frozen=True)
class DecisionTensors:
    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    candidate_ids: tuple[str, ...]


def tensors(decision: PublicDecision) -> DecisionTensors:
    return DecisionTensors(torch.tensor(decision.state, dtype=torch.float32),
                           torch.tensor(decision.candidates, dtype=torch.float32),
                           torch.tensor(decision.mask, dtype=torch.bool), decision.candidate_ids)


def _hash(value) -> str:
    """Content hash, independent of tensor device and pickle container metadata."""
    hasher = hashlib.sha256()
    def add(item):
        if isinstance(item, torch.Tensor):
            t = item.detach().cpu().contiguous()
            hasher.update(f'tensor:{t.dtype}:{tuple(t.shape)}:'.encode())
            hasher.update(t.numpy().tobytes())
        elif is_dataclass(item):
            add({field.name: getattr(item, field.name) for field in fields(item)})
        elif isinstance(item, dict):
            hasher.update(b'dict:')
            for key in sorted(item, key=repr):
                add(key)
                add(item[key])
        elif isinstance(item, (tuple, list)):
            hasher.update(f'{type(item).__name__}:{len(item)}:'.encode())
            for child in item:
                add(child)
        else:
            hasher.update(f'{type(item).__name__}:{repr(item)};'.encode())
    add(value)
    return hasher.hexdigest()


class CudaLearner(MaskedDoubleDQN):
    def __init__(self, seed: int):
        visible = os.environ.get('CUDA_VISIBLE_DEVICES', '')
        if not visible or ',' in visible or not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise RuntimeError('One explicitly selected CUDA device is required; no CPU fallback')
        expected = os.environ.get('SQSTN_EXPECTED_GPU_UUID', '')
        actual = str(torch.cuda.get_device_properties(0).uuid)
        if not expected or actual.lower().removeprefix('gpu-') != expected.lower().removeprefix('gpu-'):
            raise RuntimeError('Selected physical GPU identity mismatch')
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG') not in (':4096:8', ':16:8'):
            raise RuntimeError('Deterministic CUDA workspace configuration is required')
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        super().__init__(seed=seed, hyperparameters=DDQNHyperparameters(**B),
                         model_spec=DDQNModelSpec(STATE_DIM, CANDIDATE_DIM, MAX_CANDIDATES))
        self.seed = seed
        self.device = torch.device('cuda:0')
        self.online_network.to(self.device)
        self.target_network.to(self.device)
        self._optimizer = torch.optim.Adam(self.online_network.parameters(), lr=B['learning_rate'])
        stream_seed = lambda label: int(hashlib.sha256(f'{seed}:{label}'.encode()).hexdigest(), 16)
        self._rng = random.Random(stream_seed('actor'))
        self._tie_rng = random.Random(stream_seed('tie'))
        self._buffer._rng = random.Random(stream_seed('replay'))

    def select(self, decision: DecisionTensors, *, epsilon: float, evaluation: bool = False) -> str:
        if not math.isfinite(epsilon) or not 0 <= epsilon <= 1 or (evaluation and epsilon != 0):
            raise ValueError('Invalid exploration configuration')
        valid = decision.mask.nonzero(as_tuple=False).flatten().tolist()
        if not valid:
            raise ValueError('No valid candidate')
        if not evaluation and self._rng.random() < epsilon:
            index = self._rng.choice(valid)
        else:
            with torch.no_grad():
                scores = self.online_network(decision.state.to(self.device).unsqueeze(0),
                                             decision.candidate_features.to(self.device).unsqueeze(0)).squeeze(0).cpu()
            if not torch.isfinite(scores).all().item():
                raise RuntimeError('Non-finite Q value')
            best = max(scores[i].item() for i in valid)
            tied = [i for i in valid if scores[i].item() == best]
            index = tied[0] if evaluation else self._tie_rng.choice(tied)
        return decision.candidate_ids[index]

    def _optimize(self) -> float:
        batch = self._buffer.sample(self.hyperparameters.batch_size)
        stack = lambda name: torch.stack([getattr(item, name) for item in batch]).to(self.device)
        states, candidates = stack('state'), stack('candidates')
        actions = torch.tensor([item.action_row for item in batch], dtype=torch.long, device=self.device)
        rewards = torch.tensor([item.reward for item in batch], dtype=torch.float32, device=self.device)
        dones = torch.tensor([item.done for item in batch], dtype=torch.bool, device=self.device)
        selected_q = self.online_network(states, candidates).gather(1, actions[:, None]).squeeze(1)
        with torch.no_grad():
            next_states, next_candidates = stack('next_state'), stack('next_candidates')
            targets = double_dqn_targets(rewards=rewards, dones=dones,
                online_next_q=self.online_network(next_states, next_candidates),
                target_next_q=self.target_network(next_states, next_candidates),
                next_mask=stack('next_mask'), gamma=self.hyperparameters.gamma)
        loss = F.smooth_l1_loss(selected_q, targets)
        if not torch.isfinite(loss).item():
            raise RuntimeError('Non-finite DDQN loss')
        self._optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(self.online_network.parameters(), self.hyperparameters.gradient_clip,
                                 error_if_nonfinite=True)
        self._optimizer.step()
        if any(not torch.isfinite(parameter).all().item() for parameter in self.online_network.parameters()):
            raise RuntimeError('Non-finite DDQN parameter')
        self.optimizer_steps += 1
        if self.optimizer_steps % self.hyperparameters.target_update_every == 0:
            self.target_network.load_state_dict(self.online_network.state_dict())
        return float(loss.detach().item())

    def weight_fingerprint(self) -> str:
        return _hash(self.online_network.state_dict())

    def _state(self) -> dict:
        return {'format': 'sqstn_ddqn_checkpoint_v0', 'seed': self.seed, 'hyperparameters': B,
                'schema': schema_manifest(), 'online': self.online_network.state_dict(),
                'target': self.target_network.state_dict(), 'optimizer': self._optimizer.state_dict(),
                'replay': self._buffer._items, 'cursor': self._buffer._cursor,
                'actor_rng': self._rng.getstate(), 'tie_rng': self._tie_rng.getstate(),
                'replay_rng': self._buffer._rng.getstate(), 'environment_steps': self.environment_steps,
                'optimizer_steps': self.optimizer_steps, 'last_loss': self.last_loss}

    def fingerprint(self) -> str:
        return _hash(self._state())

    def save(self, path: Path) -> dict:
        path = Path(path)
        if path.exists() or path.with_suffix('.json').exists():
            raise FileExistsError('Checkpoint must not overwrite existing evidence')
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self._state(), path)
        receipt = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size,
                   'fingerprint': self.fingerprint(), 'weights': self.weight_fingerprint(),
                   'environment_steps': self.environment_steps, 'optimizer_steps': self.optimizer_steps,
                   'hyperparameters': B, 'schema': schema_manifest()}
        path.with_suffix('.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        return receipt

    @classmethod
    def load(cls, path: Path) -> 'CudaLearner':
        """Load only this run's trusted checkpoint, after its byte-hash verification."""
        path = Path(path)
        receipt = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        if hashlib.sha256(path.read_bytes()).hexdigest() != receipt['sha256']:
            raise ValueError('Checkpoint bytes differ from receipt')
        state = torch.load(path, map_location='cpu', weights_only=False)
        if state['format'] != 'sqstn_ddqn_checkpoint_v0' or state['hyperparameters'] != B or state['schema'] != schema_manifest():
            raise ValueError('Incompatible checkpoint')
        model = cls(state['seed'])
        model.online_network.load_state_dict(state['online'])
        model.target_network.load_state_dict(state['target'])
        model._optimizer.load_state_dict(state['optimizer'])
        model._buffer._items, model._buffer._cursor = state['replay'], state['cursor']
        model._rng.setstate(state['actor_rng'])
        model._tie_rng.setstate(state['tie_rng'])
        model._buffer._rng.setstate(state['replay_rng'])
        model.environment_steps = state['environment_steps']
        model.optimizer_steps, model.last_loss = state['optimizer_steps'], state['last_loss']
        if model.fingerprint() != receipt['fingerprint']:
            raise ValueError('Restored checkpoint state mismatch')
        return model
