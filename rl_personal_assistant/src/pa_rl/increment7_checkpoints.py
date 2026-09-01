"""Evaluation-only learner checkpoints for the Increment-7 pilot."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import torch

from .baselines import TabularQLearner
from .ddqn import DDQNHyperparameters, DDQNModelSpec, MaskedDoubleDQN


_SCHEMA_VERSION = "increment7_evaluation_checkpoint_v1"
_HEX = frozenset("0123456789abcdef")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _update_digest(digest: Any, value: object) -> None:
    """Hash nested primitive/tensor state with explicit type boundaries."""

    if isinstance(value, torch.Tensor):
        tensor = value.detach().to(device="cpu").contiguous()
        digest.update(b"tensor\0")
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(json.dumps(list(tensor.shape), separators=(",", ":")).encode("ascii"))
        digest.update(b"\0")
        digest.update(tensor.numpy().tobytes(order="C"))
        return
    if isinstance(value, Mapping):
        digest.update(b"mapping\0")
        for key in sorted(value, key=lambda item: (type(item).__name__, repr(item))):
            _update_digest(digest, key)
            _update_digest(digest, value[key])
        digest.update(b"end_mapping\0")
        return
    if isinstance(value, (tuple, list)):
        digest.update(b"tuple\0" if isinstance(value, tuple) else b"list\0")
        for item in value:
            _update_digest(digest, item)
        digest.update(b"end_sequence\0")
        return
    if is_dataclass(value) and not isinstance(value, type):
        _update_digest(
            digest,
            {field.name: getattr(value, field.name) for field in fields(value)},
        )
        return
    if value is None:
        digest.update(b"none\0")
        return
    if type(value) in {bool, int, float, str}:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("fingerprinted floats must be finite")
        digest.update(type(value).__name__.encode("ascii"))
        digest.update(b"\0")
        digest.update(json.dumps(value, ensure_ascii=True).encode("ascii"))
        digest.update(b"\0")
        return
    raise ValueError(f"unsupported fingerprint value: {type(value).__name__}")


def _fingerprint(value: object) -> str:
    digest = hashlib.sha256()
    _update_digest(digest, value)
    return digest.hexdigest()


def tabular_fingerprint(tabular: TabularQLearner) -> str:
    """Return a canonical digest of the complete public Q table."""

    if not isinstance(tabular, TabularQLearner):
        raise ValueError("tabular must be TabularQLearner")
    rows = tuple(
        (state_id, candidate_id, float(value))
        for (state_id, candidate_id), value in sorted(tabular.q_values.items())
    )
    return _fingerprint(
        {"alpha": tabular.alpha, "gamma": tabular.gamma, "q_rows": rows}
    )


def ddqn_model_fingerprint(ddqn: MaskedDoubleDQN) -> str:
    """Digest the evaluation model contract, online weights, and counters."""

    if not isinstance(ddqn, MaskedDoubleDQN):
        raise ValueError("ddqn must be MaskedDoubleDQN")
    return _fingerprint(
        {
            "model_spec": asdict(ddqn.model_spec),
            "hyperparameters": asdict(ddqn.hyperparameters),
            "online_state": dict(ddqn.online_network.state_dict()),
            "environment_steps": ddqn.environment_steps,
            "optimizer_steps": ddqn.optimizer_steps,
        }
    )


def evaluation_learner_fingerprint(
    tabular: TabularQLearner, ddqn: MaskedDoubleDQN
) -> str:
    """Digest every mutable learner surface that evaluation must preserve."""

    if not isinstance(tabular, TabularQLearner) or not isinstance(
        ddqn, MaskedDoubleDQN
    ):
        raise ValueError("evaluation learners have invalid types")
    buffer = ddqn._buffer  # Package-private audit of read-only evaluation state.
    replay_items = tuple(
        {field.name: getattr(item, field.name) for field in fields(item)}
        for item in buffer._items
    )
    return _fingerprint(
        {
            "tabular": {
                "alpha": tabular.alpha,
                "gamma": tabular.gamma,
                "q_rows": tuple(
                    (state_id, candidate_id, float(value))
                    for (state_id, candidate_id), value in sorted(
                        tabular.q_values.items()
                    )
                ),
            },
            "ddqn": {
                "model_spec": asdict(ddqn.model_spec),
                "hyperparameters": asdict(ddqn.hyperparameters),
                "online_state": dict(ddqn.online_network.state_dict()),
                "target_state": dict(ddqn.target_network.state_dict()),
                "optimizer_state": ddqn._optimizer.state_dict(),
                "environment_steps": ddqn.environment_steps,
                "optimizer_steps": ddqn.optimizer_steps,
                "last_loss": ddqn.last_loss,
                "replay_capacity": buffer._capacity,
                "replay_cursor": buffer._cursor,
                "replay_items": replay_items,
                "replay_size": ddqn.replay_size,
                "rng_state": ddqn._rng.getstate(),
            },
        }
    )


@dataclass(frozen=True, slots=True)
class EvaluationCheckpointInfo:
    schema_version: str
    seed: int
    checkpoint_hash: str
    tabular_entry_count: int
    ddqn_fingerprint: str
    optimizer_steps: int
    environment_steps: int

    def __post_init__(self) -> None:
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError("unsupported evaluation checkpoint schema")
        if type(self.seed) is not int:
            raise ValueError("checkpoint seed must be an exact integer")
        for name in ("tabular_entry_count", "optimizer_steps", "environment_steps"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative exact integer")
        for name in ("checkpoint_hash", "ddqn_fingerprint"):
            value = getattr(self, name)
            if (
                type(value) is not str
                or len(value) != 64
                or not set(value).issubset(_HEX)
            ):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")

    def as_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "checkpoint_hash": self.checkpoint_hash,
            "tabular_entry_count": self.tabular_entry_count,
            "ddqn_fingerprint": self.ddqn_fingerprint,
            "optimizer_steps": self.optimizer_steps,
            "environment_steps": self.environment_steps,
        }


def _checkpoint_payload(
    *, seed: int, tabular: TabularQLearner, ddqn: MaskedDoubleDQN
) -> dict[str, object]:
    if type(seed) is not int:
        raise ValueError("seed must be an exact integer")
    if not isinstance(tabular, TabularQLearner) or not isinstance(
        ddqn, MaskedDoubleDQN
    ):
        raise ValueError("checkpoint learners have invalid types")
    q_rows = tuple(
        (state_id, candidate_id, float(value))
        for (state_id, candidate_id), value in sorted(tabular.q_values.items())
    )
    return {
        "schema_version": _SCHEMA_VERSION,
        "seed": seed,
        "tabular": {
            "alpha": tabular.alpha,
            "gamma": tabular.gamma,
            "q_rows": q_rows,
            "fingerprint": tabular_fingerprint(tabular),
        },
        "ddqn": {
            "model_spec": asdict(ddqn.model_spec),
            "hyperparameters": asdict(ddqn.hyperparameters),
            "online_state": {
                name: tensor.detach().to(device="cpu").clone()
                for name, tensor in ddqn.online_network.state_dict().items()
            },
            "environment_steps": ddqn.environment_steps,
            "optimizer_steps": ddqn.optimizer_steps,
            "fingerprint": ddqn_model_fingerprint(ddqn),
        },
    }


def save_evaluation_checkpoint(
    path: str | Path,
    *,
    seed: int,
    tabular: TabularQLearner,
    ddqn: MaskedDoubleDQN,
) -> EvaluationCheckpointInfo:
    """Atomically save a completed seed for read-only validation/test use."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    payload = _checkpoint_payload(seed=seed, tabular=tabular, ddqn=ddqn)
    torch.save(payload, temporary)
    temporary.replace(target)
    ddqn_payload = payload["ddqn"]
    assert isinstance(ddqn_payload, dict)
    tabular_payload = payload["tabular"]
    assert isinstance(tabular_payload, dict)
    return EvaluationCheckpointInfo(
        schema_version=_SCHEMA_VERSION,
        seed=seed,
        checkpoint_hash=_sha256_file(target),
        tabular_entry_count=len(tabular.q_values),
        ddqn_fingerprint=str(ddqn_payload["fingerprint"]),
        optimizer_steps=ddqn.optimizer_steps,
        environment_steps=ddqn.environment_steps,
    )


