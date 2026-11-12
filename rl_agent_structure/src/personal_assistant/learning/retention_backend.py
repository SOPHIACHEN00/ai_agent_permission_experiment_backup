"""Optional fixed-bank auxiliary term in the SAME native DDQN optimizer step."""
import torch
from torch.nn import functional as F
from .device import DeviceMaskedDoubleDQN
from .ddqn import double_dqn_targets, _padded
from .retention import family_weights, retention_loss
from ..contracts.permission import ControllerAction


class RetainedDoubleDQN(DeviceMaskedDoubleDQN):
    def __init__(self, *, retention_weight=0., **kwargs):
        super().__init__(**kwargs)
        self.retention_weight = retention_weight
        self.fixed_batch = None
        self.fixed_weights = None
        self.retention_applications = 0
        self.last_auxiliary_loss = None

    def set_bank(self, bank, encoder):
        samples = bank.transitions
        returns = [0.] * len(samples); value = 0.
        for i in range(len(samples)-1, -1, -1):
            t = samples[i]
            if t.done: value = 0.
            value = t.reward + self.hyperparameters.gamma * value
            returns[i] = value
        rows = []
        for t in samples:
            e = encoder.encode(t.pre_decision)
            rows.append((*_padded(e, e.mask, self.model_spec), e.candidate_ids.index(t.action_candidate_id)))
        states, candidates, masks = (torch.stack([r[i] for r in rows]) for i in range(3))
        actions = torch.tensor([r[3] for r in rows], dtype=torch.long)
        self.fixed_batch = (states, candidates, masks, actions, torch.tensor(returns, dtype=torch.float32))
        families = candidates[torch.arange(len(actions)), actions, :len(ControllerAction)].argmax(1)
        self.fixed_weights = family_weights(families)

    def _optimize(self):
        if not self.retention_weight: return super()._optimize()
        if self.fixed_batch is None: raise ValueError('fixed observed bank required')
        batch = self._buffer.sample(self.hyperparameters.batch_size)
        states = torch.stack([x.state for x in batch]); candidates = torch.stack([x.candidates for x in batch])
        q = self.online_network(states, candidates)
        actions = torch.tensor([x.action_row for x in batch], dtype=torch.long, device=q.device)
        chosen = q.gather(1, actions[:, None]).squeeze(1)
        ns = torch.stack([x.next_state for x in batch]); nc = torch.stack([x.next_candidates for x in batch])
        with torch.no_grad():
            target = double_dqn_targets(rewards=torch.tensor([x.reward for x in batch], device=q.device),
                dones=torch.tensor([x.done for x in batch], dtype=torch.bool, device=q.device),
                online_next_q=self.online_network(ns, nc).to(q.device),
                target_next_q=self.target_network(ns, nc).to(q.device),
                next_mask=torch.stack([x.next_mask for x in batch]).to(q.device), gamma=self.hyperparameters.gamma)
        ds, dc, dm, da, dr = self.fixed_batch
        auxiliary = retention_loss(self.online_network(ds, dc), dm, da, dr, self.fixed_weights, margin=.1)
        loss = F.smooth_l1_loss(chosen, target) + self.retention_weight * auxiliary
        self._optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_network.parameters(), self.hyperparameters.gradient_clip)
        self._optimizer.step()
        self.optimizer_steps += 1
        self.retention_applications += 1
        self.last_auxiliary_loss = float(auxiliary.detach())
        if self.optimizer_steps % self.hyperparameters.target_update_every == 0:
            self.target_network.load_state_dict(self.online_network.state_dict())
        return float(loss.detach())
