from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random
import unittest

import torch

from pa_rl.contracts import canonical_hash
from pa_rl.family3_v2_environment import Family3V2Environment
from pa_rl.family3_v2_policy import Family3V2FeatureEncoder
from pa_rl.family3_v2_learning import (
    FAMILY3_V2_DDQN_MODEL_SPEC,
    Family3V2LearnerAdapter,
    Family3V2LearnerDecision,
    Family3V2LearnerRngDeriver,
    Family3V2MaskedDoubleDQN,
    choose_forecast_ablated_rule,
    choose_forecast_rule,
    derive_family3_v2_eval_environment_seed,
    derive_family3_v2_eval_policy_seed,
    choose_random_valid,
    encode_family3_v2_successor,
    family3_v2_tabular_state_id,
    resolve_family3_v2_semantic_slot,
)
from pa_rl.ddqn import DDQNHyperparameters


def _slot(observation, semantic_candidate_id: str) -> int:
    return next(
        index
        for index, row in enumerate(observation.candidates)
        if row.semantic_candidate_id == semantic_candidate_id
    )


def _manual_u64_seed(payload: list[object]) -> int:
    """Independently derive the approved canonical-json SHA-256 seed."""
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big", signed=False)


def _tensor_state_digest(state: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(repr(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def _module_state_digest(module: torch.nn.Module) -> str:
    """Hash full module state plus training flags and parameter gradients."""
    if not isinstance(module, torch.nn.Module):
        raise TypeError("module digest requires torch.nn.Module")
    digest = hashlib.sha256()
    digest.update(b"state_dict")
    digest.update(_tensor_state_digest(module.state_dict()).encode("ascii"))
    for name, nested_module in sorted(module.named_modules(), key=lambda item: item[0]):
        digest.update(b"module")
        digest.update(name.encode("utf-8"))
        digest.update(b"training:1" if nested_module.training else b"training:0")
    for name, parameter in sorted(module.named_parameters(), key=lambda item: item[0]):
        digest.update(b"parameter")
        digest.update(name.encode("utf-8"))
        digest.update(b"requires_grad:1" if parameter.requires_grad else b"requires_grad:0")
        if parameter.grad is None:
            digest.update(b"gradient:none")
        else:
            gradient = parameter.grad.detach().cpu().contiguous()
            digest.update(b"gradient:tensor")
            digest.update(str(gradient.dtype).encode("ascii"))
            digest.update(repr(tuple(gradient.shape)).encode("ascii"))
            digest.update(gradient.numpy().tobytes())
    return digest.hexdigest()


def _nested_state_digest(value: object) -> str:
    """Hash nested optimizer state, including tensor and container metadata."""
    digest = hashlib.sha256()

    def update(item: object) -> None:
        if isinstance(item, torch.Tensor):
            tensor = item.detach().cpu().contiguous()
            digest.update(b"tensor")
            digest.update(str(tensor.dtype).encode("ascii"))
            digest.update(repr(tuple(tensor.shape)).encode("ascii"))
            digest.update(tensor.numpy().tobytes())
        elif isinstance(item, dict):
            digest.update(b"dict")
            for key in sorted(item, key=lambda candidate: (type(candidate).__name__, repr(candidate))):
                update(key)
                update(item[key])
        elif isinstance(item, (tuple, list)):
            digest.update(type(item).__name__.encode("ascii"))
            for nested in item:
                update(nested)
        elif item is None:
            digest.update(b"none")
        elif type(item) is bool:
            digest.update(b"bool:1" if item else b"bool:0")
        elif type(item) is int:
            digest.update(f"int:{item}".encode("ascii"))
        elif type(item) is float:
            digest.update(f"float:{item.hex()}".encode("ascii"))
        elif isinstance(item, str):
            digest.update(b"str")
            digest.update(item.encode("utf-8"))
        else:
            raise TypeError(f"unsupported nested state value: {type(item)!r}")

    update(value)
    return digest.hexdigest()


def _assert_finite_nested(test: unittest.TestCase, value: object) -> None:
    if isinstance(value, torch.Tensor):
        test.assertTrue(bool(torch.isfinite(value).all().item()))
    elif isinstance(value, dict):
        for nested in value.values():
            _assert_finite_nested(test, nested)
    elif isinstance(value, (tuple, list)):
        for nested in value:
            _assert_finite_nested(test, nested)
    elif isinstance(value, float):
        test.assertTrue(math.isfinite(value))


class Family3V2LearningTests(unittest.TestCase):
    def test_rng_namespaces_matched_initialization_and_replay_sampling(self) -> None:
        """Catch unpaired DDQN arms, RNG namespace drift, or nonfinite learning."""
        experiment_id = "increment8_family3_v2_learner_pilot_v0"
        learner_family = "masked_ddqn"
        evaluation_environment_payload = [
            "family3_v2_eval_coord_v0", experiment_id, "environment", 17,
            "i8_f3v2_v5", 0,
        ]
        evaluation_policy_payload = [
            "family3_v2_eval_policy_rng_v0", experiment_id, "policy",
            "masked_ddqn_gamma1", 17, "i8_f3v2_v5", "original", 0, 0,
        ]
        model_init_payload = [
            "family3_v2_learner_rng_v0", experiment_id, learner_family,
            "model_init", 17, [],
        ]
        replay_step_zero_payload = [
            "family3_v2_learner_rng_v0", experiment_id, learner_family,
            "replay_sampling", 17, [0],
        ]
        training_v0_episode_zero_payload = [
            "family3_v2_learner_rng_v0", experiment_id, learner_family,
            "training_environment", 17, ["i8_f3v2_v0", 0],
        ]
        exploration_zero_payload = [
            "family3_v2_learner_rng_v0", experiment_id, learner_family,
            "exploration", 17, [0, 0],
        ]
        golden_vectors = {
            "evaluation_environment": 8668540546105496985,
            "evaluation_policy": 15517394897656733486,
            "model_init": 10667103740917252978,
            "replay_step_zero": 7712939384978999891,
            "training_v0_episode_zero": 2252252023061420188,
            "exploration_zero": 1745296707429322971,
        }
        for name, payload in (
            ("evaluation_environment", evaluation_environment_payload),
            ("evaluation_policy", evaluation_policy_payload),
            ("model_init", model_init_payload),
            ("replay_step_zero", replay_step_zero_payload),
            ("training_v0_episode_zero", training_v0_episode_zero_payload),
            ("exploration_zero", exploration_zero_payload),
        ):
            self.assertEqual(_manual_u64_seed(payload), golden_vectors[name])

        self.assertEqual(
            derive_family3_v2_eval_environment_seed(
                experiment_id=experiment_id,
                evaluation_seed=17,
                graph_id="i8_f3v2_v5",
                episode_ordinal=0,
            ),
            golden_vectors["evaluation_environment"],
        )
        self.assertEqual(
            derive_family3_v2_eval_policy_seed(
                experiment_id=experiment_id,
                method_id="masked_ddqn_gamma1",
                evaluation_seed=17,
                graph_id="i8_f3v2_v5",
                condition="original",
                episode_ordinal=0,
                decision_index=0,
            ),
            golden_vectors["evaluation_policy"],
        )
        self.assertEqual(
            derive_family3_v2_eval_environment_seed(
                experiment_id=experiment_id,
                evaluation_seed=17,
                graph_id="i8_f3v2_v5",
                episode_ordinal=0,
            ),
            derive_family3_v2_eval_environment_seed(
                experiment_id=experiment_id,
                evaluation_seed=17,
                graph_id="i8_f3v2_v5",
                episode_ordinal=0,
            ),
        )
        self.assertNotEqual(
            derive_family3_v2_eval_policy_seed(
                experiment_id=experiment_id,
                method_id="masked_ddqn_gamma0",
                evaluation_seed=17,
                graph_id="i8_f3v2_v5",
                condition="forecast_counterfactual",
                episode_ordinal=0,
                decision_index=0,
            ),
            golden_vectors["evaluation_policy"],
        )

        deriver = Family3V2LearnerRngDeriver(
            experiment_id=experiment_id, learner_family=learner_family, base_seed=17
        )
        self.assertEqual(deriver.model_init_seed(), golden_vectors["model_init"])
        self.assertEqual(
            deriver.replay_sampling_seed(0), golden_vectors["replay_step_zero"]
        )
        self.assertEqual(
            deriver.training_environment_seed("i8_f3v2_v0", 0),
            golden_vectors["training_v0_episode_zero"],
        )
        self.assertEqual(
            deriver.exploration_seed(0, 0), golden_vectors["exploration_zero"]
        )
        self.assertEqual(
            Family3V2LearnerRngDeriver(
                experiment_id=experiment_id,
                learner_family=learner_family,
                base_seed=17,
            ).model_init_seed(),
            deriver.model_init_seed(),
        )
        self.assertEqual(
            Family3V2LearnerRngDeriver(
                experiment_id=experiment_id,
                learner_family=learner_family,
                base_seed=17,
            ).replay_sampling_seed(0),
            deriver.replay_sampling_seed(0),
        )
        self.assertEqual(
            len({
                deriver.model_init_seed(),
                deriver.replay_sampling_seed(0),
                deriver.training_environment_seed("i8_f3v2_v0", 0),
                deriver.exploration_seed(0, 0),
            }),
            4,
        )

        adapter = Family3V2LearnerAdapter()
        environment = Family3V2Environment()
        initial, _ = environment.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
        granted, _, terminated, truncated, _ = environment.step(
            _slot(initial, "request_narrow")
        )
        self.assertFalse(terminated)
        self.assertFalse(truncated)
        initial_decision = adapter.encode(initial)
        granted_decision = adapter.encode(granted)
        forged_current = adapter.encode(initial)
        forged_current.mask[2] = True
        forged_current.candidate_features[2, 2] = 1.0
        forged_successor = adapter.encode(granted)
        forged_successor.mask[0] = True
        forged_successor.candidate_features[0, 2] = 1.0
        integrity_arm = Family3V2MaskedDoubleDQN(
            rng_deriver=deriver,
            hyperparameters=DDQNHyperparameters(
                gamma=0.0, batch_size=2, replay_capacity=4,
                warmup_transitions=2, optimize_every=1, target_update_every=2,
            ),
            model_spec=FAMILY3_V2_DDQN_MODEL_SPEC,
        )
        replay_before = (
            integrity_arm.replay_size,
            integrity_arm._buffer._cursor,
            tuple(integrity_arm._buffer._items),
            integrity_arm._buffer._rng.getstate(),
            integrity_arm.environment_steps,
            integrity_arm.optimizer_steps,
            integrity_arm.last_loss,
            _module_state_digest(integrity_arm.online_network),
            _module_state_digest(integrity_arm.target_network),
            _nested_state_digest(integrity_arm._optimizer.state_dict()),
        )
        with self.assertRaises(ValueError):
            integrity_arm.select_candidate(
                forged_current,
                policy_mask=forged_current.mask,
                epsilon=0.0,
                rng=random.Random(0),
            )
        self.assertEqual(replay_before, (
            integrity_arm.replay_size,
            integrity_arm._buffer._cursor,
            tuple(integrity_arm._buffer._items),
            integrity_arm._buffer._rng.getstate(),
            integrity_arm.environment_steps,
            integrity_arm.optimizer_steps,
            integrity_arm.last_loss,
            _module_state_digest(integrity_arm.online_network),
            _module_state_digest(integrity_arm.target_network),
            _nested_state_digest(integrity_arm._optimizer.state_dict()),
        ))
        with self.assertRaises(ValueError):
            integrity_arm.observe(
                forged_current,
                policy_mask=forged_current.mask,
                action_candidate_id="request_narrow",
                reward=0,
                next_decision=granted_decision,
                next_policy_mask=granted_decision.mask,
                done=False,
            )
        self.assertEqual(replay_before, (
            integrity_arm.replay_size,
            integrity_arm._buffer._cursor,
            tuple(integrity_arm._buffer._items),
            integrity_arm._buffer._rng.getstate(),
            integrity_arm.environment_steps,
            integrity_arm.optimizer_steps,
            integrity_arm.last_loss,
            _module_state_digest(integrity_arm.online_network),
            _module_state_digest(integrity_arm.target_network),
            _nested_state_digest(integrity_arm._optimizer.state_dict()),
        ))
        with self.assertRaises(ValueError):
            integrity_arm.observe(
                initial_decision,
                policy_mask=initial_decision.mask,
                action_candidate_id="request_narrow",
                reward=0,
                next_decision=forged_successor,
                next_policy_mask=forged_successor.mask,
                done=False,
            )
        self.assertEqual(replay_before, (
            integrity_arm.replay_size,
            integrity_arm._buffer._cursor,
            tuple(integrity_arm._buffer._items),
            integrity_arm._buffer._rng.getstate(),
            integrity_arm.environment_steps,
            integrity_arm.optimizer_steps,
            integrity_arm.last_loss,
            _module_state_digest(integrity_arm.online_network),
            _module_state_digest(integrity_arm.target_network),
            _nested_state_digest(integrity_arm._optimizer.state_dict()),
        ))

        for base_seed in (17, 29, 43):
            arm_deriver = Family3V2LearnerRngDeriver(
                experiment_id=experiment_id,
                learner_family=learner_family,
                base_seed=base_seed,
            )
            gamma_zero = DDQNHyperparameters(
                gamma=0.0, batch_size=2, replay_capacity=4,
                warmup_transitions=2, optimize_every=1, target_update_every=2,
            )
            gamma_one = replace(gamma_zero, gamma=1.0)
            gamma_zero_arm = Family3V2MaskedDoubleDQN(
                rng_deriver=arm_deriver,
                hyperparameters=gamma_zero,
                model_spec=FAMILY3_V2_DDQN_MODEL_SPEC,
            )
            gamma_one_arm = Family3V2MaskedDoubleDQN(
                rng_deriver=arm_deriver,
                hyperparameters=gamma_one,
                model_spec=FAMILY3_V2_DDQN_MODEL_SPEC,
            )
            self.assertEqual(
                _module_state_digest(gamma_zero_arm.online_network),
                _module_state_digest(gamma_one_arm.online_network),
            )
            self.assertEqual(
                _module_state_digest(gamma_zero_arm.target_network),
                _module_state_digest(gamma_one_arm.target_network),
            )
            self.assertEqual(
                gamma_zero_arm._optimizer.state_dict(),
                gamma_one_arm._optimizer.state_dict(),
            )
            self.assertEqual(replace(gamma_one_arm.hyperparameters, gamma=0.0), gamma_zero_arm.hyperparameters)
            self.assertIsNot(gamma_zero_arm._buffer, gamma_one_arm._buffer)
            self.assertIsNot(gamma_zero_arm._buffer._rng, gamma_one_arm._buffer._rng)
            with self.assertRaises(ValueError):
                gamma_zero_arm.select_candidate(
                    initial_decision,
                    policy_mask=initial_decision.mask,
                    epsilon=0.0,
                )
            self.assertIn(
                gamma_zero_arm.select_candidate(
                    initial_decision,
                    policy_mask=initial_decision.mask,
                    epsilon=0.0,
                    rng=random.Random(derive_family3_v2_eval_policy_seed(
                        experiment_id=experiment_id,
                        method_id="masked_ddqn_gamma0",
                        evaluation_seed=base_seed,
                        graph_id="i8_f3v2_v5",
                        condition="original",
                        episode_ordinal=0,
                        decision_index=0,
                    )),
                ),
                initial_decision.semantic_candidate_ids,
            )
            for learner in (gamma_zero_arm, gamma_one_arm):
                self.assertIsNone(learner.observe(
                    initial_decision,
                    policy_mask=initial_decision.mask,
                    action_candidate_id="request_narrow",
                    reward=0,
                    next_decision=granted_decision,
                    next_policy_mask=granted_decision.mask,
                    done=False,
                ))
                loss = learner.observe(
                    granted_decision,
                    policy_mask=granted_decision.mask,
                    action_candidate_id="execute_covering",
                    reward=1,
                    next_decision=None,
                    next_policy_mask=None,
                    done=True,
                )
                self.assertIsNotNone(loss)
                self.assertTrue(math.isfinite(loss))
                expected_replay_rng = random.Random(arm_deriver.replay_sampling_seed(0))
                expected_replay_rng.sample((0, 1), 2)
                self.assertEqual(learner._buffer._rng.getstate(), expected_replay_rng.getstate())
                for network in (learner.online_network, learner.target_network):
                    values = network(
                        initial_decision.state.unsqueeze(0),
                        initial_decision.candidate_features.unsqueeze(0),
                    )
                    self.assertTrue(bool(torch.isfinite(values).all().item()))
                    for parameter in network.parameters():
                        self.assertTrue(bool(torch.isfinite(parameter).all().item()))
                for parameter in learner.online_network.parameters():
                    self.assertIsNotNone(parameter.grad)
                    self.assertTrue(bool(torch.isfinite(parameter.grad).all().item()))
                _assert_finite_nested(self, learner._optimizer.state_dict())

    def test_adapter_rules_tabular_key_and_terminal_contract(self) -> None:
        """Catch unsafe padding, stale dispatch, forecast leakage, or private imports."""
        adapter = Family3V2LearnerAdapter()
        environment = Family3V2Environment()
        original, _ = environment.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
        pre_encoded = Family3V2FeatureEncoder().encode(original)
        pre = adapter.encode(original)

        self.assertEqual(FAMILY3_V2_DDQN_MODEL_SPEC.state_dim, 43)
        self.assertEqual(FAMILY3_V2_DDQN_MODEL_SPEC.candidate_dim, 7)
        self.assertEqual(FAMILY3_V2_DDQN_MODEL_SPEC.max_candidates, 7)
        self.assertEqual(tuple(pre_encoded.state_features).__len__(), 37)
        self.assertEqual(tuple(pre.state.shape), (43,))
        self.assertEqual(tuple(pre.candidate_features.shape), (7, 7))
        self.assertEqual(tuple(pre.mask.shape), (7,))
        self.assertEqual(pre.state.dtype, torch.float32)
        self.assertEqual(pre.candidate_features.dtype, torch.float32)
        self.assertEqual(pre.mask.dtype, torch.bool)
        self.assertEqual(pre.state.device.type, "cpu")
        self.assertEqual(pre.candidate_features.device.type, "cpu")
        self.assertEqual(pre.mask.device.type, "cpu")
        self.assertEqual(
            pre.semantic_candidate_ids,
            (
                "request_narrow", "request_broader", "execute_covering",
                "refresh_closed", "disable_active", "deny", "escalate",
            ),
        )
        self.assertEqual(pre.state.tolist()[:37], list(pre_encoded.state_features))
        self.assertEqual(pre.state.tolist()[37:], [0.0] * 6)
        self.assertEqual(
            family3_v2_tabular_state_id(pre),
            "family3_v2_tabular_state_v0:" + canonical_hash(pre_encoded.representation_key()),
        )
        forged = adapter.encode(original)
        forged.mask[2] = True
        forged.candidate_features[2, 2] = 1.0
        with self.assertRaises(ValueError):
            choose_random_valid(forged, random.Random(0))
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(original, forged, "execute_covering")
        non_bit = adapter.encode(original)
        non_bit.candidate_features[2, 2] = 0.5
        with self.assertRaises(ValueError):
            choose_forecast_ablated_rule(non_bit)
        with self.assertRaises(ValueError):
            replace(pre, public_representation_key=pre.public_representation_key[:-1] + (("changed",),))

        self.assertEqual(choose_forecast_ablated_rule(pre), "request_narrow")
        self.assertEqual(choose_forecast_rule(original, pre), "request_narrow")
        self.assertEqual(resolve_family3_v2_semantic_slot(original, pre, "request_narrow"), 0)
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(original, pre, "execute_covering")
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(original, pre, "unknown")
        for seed in range(30):
            self.assertIn(choose_random_valid(pre, random.Random(seed)), {"request_narrow", "request_broader", "deny", "escalate"})

        post_grant, _, terminated, truncated, _ = environment.step(_slot(original, "request_narrow"))
        self.assertFalse(terminated)
        self.assertFalse(truncated)
        post_encoded = Family3V2FeatureEncoder().encode(post_grant)
        post = adapter.encode(post_grant)
        self.assertEqual(len(post_encoded.state_features), 43)
        self.assertEqual(post.state.tolist(), list(post_encoded.state_features))
        self.assertEqual(choose_forecast_ablated_rule(post), "execute_covering")
        self.assertEqual(choose_forecast_rule(post_grant, post), "execute_covering")
        self.assertEqual(resolve_family3_v2_semantic_slot(post_grant, post, "execute_covering"), 2)
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(post_grant, post, "request_narrow")
        with self.assertRaises(ValueError):
            choose_forecast_rule(post_grant, pre)



        counterfactual_environment = Family3V2Environment()
        counterfactual, _ = counterfactual_environment.reset(
            "i8_f3v2_v4", root_seed=7, episode_ordinal=0, forecast_counterfactual=True
        )
        counterfactual_decision = adapter.encode(counterfactual)
        self.assertEqual(choose_forecast_ablated_rule(counterfactual_decision), "request_narrow")
        self.assertEqual(choose_forecast_rule(counterfactual, counterfactual_decision), "request_broader")
        tied = replace(
            original,
            forecast_exact_probability=Fraction(1, 2),
            forecast_broader_probability=Fraction(1, 2),
        )
        with self.assertRaises(ValueError):
            choose_forecast_rule(tied, pre)

        terminal_environment = Family3V2Environment()
        terminal, _ = terminal_environment.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
        terminal, _, terminal_flag, truncation_flag, _ = terminal_environment.step(_slot(terminal, "execute_covering"))
        self.assertTrue(terminal_flag)
        self.assertFalse(truncation_flag)
        self.assertEqual(terminal.candidates, ())
        self.assertIsNone(
            encode_family3_v2_successor(
                adapter, terminal, terminated=terminal_flag, truncated=truncation_flag
            )
        )

        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(42), torch.zeros((7, 7)), torch.ones(7, dtype=torch.bool),
                pre.semantic_candidate_ids, pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(43), torch.zeros((6, 7)), torch.ones(6, dtype=torch.bool),
                pre.semantic_candidate_ids[:6], pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(43), torch.zeros((7, 6)), torch.ones(7, dtype=torch.bool),
                pre.semantic_candidate_ids, pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.tensor([float("nan")] + [0.0] * 42), torch.zeros((7, 7)),
                torch.ones(7, dtype=torch.bool), pre.semantic_candidate_ids, pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(43), torch.zeros((7, 7)), torch.zeros(7, dtype=torch.bool),
                pre.semantic_candidate_ids, pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(43), torch.zeros((7, 7)), torch.ones(7, dtype=torch.bool),
                ("request_broader", "request_narrow", *pre.semantic_candidate_ids[2:]),
                pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(43), torch.zeros((7, 7)), torch.ones(7, dtype=torch.bool),
                ("request_narrow", "request_narrow", *pre.semantic_candidate_ids[2:]),
                pre.public_representation_key,
            )
        disagreeing_features = pre.candidate_features.clone()
        disagreeing_features[2, 2] = 1.0
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                pre.state, disagreeing_features, pre.mask, pre.semantic_candidate_ids,
                pre.public_representation_key,
            )

        source = Path(__import__("pa_rl.family3_v2_learning", fromlist=["__file__"]).__file__)
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        forbidden_modules = {
            "family3_v2_exact_solver", "family3_v2_exact_reference", "family3_v2_audit",
            "family3_v2_certificate", "family3_v2_certificates",
        }
        forbidden_names = {"Family3V2EnvironmentInfo"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertFalse(
                    node.module and any(part in forbidden_modules for part in node.module.split("."))
                )
                self.assertFalse(
                    node.module and node.module.endswith("family3_v2_environment")
                    and any(alias.name in forbidden_names for alias in node.names)
                )
            elif isinstance(node, ast.Import):
                self.assertFalse(
                    any(any(part in forbidden_modules for part in alias.name.split(".")) for alias in node.names)
                )

        relative_environment_escape = ast.parse(
            "from .family3_v2_environment import Family3V2EnvironmentInfo"
        ).body[0]
        self.assertIsInstance(relative_environment_escape, ast.ImportFrom)
        self.assertTrue(relative_environment_escape.module.endswith("family3_v2_environment"))
        self.assertIn("Family3V2EnvironmentInfo", {alias.name for alias in relative_environment_escape.names})


if __name__ == "__main__":
    unittest.main()