def _exact_mapping(value: object, keys: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"{name} has an invalid schema")
    return value


def load_evaluation_checkpoint(
    path: str | Path,
) -> tuple[TabularQLearner, MaskedDoubleDQN, EvaluationCheckpointInfo]:
    """Load and verify an evaluation-only checkpoint on CPU."""

    source = Path(path)
    payload = torch.load(source, map_location="cpu", weights_only=True)
    root = _exact_mapping(
        payload, {"schema_version", "seed", "tabular", "ddqn"}, "checkpoint"
    )
    if root["schema_version"] != _SCHEMA_VERSION or type(root["seed"]) is not int:
        raise ValueError("checkpoint identity is invalid")
    seed = root["seed"]
    tabular_payload = _exact_mapping(
        root["tabular"], {"alpha", "gamma", "q_rows", "fingerprint"}, "tabular"
    )
    ddqn_payload = _exact_mapping(
        root["ddqn"],
        {
            "model_spec",
            "hyperparameters",
            "online_state",
            "environment_steps",
            "optimizer_steps",
            "fingerprint",
        },
        "ddqn",
    )

    tabular = TabularQLearner(
        alpha=tabular_payload["alpha"], gamma=tabular_payload["gamma"]
    )
    q_rows = tabular_payload["q_rows"]
    if not isinstance(q_rows, (tuple, list)):
        raise ValueError("tabular q_rows must be a sequence")
    for row in q_rows:
        if not isinstance(row, (tuple, list)) or len(row) != 3:
            raise ValueError("tabular q row is invalid")
        tabular.set_value(row[0], row[1], row[2])
    if len(tabular.q_values) != len(q_rows):
        raise ValueError("tabular q rows must be unique")
    if tabular_fingerprint(tabular) != tabular_payload["fingerprint"]:
        raise ValueError("tabular checkpoint fingerprint mismatch")

    model_mapping = _exact_mapping(
        ddqn_payload["model_spec"],
        {"state_dim", "candidate_dim", "max_candidates"},
        "model_spec",
    )
    hyper_mapping = _exact_mapping(
        ddqn_payload["hyperparameters"],
        {
            "gamma",
            "learning_rate",
            "batch_size",
            "replay_capacity",
            "warmup_transitions",
            "optimize_every",
            "target_update_every",
            "gradient_clip",
        },
        "hyperparameters",
    )
    ddqn = MaskedDoubleDQN(
        seed=seed,
        model_spec=DDQNModelSpec(**dict(model_mapping)),
        hyperparameters=DDQNHyperparameters(**dict(hyper_mapping)),
    )
    online_state = ddqn_payload["online_state"]
    if not isinstance(online_state, Mapping):
        raise ValueError("online_state must be a mapping")
    ddqn.online_network.load_state_dict(dict(online_state), strict=True)
    ddqn.target_network.load_state_dict(ddqn.online_network.state_dict())
    for name in ("environment_steps", "optimizer_steps"):
        value = ddqn_payload[name]
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative exact integer")
        setattr(ddqn, name, value)
    if ddqn_model_fingerprint(ddqn) != ddqn_payload["fingerprint"]:
        raise ValueError("DDQN checkpoint fingerprint mismatch")

    info = EvaluationCheckpointInfo(
        schema_version=_SCHEMA_VERSION,
        seed=seed,
        checkpoint_hash=_sha256_file(source),
        tabular_entry_count=len(tabular.q_values),
        ddqn_fingerprint=str(ddqn_payload["fingerprint"]),
        optimizer_steps=ddqn.optimizer_steps,
        environment_steps=ddqn.environment_steps,
    )
    return tabular, ddqn, info


__all__ = [
    "EvaluationCheckpointInfo",
    "ddqn_model_fingerprint",
    "evaluation_learner_fingerprint",
    "load_evaluation_checkpoint",
    "save_evaluation_checkpoint",
    "tabular_fingerprint",
]
