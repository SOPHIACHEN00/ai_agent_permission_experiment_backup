"""Public-only bridge; selected deployment is GPU1 under GPU0/1 authorization."""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
from dataclasses import asdict, dataclass
from fractions import Fraction as F
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage_a"))
from budget_recourse import ACTIONS, State, legal_actions
from budget_recourse_env import Environment, Tape
from pa_rl.ddqn import DDQNHyperparameters, DDQNModelSpec, MaskedDoubleDQN, _policy_mask
from pa_rl.family3_v2_learning import Family3V2LearnerRngDeriver, Family3V2MaskedDoubleDQN

EXPERIMENT_ID = "increment8_budget_recourse_pilot_v0"
ENCODER_SCHEMA = "budget_recourse_public_18_candidate_10_v1"
RNG_SCHEMA = "budget_recourse_named_rng_v1"
MODEL_SPEC = DDQNModelSpec(18, 10, 7)
TIE_RTOL, TIE_ATOL = 1e-7, 1e-8
PHYSICAL_GPU = "1"
STATE_FEATURES = (
    "n1/2", "n2/2", "forecast", "future_high", "exposure/24", "prompts/3",
    "stage1", "stage2", "common_pending", "continuation_pending",
    "grant_none", "grant_narrow", "grant_broader", "request_open",
    "branch_unrevealed", "branch_exact", "branch_broader", "remaining/12",
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True, slots=True, init=False)
class LearnerDecision:
    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    semantic_candidate_ids: tuple[str, ...]
    public_key: tuple[tuple[str, object], ...]
    fingerprint: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise ValueError("use encode(public_state), not a hand-built learner decision")

    def _computed_fingerprint(self) -> str:
        return _digest([ENCODER_SCHEMA, self.state.tolist(), self.candidate_features.tolist(),
                        self.mask.tolist(), self.semantic_candidate_ids, self.public_key])

    def require_integrity(self) -> None:
        for tensor, shape, dtype in ((self.state, (18,), torch.float32),
                                     (self.candidate_features, (7, 10), torch.float32),
                                     (self.mask, (7,), torch.bool)):
            if not isinstance(tensor, torch.Tensor) or tuple(tensor.shape) != shape or tensor.dtype is not dtype or tensor.device.type != "cpu":
                raise ValueError("learner decision tensor contract changed")
        if self.semantic_candidate_ids != ACTIONS or not bool(self.mask.any()):
            raise ValueError("invalid learner action catalog")
        if not bool(torch.isfinite(self.state).all()) or not bool(torch.isfinite(self.candidate_features).all()):
            raise ValueError("non-finite learner input")
        if not torch.equal(self.candidate_features[:, 7], self.mask.float()):
            raise ValueError("candidate validity feature differs from authoritative mask")
        if self._computed_fingerprint() != self.fingerprint:
            raise ValueError("learner decision changed after public encoding")


def encode(state: State) -> LearnerDecision:
    if type(state) is not State or state.status != "running" or state.progress not in (0, 1) or state.remaining < 1:
        raise ValueError("encoder accepts only a live public State")
    if state.n1 > 2 or state.n2 > 2 or state.exposure > 24 or state.prompts > 3:
        raise ValueError("state exceeds this frozen pilot's public feature ranges")
    values = [state.n1 / 2, state.n2 / 2, float(state.forecast), float(state.future_high),
              state.exposure / 24, state.prompts / 3]
    values += [float(state.stage == value) for value in (1, 2)]
    values += [float(state.progress == value) for value in (0, 1)]
    values += [float(state.grant == value) for value in (0, 1, 2)]
    values += [float(state.request_open)]
    values += [float(state.branch == value) for value in (0, 1, 2)]
    values += [state.remaining / 12]
    allowed = legal_actions(state)
    mask = torch.tensor([action in allowed for action in ACTIONS], dtype=torch.bool)
    candidates = torch.zeros((7, 10), dtype=torch.float32)
    candidates[:, :7] = torch.eye(7, dtype=torch.float32)
    candidates[:, 7] = mask.float()
    for index, action in enumerate(ACTIONS):
        width = 1 if action == "request_narrow" else 2 if action == "request_broader" else state.grant if action == "execute_covering" else 0
        candidates[index, 8] = width * state.cost / 24
        candidates[index, 9] = float(action in ("request_narrow", "request_broader"))
    public_key = tuple((key, str(value) if type(value) is F else value) for key, value in asdict(state).items())
    decision = object.__new__(LearnerDecision)
    for name, value in (("state", torch.tensor(values, dtype=torch.float32)),
                        ("candidate_features", candidates), ("mask", mask),
                        ("semantic_candidate_ids", ACTIONS), ("public_key", public_key)):
        object.__setattr__(decision, name, value)
    object.__setattr__(decision, "fingerprint", decision._computed_fingerprint())
    decision.require_integrity()
    return decision


def greedy_distribution(decision: LearnerDecision, scores: torch.Tensor) -> dict[str, F]:
    decision.require_integrity()
    if not isinstance(scores, torch.Tensor) or tuple(scores.shape) != (7,) or not bool(torch.isfinite(scores).all()):
        raise ValueError("policy scores must be seven finite values")
    scores = scores.detach().to(device="cpu", dtype=torch.float64)
    best = scores[decision.mask].max()
    tied = decision.mask & torch.isclose(scores, best, rtol=TIE_RTOL, atol=TIE_ATOL)
    actions = [ACTIONS[index] for index in tied.nonzero().flatten().tolist()]
    return {action: F(1, len(actions)) for action in actions}


