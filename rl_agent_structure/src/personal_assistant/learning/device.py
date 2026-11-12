"""CPU replay with optional CUDA network compute; learner mathematics are unchanged.

The bridge moves Q outputs back to the caller's device, preserving the native
masked selector, replay, Double-DQN targets and optimizer loop. Tensor transfers
are differentiable: network parameters, gradients and Adam state live on CUDA.
This is portability support, not a multi-GPU implementation or a speedup claim.
"""
from __future__ import annotations

import torch
from torch import nn
from .ddqn import MaskedDoubleDQN


def resolve_device(value='auto') -> torch.device:
    if value == 'auto':
        value = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    try:
        device = torch.device(value)
    except (TypeError, RuntimeError) as error:
        raise ValueError('device must be auto, cpu or cuda[:index]') from error
    if device.type not in {'cpu', 'cuda'}:
        raise ValueError('only CPU and CUDA devices are supported')
    if device.type == 'cuda':
        if not torch.cuda.is_available():
            raise ValueError('requested CUDA device is unavailable; select cpu explicitly')
        index = torch.cuda.current_device() if device.index is None else device.index
        if index >= torch.cuda.device_count():
            raise ValueError('requested CUDA device is unavailable; select cpu explicitly')
        device = torch.device('cuda', index)
    return device


class _DeviceNetwork(nn.Module):
    def __init__(self, network, device):
        super().__init__()
        self.network = network.to(device)

    def forward(self, state, candidates):
        device = next(self.network.parameters()).device
        return self.network(state.to(device), candidates.to(device)).to(state.device)


class DeviceMaskedDoubleDQN(MaskedDoubleDQN):
    def __init__(self, *, device='auto', **kwargs):
        self.device = resolve_device(device)
        # The target-network constructor also consumes torch RNG; isolate it.
        # torch.manual_seed also touches every CUDA generator.
        devices = list(range(torch.cuda.device_count())) if torch.cuda.is_available() else []
        with torch.random.fork_rng(devices=devices):
            super().__init__(**kwargs)
        self.online_network = _DeviceNetwork(self.online_network, self.device)
        self.target_network = _DeviceNetwork(self.target_network, self.device)
        self.target_network.eval()
        self._optimizer = torch.optim.Adam(self.online_network.parameters(), lr=self.hyperparameters.learning_rate)