def seed_for(namespace: str, *coordinates: object) -> int:
    if not isinstance(namespace, str) or not namespace:
        raise ValueError("RNG namespace required")
    return int(_digest([RNG_SCHEMA, EXPERIMENT_ID, namespace, coordinates])[:16], 16)


def draw_tape(initial: State, *, seed: int, graph_id: str, episode: int, phase: str) -> Tape:
    """Environment/evaluator only. No method, gamma, condition or action-count key."""
    if type(initial) is not State or type(seed) is not int or type(episode) is not int or seed < 0 or episode < 0:
        raise ValueError("invalid environment RNG coordinates")
    if not isinstance(graph_id, str) or not graph_id or phase not in ("train", "validation", "test"):
        raise ValueError("invalid environment split/graph coordinate")
    coordinates = phase, seed, graph_id, episode

    def draw(namespace: str, probability: F) -> bool:
        rng = random.Random(seed_for(namespace, *coordinates))
        return rng.randrange(probability.denominator) < probability.numerator

    high = draw("forecast2", initial.future_high)
    p2 = F(4, 5) if high else F(1, 5)
    return Tape(1 if draw("branch1", initial.forecast) else 2,
                high, 1 if draw("branch2", p2) else 2)


class BudgetRecourseDDQN(Family3V2MaskedDoubleDQN):
    """Reuse the frozen CUDA optimizer, but never fake a Family3-v2 decision."""
    def __init__(self, *, seed: int, gamma: int) -> None:
        if os.environ.get("PA_RL_DEVICE") != "cuda:0" or os.environ.get("CUDA_VISIBLE_DEVICES") != PHYSICAL_GPU:
            raise ValueError("this deployment requires physical GPU1; CPU/other-GPU fallback forbidden")
        if type(seed) is not int or seed not in (101, 211, 307) or type(gamma) is not int or gamma not in (0, 1):
            raise ValueError("use frozen seed and gamma coordinates")
        settings = DDQNHyperparameters(gamma=gamma, learning_rate=0.001, batch_size=64,
            replay_capacity=20000, warmup_transitions=256, optimize_every=4,
            target_update_every=250, gradient_clip=5.0)
        rng = Family3V2LearnerRngDeriver(EXPERIMENT_ID, "masked_ddqn", seed)
        super().__init__(rng_deriver=rng, hyperparameters=settings, model_spec=MODEL_SPEC)
        self.require_execution_device("cuda")

    @staticmethod
    def _validate_decision(decision: LearnerDecision, mask: torch.Tensor) -> None:
        if type(decision) is not LearnerDecision:
            raise ValueError("budget/recourse public decision required")
        decision.require_integrity()
        if not torch.equal(_policy_mask(decision, mask), decision.mask):
            raise ValueError("pilot policies must use exactly the immediate legal-action mask")

    def scores(self, decision: LearnerDecision) -> torch.Tensor:
        self._validate_decision(decision, decision.mask)
        self.require_execution_device("cuda")
        with torch.no_grad():
            scores = self.online_network(decision.state.unsqueeze(0).to(self.device),
                                         decision.candidate_features.unsqueeze(0).to(self.device))
        return scores.squeeze(0).detach().cpu()

    def select_candidate(self, decision: LearnerDecision, *, policy_mask: torch.Tensor,
                         epsilon: float, exploration_rng: random.Random,
                         tie_rng: random.Random) -> str:
        self._validate_decision(decision, policy_mask)
        self.require_execution_device("cuda")
        if type(exploration_rng) is not random.Random or type(tie_rng) is not random.Random or exploration_rng is tie_rng:
            raise ValueError("distinct external exploration and tie RNG streams required")
        if type(epsilon) not in (int, float) or not math.isfinite(epsilon) or not 0 <= epsilon <= 1:
            raise ValueError("finite epsilon in[0,1] required")
        valid = tuple(action for action, bit in zip(ACTIONS, decision.mask.tolist()) if bit)
        if exploration_rng.random() < epsilon:
            return exploration_rng.choice(valid)
        return tie_rng.choice(tuple(greedy_distribution(decision, self.scores(decision))))

    def observe(self, decision: LearnerDecision, *, policy_mask: torch.Tensor,
                action_candidate_id: str, reward: int | float,
                next_decision: LearnerDecision | None, next_policy_mask: torch.Tensor | None,
                done: bool) -> float | None:
        self._validate_decision(decision, policy_mask)
        self.require_execution_device("cuda")
        if type(reward) not in (int, float) or reward not in (0, 1) or (not done and reward != 0):
            raise ValueError("reward must be terminal binary success")
        if next_decision is not None:
            if next_policy_mask is None:
                raise ValueError("live successor requires its legal mask")
            self._validate_decision(next_decision, next_policy_mask)
        # The generic replay surface supports this explicit new model_spec.
        # _optimize dispatch still resolves to the unchanged inherited CUDA DDQN.
        return MaskedDoubleDQN.observe(self, decision, policy_mask=policy_mask,
            action_candidate_id=action_candidate_id, reward=reward,
            next_decision=next_decision, next_policy_mask=next_policy_mask, done=done)
