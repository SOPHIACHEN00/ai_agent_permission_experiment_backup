# Task 1 fix round 2 review package

Fix base is the state captured in task-1-fix-1-review-package.md; open findings are in the ledger and review message.

## Post-fix manifest
- docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json — 11338 bytes — c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef
- src/pa_rl/family3_v2_pilot_criteria.py — 8984 bytes — a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143
- tests/test_family3_v2_learner_pilot.py — 6332 bytes — 18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea
- docs/CONTINUATION_CHECKPOINT.md — 64948 bytes — 5ead68f023ee85613c6f0a5fe6a9a91d21217d02fc0273531ae53bf710ff9613

## Current file: docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json
```
{
  "schema_version": "family3_v2_learner_source_baseline_v0",
  "created_at_utc": "2026-09-21T00:56:07Z",
  "certified_suite": {"version": "increment8_family3_v2_forecast_scope_reservation_v0", "suite_hash": "98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c"},
  "approved_specs": [
    {"relative_path":"docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md","sha256":"f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9","byte_size":38149},
    {"relative_path":"docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md","sha256":"0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20","byte_size":35818}
  ],
  "certified_preflight": {
    "result_root": "results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight",
    "final_verdict": "CERTIFIED_PASS",
    "artifacts": [
      {"relative_path":"run_config.json","sha256":"b4384b248d9973a730d4ee1f24cc00f1388fd39c0945b6180d7ac4d70c31fabb","byte_size":3090},
      {"relative_path":"final_verdict.json","sha256":"ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552","byte_size":329},
      {"relative_path":"frozen_v0_v1_baseline.json","sha256":"d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055","byte_size":15208},
      {"relative_path":"suite_manifest.json","sha256":"9d2317cde93e4d2b48bd71df5787afed238e492c06d8bf7f09475ce107e6bcc2","byte_size":11976}
    ],
    "certificate_entries": [
      {"relative_path":"graphs/i8_f3v2_v0/exact_certificate.json","sha256":"299283145186e6db32eff1ef2842c8e32c1b9d2e81312c137932b0ef03aae0ea","byte_size":940},{"relative_path":"graphs/i8_f3v2_v1/exact_certificate.json","sha256":"5f3186077290241b8382e22d2b2a666c1041a533668b9fc90974a70c702eea50","byte_size":940},{"relative_path":"graphs/i8_f3v2_v2/exact_certificate.json","sha256":"be82bef9fcfe02c59da9213064ce26281034a1b9284f5da84f34e0bebf6cd059","byte_size":577},{"relative_path":"graphs/i8_f3v2_v3/exact_certificate.json","sha256":"023e73690dd5a56bac00e17cb89adff1e540436f1f57e2b645ded71142782c21","byte_size":577},{"relative_path":"graphs/i8_f3v2_v4/exact_certificate.json","sha256":"da6052f64da9d0450262fedf97258e3d8ae80baccd82dd8ec8dd5c4c031cad2c","byte_size":577},{"relative_path":"graphs/i8_f3v2_v5/exact_certificate.json","sha256":"e6ec8f866e17df45f1897501bd47ccb9c6041246fc493789148e7b9aeb8bde56","byte_size":577},{"relative_path":"graphs/i8_f3v2_v6/exact_certificate.json","sha256":"965efcb11dbc5534c0de1fd624022c701ea44c66ef5e426aebf8084b77a1aa47","byte_size":577},{"relative_path":"graphs/i8_f3v2_v7/exact_certificate.json","sha256":"86afb9601da7e13af63c4baaf818b6a731fdab6014d41dce8e8bb40a7dfe6378","byte_size":577},{"relative_path":"graphs/i8_f3v2_v8/exact_certificate.json","sha256":"e3f63dee4b0bb42e5f87b6593df191a8dcfecac50f8fc750dcb84ed433212b5c","byte_size":577},{"relative_path":"graphs/i8_f3v2_v9/exact_certificate.json","sha256":"320974f18bc2f8bcd11bfd75d017dd33595410f1d9052e09ff54b118b6208964","byte_size":577},
      {"relative_path":"counterfactuals/i8_f3v2_v0/exact_certificate.json","sha256":"88f0f4965f4ae3d9a3c7f6991271a4712f288529833d9b6f0f213a0719cb6fea","byte_size":1719},{"relative_path":"counterfactuals/i8_f3v2_v1/exact_certificate.json","sha256":"fdcd0d77f45e0d3b1ec9f17d11dc418cc5a18888144e06173340b0dec4cb4cfe","byte_size":1723},{"relative_path":"counterfactuals/i8_f3v2_v2/exact_certificate.json","sha256":"9128e5be0462f05dfbc7eafb752c911b9bd0a51cc1282b5261dc5ec83dc7b293","byte_size":1730},{"relative_path":"counterfactuals/i8_f3v2_v3/exact_certificate.json","sha256":"83c494e295ad6af719e6203534a9d465a348c67b4eaa7f611faae81361ee4a18","byte_size":1724},{"relative_path":"counterfactuals/i8_f3v2_v4/exact_certificate.json","sha256":"f3a72b72544bc5b5081e68f87f430a31c9cc37011df0d1d5105a363d0c2cdbe7","byte_size":1728},{"relative_path":"counterfactuals/i8_f3v2_v5/exact_certificate.json","sha256":"fa42d291f5fda0288c3abbbe0a145783e298336dc68d0c07bcec47f9527e6c89","byte_size":1726},{"relative_path":"counterfactuals/i8_f3v2_v6/exact_certificate.json","sha256":"785abb5241509d10422a24c7079f6e3adbbb5f1252dcb3c8e434c2a8c6aa85e5","byte_size":1726},{"relative_path":"counterfactuals/i8_f3v2_v7/exact_certificate.json","sha256":"ef6f1f9eaa1a0f2f928982c31e9fe159a793b1987777b843b1549e6057b95f36","byte_size":1726},{"relative_path":"counterfactuals/i8_f3v2_v8/exact_certificate.json","sha256":"e8874ab48c8a412d3b82be74e5a8c4ead148396dfdc153b230a49bb3cfbbaf59","byte_size":1726},{"relative_path":"counterfactuals/i8_f3v2_v9/exact_certificate.json","sha256":"60d3b90fb43841d98af04eff152844ef399661a81c6fa2f494d5763c694d4367","byte_size":1728}
    ],
    "cache_entries": [
      {"relative_path":"graphs/i8_f3v2_v0/value_cache.sqlite3","sha256":"f96fffb068197ad55ac92d09c9c016534152eaa21b42a1aa7e6685074f144f78","byte_size":16384},{"relative_path":"graphs/i8_f3v2_v1/value_cache.sqlite3","sha256":"5ec7d8fa3a697b50a2b90d5eed29ee16603181171d72f814960ec416e8b3a54f","byte_size":16384},{"relative_path":"graphs/i8_f3v2_v2/value_cache.sqlite3","sha256":"582756a383aa48445c728f317724962deb06fe28ba291b5b14cc7e0936dd56f4","byte_size":16384},{"relative_path":"graphs/i8_f3v2_v3/value_cache.sqlite3","sha256":"50e9fa528382367b35d54e7e5f2f835b18880a1c8f1e30b50365a0c86bc3b25d","byte_size":16384},{"relative_path":"graphs/i8_f3v2_v4/value_cache.sqlite3","sha256":"e2ce2688e3ad131b3b1094a3d25b75884ed678f46bee77084f6831a1ec8fa682","byte_size":16384},{"relative_path":"graphs/i8_f3v2_v5/value_cache.sqlite3","sha256":"64f9719a0b2c0d4e85258ea027d4ce8d7da555b72ffeb7fcc36834e409497858","byte_size":16384},{"relative_path":"graphs/i8_f3v2_v6/value_cache.sqlite3","sha256":"d41766931a0b4e341d698632644ab0ddca3dbe59d36462b12e0ff6d345598e3a","byte_size":16384},{"relative_path":"graphs/i8_f3v2_v7/value_cache.sqlite3","sha256":"bd2a5b33ea8f512a11e227b68fa80d6cc4353f152107bb7bfd79e57efe74e7d2","byte_size":16384},{"relative_path":"graphs/i8_f3v2_v8/value_cache.sqlite3","sha256":"b7ab806bc776548d795a4d68fc6a2859ab97a02fd96abb95299f152e2c032354","byte_size":16384},{"relative_path":"graphs/i8_f3v2_v9/value_cache.sqlite3","sha256":"bf8f856299329aafb09708f2ec0ba4edf549c7d8e43d44bb72f3ade8ca9f2037","byte_size":16384},
      {"relative_path":"counterfactuals/i8_f3v2_v0/value_cache.sqlite3","sha256":"8b5ebf888e4b62a7d2c804ded61b21be288c13b5a7a45d0b28957f4b49f55c6d","byte_size":16384},{"relative_path":"counterfactuals/i8_f3v2_v1/value_cache.sqlite3","sha256":"eb4096a80ae29023fcbfc229bab3e960bb2ac4eb3fff01998a358fc4f0b30a95","byte_size":16384},{"relative_path":"counterfactuals/i8_f3v2_v2/value_cache.sqlite3","sha256":"adf4140878742062c93d3c61a464f5e36edf8547eaccda4281f022aa52a1409e","byte_size":16384},{"relative_path":"counterfactuals/i8_f3v2_v3/value_cache.sqlite3","sha256":"2da327b5f1296035fad3e11549885229cc95d9bd02bd3ddf6683d304ee8f2702","byte_size":16384},{"relative_path":"counterfactuals/i8_f3v2_v4/value_cache.sqlite3","sha256":"cf7accd7d2670c7ff6883eb0f9d1f060601528aeeda3af8fb2254a2196b4c428","byte_size":16384},{"relative_path":"counterfactuals/i8_f3v2_v5/value_cache.sqlite3","sha256":"2c51908071291fad339c554bd443eec92417f167ff03d00fb57a934ecf3deeac","byte_size":16384},{"relative_path":"counterfactuals/i8_f3v2_v6/value_cache.sqlite3","sha256":"2c087317c774eb867f25034e16969b419d71957490140d6088ad101822bf8220","byte_size":16384},{"relative_path":"counterfactuals/i8_f3v2_v7/value_cache.sqlite3","sha256":"6f2fe50f9f354c79682c2e6082ef8a805c59eafdb075ef143c16fd7d4bd4e4ce","byte_size":16384},{"relative_path":"counterfactuals/i8_f3v2_v8/value_cache.sqlite3","sha256":"fddd8829ecb5d75ec17b271a62a6ff8035583caa1f143eef4b7146ed05a731ad","byte_size":16384},{"relative_path":"counterfactuals/i8_f3v2_v9/value_cache.sqlite3","sha256":"8c36647470d50dfcb8e0de4c7087e856a74f825cdfa882082c1c636e06b754ea","byte_size":16384}
    ]
  },
  "certified_source_files": [
    {"relative_path":"src/pa_rl/authorization.py","sha256":"8d3d060421e2bff320ceb304095f34ac28110a23f0e33bebc66e833189900fd9","byte_size":32604},
    {"relative_path":"src/pa_rl/config.py","sha256":"1dead76ebaaba8230a3c51ef8b79c981cc7467488807d59c44da0a82c52dbb3e","byte_size":845},
    {"relative_path":"src/pa_rl/contracts.py","sha256":"a01b1b5ced492c450e3e0eb3542d1855a0918bf8f0770816399e3c92320d6ee3","byte_size":10282},
    {"relative_path":"src/pa_rl/effects.py","sha256":"6c81c05d99b0cb084e53a81f20c3d8b08b9c4d5d50cfed4bb84d6688c75cdf94","byte_size":10503},
    {"relative_path":"src/pa_rl/execution.py","sha256":"e2dc444b75ff85aee0436289d94b5bdc2c8fe8f28e19fd7435b1081b126079e6","byte_size":22176},
    {"relative_path":"src/pa_rl/family3_v2_artifacts.py","sha256":"47ddb25684244822e596fecfa950336307da18dafc3fe0ae3f00f177d3148a0d","byte_size":43038},
    {"relative_path":"src/pa_rl/family3_v2_audit.py","sha256":"92ef0f7794536581a5fbb51719ea8b4a79436b61b4b0bc61eb3632a020b45921","byte_size":64280},
    {"relative_path":"src/pa_rl/family3_v2_authority.py","sha256":"0aca9e16347a8e0c128b0dcaf632a3223556a6c9d79adbf4c9fe776fe030588d","byte_size":6234},
    {"relative_path":"src/pa_rl/family3_v2_contracts.py","sha256":"c6ceb984c319a7a8fa407cb5abe730fb75c31ba7513c36346c9695302985eeeb","byte_size":4376},
    {"relative_path":"src/pa_rl/family3_v2_environment.py","sha256":"20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8","byte_size":15947},
    {"relative_path":"src/pa_rl/family3_v2_exact_reference.py","sha256":"7a1c12fff617b678e8cac750bb222157f83a914e5df44fd3f1aadf84a7309575","byte_size":12684},
    {"relative_path":"src/pa_rl/family3_v2_exact_solver.py","sha256":"b69833fc440a654ca33cabe373ddc2ff55c1e90d1f7016c19b575974f01212d0","byte_size":37078},
    {"relative_path":"src/pa_rl/family3_v2_model.py","sha256":"f7848d2ac0343d2ffb79b24d584a81da1fa5daa51c7f97d35134948d90020f2c","byte_size":23904},
    {"relative_path":"src/pa_rl/family3_v2_outcome.py","sha256":"b4aaff4856194966823380dcc1b34af3cecee3c2da0ed5b0fa169c7f712318d6","byte_size":5949},
    {"relative_path":"src/pa_rl/family3_v2_policy.py","sha256":"2ebbb936567c0ca65ec616cc91e4e5c708d939394c7f41b31d00c0c8a2f4e0a6","byte_size":10368},
    {"relative_path":"src/pa_rl/family3_v2_preflight.py","sha256":"17439cbdedb1846af71bb032b0e4a72f7d1dea1e38d3b3257c0cf6948f4abbbe","byte_size":63021},
    {"relative_path":"src/pa_rl/family3_v2_rng.py","sha256":"bf0f9cb388c883d20c77848c0cb8e94e73da9d0f8769395440949fbeffc46530","byte_size":4837},
    {"relative_path":"src/pa_rl/family3_v2_suite.py","sha256":"b9def623bd0eb025754c458a4289d8a7c96e18c0aaae5aa586a521d9dd0e8d54","byte_size":16679},
    {"relative_path":"src/pa_rl/scenarios.py","sha256":"fc76020e39fb24fbb6da89d380da62f3fd1dbcca3d4473988b1f1c0bc2f352c6","byte_size":11712},
    {"relative_path":"src/pa_rl/scope_matching.py","sha256":"cbdff3449287927ad6a9739e14db6dcbeee3eb5444c97f15bb6192f0d354972c","byte_size":3339}
  ],
  "additional_learner_dependencies": [{"relative_path":"src/pa_rl/ddqn.py","sha256":"8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1","byte_size":18033},{"relative_path":"src/pa_rl/baselines.py","sha256":"6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69","byte_size":4350}],
  "pilot_config": {"relative_path":"configs/evaluation/family3_v2_learner_pilot_v0.json","sha256":"7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2","byte_size":8377}
}

```

## Current file: src/pa_rl/family3_v2_pilot_criteria.py
```
"""Strict frozen configuration and certified-dependency boundary for the v2 pilot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


_CONFIG_CANONICAL_SHA256 = "27ecd5b5614c1542a971265b8f3ca657a82c434cdcd3fd5e17df9a1c0c07596d"
_TOP_LEVEL = (
    "schema_version", "experiment_id", "certified_environment", "split", "methods",
    "training", "hyperparameters", "evaluation", "hard_zero_counts",
    "phase_completion_only_counts", "validation_gate", "result_classification",
    "external_services",
)
_BASELINE_TOP_LEVEL = {"schema_version", "created_at_utc", "certified_suite", "approved_specs", "certified_preflight", "certified_source_files", "additional_learner_dependencies", "pilot_config"}
_CERTIFICATE_PATHS = tuple([f"graphs/i8_f3v2_v{i}/exact_certificate.json" for i in range(10)] + [f"counterfactuals/i8_f3v2_v{i}/exact_certificate.json" for i in range(10)])
_CACHE_PATHS = tuple([f"graphs/i8_f3v2_v{i}/value_cache.sqlite3" for i in range(10)] + [f"counterfactuals/i8_f3v2_v{i}/value_cache.sqlite3" for i in range(10)])
_SPEC_PATHS = ("docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md", "docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md")
_SOURCE_ENTRIES_SHA256 = "3d51cc6f50bbfadde77e0adc3e7d05189e19eb94f3ccaab1196c444ae739044d"
_LEARNER_DEPENDENCIES_SHA256 = "f39def7a36b90e4f2abb32d43e0008d40433ca30336ed1c266c80e2dcae8ca22"
_PILOT_CONFIG_ENTRY_SHA256 = "6d3c085d5a7c6b2cc1aed55f1755931728b930381d65891b78de4226715a86e3"
_PREFLIGHT_ARTIFACTS_SHA256 = "84ce6746c795f5c00869140a9e6c7d4a379e0b08c83fff3621c4aed02c602287"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class Family3V2PilotConfig:
    schema_version: str
    experiment_id: str
    certified_environment: Mapping[str, object]
    split: Mapping[str, object]
    methods: tuple[Mapping[str, object], ...]
    training: Mapping[str, object]
    hyperparameters: Mapping[str, object]
    evaluation: Mapping[str, object]
    hard_zero_counts: tuple[str, ...]
    phase_completion_only_counts: tuple[str, ...]
    validation_gate: Mapping[str, object]
    result_classification: Mapping[str, object]
    external_services: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class CertifiedDependencyVerification:
    passed: bool
    mismatches: tuple[str, ...]
    suite_hash: str
    approved_spec_hashes: tuple[str, ...]


def load_family3_v2_pilot_config(path: str | Path) -> Family3V2PilotConfig:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("pilot config must be readable JSON") from error
    if not isinstance(raw, dict) or tuple(raw) != _TOP_LEVEL:
        raise ValueError("pilot config has missing, unknown, or noncanonical fields")
    if hashlib.sha256(_canonical(raw)).hexdigest() != _CONFIG_CANONICAL_SHA256:
        raise ValueError("pilot config differs from the approved frozen contract")
    frozen = _freeze(raw)
    assert isinstance(frozen, Mapping)
    return Family3V2PilotConfig(
        schema_version=frozen["schema_version"], experiment_id=frozen["experiment_id"],
        certified_environment=frozen["certified_environment"], split=frozen["split"],
        methods=frozen["methods"], training=frozen["training"],
        hyperparameters=frozen["hyperparameters"], evaluation=frozen["evaluation"],
        hard_zero_counts=frozen["hard_zero_counts"],
        phase_completion_only_counts=frozen["phase_completion_only_counts"],
        validation_gate=frozen["validation_gate"], result_classification=frozen["result_classification"],
        external_services=frozen["external_services"],
    )


def verify_certified_dependency_baseline(baseline_path: str | Path) -> CertifiedDependencyVerification:
    try:
        baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("dependency baseline must be readable JSON") from error
    if not isinstance(baseline, dict) or set(baseline) != _BASELINE_TOP_LEVEL or baseline.get("schema_version") != "family3_v2_learner_source_baseline_v0":
        raise ValueError("dependency baseline schema is invalid")
    root = Path(__file__).resolve().parents[2]
    mismatches: list[str] = []

    def verify(entries: object, base: Path = root) -> None:
        if not isinstance(entries, list):
            raise ValueError("baseline file list is invalid")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"relative_path", "sha256", "byte_size"}:
                raise ValueError("baseline entry is invalid")
            relative, expected_hash, expected_size = entry.get("relative_path"), entry.get("sha256"), entry.get("byte_size")
            if type(relative) is not str or type(expected_hash) is not str or type(expected_size) is not int:
                raise ValueError("baseline entry types are invalid")
            candidate = (base / relative).resolve()
            try:
                candidate.relative_to(base.resolve())
            except ValueError as error:
                raise ValueError("baseline path escapes its allowlisted root") from error
            if not candidate.is_file() or candidate.stat().st_size != expected_size or _sha256(candidate) != expected_hash:
                mismatches.append(relative)

    def require_authoritative(entries: object, digest: str, name: str) -> None:
        if not isinstance(entries, list) or hashlib.sha256(_canonical(entries)).hexdigest() != digest:
            raise ValueError(f"{name} inventory is noncanonical")

    approved_specs = baseline.get("approved_specs")
    if not isinstance(approved_specs, list) or tuple(entry.get("relative_path") for entry in approved_specs if isinstance(entry, dict)) != _SPEC_PATHS:
        raise ValueError("approved-spec inventory is noncanonical")
    verify(approved_specs)
    sources = baseline.get("certified_source_files")
    dependencies = baseline.get("additional_learner_dependencies")
    pilot_config = baseline.get("pilot_config")
    require_authoritative(sources, _SOURCE_ENTRIES_SHA256, "certified source")
    require_authoritative(dependencies, _LEARNER_DEPENDENCIES_SHA256, "learner dependency")
    if hashlib.sha256(_canonical(pilot_config)).hexdigest() != _PILOT_CONFIG_ENTRY_SHA256:
        raise ValueError("pilot config inventory is noncanonical")
    verify(sources)
    verify(dependencies)
    verify([pilot_config])
    preflight = baseline.get("certified_preflight")
    if not isinstance(preflight, dict) or set(preflight) != {"result_root", "final_verdict", "artifacts", "certificate_entries", "cache_entries"} or preflight.get("final_verdict") != "CERTIFIED_PASS" or preflight.get("result_root") != "results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight":
        raise ValueError("certified preflight baseline is invalid")
    result_root = root / preflight.get("result_root", "")
    if not result_root.is_dir():
        mismatches.append("certified_preflight.result_root")
    else:
        require_authoritative(preflight.get("artifacts"), _PREFLIGHT_ARTIFACTS_SHA256, "preflight artifact")
        verify(preflight.get("artifacts"), result_root)
        for key, expected_paths in (("certificate_entries", _CERTIFICATE_PATHS), ("cache_entries", _CACHE_PATHS)):
            entries = preflight.get(key)
            if not isinstance(entries, list) or tuple(entry.get("relative_path") for entry in entries if isinstance(entry, dict)) != expected_paths or len({entry.get("relative_path") for entry in entries if isinstance(entry, dict)}) != 20:
                raise ValueError("certified preflight inventory is noncanonical")
            verify(entries, result_root)
    suite = baseline.get("certified_suite")
    if not isinstance(suite, dict) or set(suite) != {"version", "suite_hash"} or suite.get("version") != "increment8_family3_v2_forecast_scope_reservation_v0" or suite.get("suite_hash") != "98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c":
        raise ValueError("certified suite inventory is noncanonical")
    hashes = tuple(entry["sha256"] for entry in baseline["approved_specs"])
    return CertifiedDependencyVerification(not mismatches, tuple(mismatches), str(suite.get("suite_hash", "")), hashes)

```

## Current file: tests/test_family3_v2_learner_pilot.py
```
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from pa_rl.family3_v2_pilot_criteria import (
    load_family3_v2_pilot_config,
    verify_certified_dependency_baseline,
)


class Family3V2PilotContractTests(unittest.TestCase):
    def test_config_and_certified_baseline_are_exact(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config_path = root / "configs/evaluation/family3_v2_learner_pilot_v0.json"
        baseline_path = root / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json"

        config = load_family3_v2_pilot_config(config_path)
        self.assertEqual(
            tuple(method["id"] for method in config.methods),
            (
                "random_valid", "forecast_ablated_rule", "forecast_rule",
                "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
                "masked_ddqn_gamma1",
            ),
        )
        self.assertEqual(tuple(config.split["train"]), tuple(f"i8_f3v2_v{i}" for i in range(5)))
        self.assertEqual(tuple(config.split["validation"]), ("i8_f3v2_v5", "i8_f3v2_v6"))
        self.assertEqual(tuple(config.split["test"]), ("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9"))
        self.assertEqual(tuple(config.training["seeds"]), (17, 29, 43))
        self.assertEqual(config.training["transitions_per_learner_seed"], 12000)
        self.assertEqual(config.training["allocation"]["transitions_per_train_graph"], 2400)
        self.assertEqual(config.evaluation["episodes_per_graph_condition_seed"], 50)
        self.assertEqual(config.certified_environment["adapter"]["maximum_state_width"], 43)
        self.assertEqual(config.certified_environment["adapter"]["candidate_count"], 7)
        self.assertEqual(config.certified_environment["adapter"]["candidate_feature_width"], 7)

        verification = verify_certified_dependency_baseline(baseline_path)
        self.assertTrue(verification.passed, verification.mismatches)
        self.assertEqual(verification.suite_hash, "98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c")
        self.assertEqual(len(verification.approved_spec_hashes), 2)

        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        preflight = baseline["certified_preflight"]
        self.assertEqual(len(preflight["certificate_entries"]), 20)
        self.assertEqual(len(preflight["cache_entries"]), 20)
        self.assertTrue(all(set(entry) == {"relative_path", "sha256", "byte_size"} for entry in preflight["certificate_entries"]))
        self.assertTrue(all(set(entry) == {"relative_path", "sha256", "byte_size"} for entry in preflight["cache_entries"]))

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            altered_config = json.loads(config_path.read_text(encoding="utf-8"))
            altered_config["unknown"] = "forbidden"
            altered_path = temporary / "unknown.json"
            altered_path.write_text(json.dumps(altered_config), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_family3_v2_pilot_config(altered_path)
            altered_config.pop("unknown")
            altered_config.pop("methods")
            altered_path.write_text(json.dumps(altered_config), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_family3_v2_pilot_config(altered_path)
            altered_config = json.loads(config_path.read_text(encoding="utf-8"))
            altered_config["training"]["transitions_per_learner_seed"] = True
            altered_path.write_text(json.dumps(altered_config), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_family3_v2_pilot_config(altered_path)

            tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
            tampered["additional_learner_dependencies"][0]["sha256"] = "0" * 64
            tampered_path = temporary / "tampered-baseline.json"
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_certified_dependency_baseline(tampered_path)

            tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
            tampered["certified_preflight"]["certificate_entries"][0]["sha256"] = "0" * 64
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertFalse(verify_certified_dependency_baseline(tampered_path).passed)
            tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
            tampered["certified_preflight"]["cache_entries"][0]["byte_size"] = 0
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertFalse(verify_certified_dependency_baseline(tampered_path).passed)

            for mutation in (
                lambda value: value.__setitem__("unknown", True),
                lambda value: value.__setitem__("approved_specs", list(reversed(value["approved_specs"]))),
                lambda value: value["certified_preflight"].__setitem__("result_root", "../escape"),
                lambda value: value["certified_preflight"].__setitem__("certificate_entries", value["certified_preflight"]["certificate_entries"][:-1] + [value["certified_preflight"]["certificate_entries"][0]]),
                lambda value: value.__setitem__("certified_source_files", list(reversed(value["certified_source_files"]))),
                lambda value: value.__setitem__("additional_learner_dependencies", list(reversed(value["additional_learner_dependencies"]))),
                lambda value: value.__setitem__("pilot_config", {**value["pilot_config"], "relative_path": "src/pa_rl/ddqn.py"}),
                lambda value: value["certified_preflight"].__setitem__("artifacts", list(reversed(value["certified_preflight"]["artifacts"]))),
            ):
                tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
                mutation(tampered)
                tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
                with self.assertRaises(ValueError):
                    verify_certified_dependency_baseline(tampered_path)


if __name__ == "__main__":
    unittest.main()

```

## Current file: docs/CONTINUATION_CHECKPOINT.md
```
# RL Personal Assistant — Continuation Checkpoint

This file is the durable restart point for interrupted work. Update it at every
meaningful boundary: before production edits, after a genuine RED, after GREEN,
before independent review, and after the review verdict. It is intentionally
shorter than the implementation reports and is the first file to read after a
network interruption or context reset.

## Current checkpoint

- Updated: 2026-09-20 (America/Toronto)
- Active phase: **Family-3 v2 exact-preflight artifact remains frozen `CERTIFIED_PASS`; Learner/Baseline Pilot Task 1 dependency/config boundary is complete; Task 1 review is the next authorized boundary**
- Increment 8 state: **all 10 Family-3 v2 graphs remain certified at exact `V*=4/5` with request Q-gap `3/5`; the certified environment/suite/policy/solver artifacts remain immutable for the learner study**
- Experiment state: **Task 1 added only the frozen config, dependency baseline, strict criteria loader/verifier, and focused contract test; no adapter, runner, smoke, training, validation, official test, server job, or OpenAI API call has run**
- Last approved completed experiment: **Increment 7 Task 5 — Run integrity PASS / Result interpretation APPROVED; PARITY; prefer Rule; no rerun/tuning or Deep-RL advantage claim**
- Current design worker: none; Task 1 is implemented and its focused fix round is GREEN; no learner/training process is in flight
- Current read-only reviewers/calibrators: learner-pilot scientific closeout `APPROVE`; bilingual contract audit `PASS`; final implementation-plan audit `APPROVE`; normative JSON is byte-for-byte identical and parseable in both specs
- Learner-pilot English approved spec: `docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md` (SHA-256 `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`, 38,149 bytes)
- Learner-pilot Chinese approved spec: `docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md` (SHA-256 `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`, 35,818 bytes)
- Learner-pilot implementation plan: `docs/superpowers/plans/2026-09-20-increment8-family3-v2-learner-pilot.md` (SHA-256 `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`, 30,311 bytes)
- Family-3 v2 English spec: `docs/superpowers/specs/2026-08-27-increment8-family3-v2-design.md` (SHA-256 `1C2F173A33EE438CE15ED910EF1637536B535495C95D73F340B679291C00656F`)
- Family-3 v2 Chinese spec: `docs/superpowers/specs/2026-08-27-increment8-family3-v2-design_zh.md` (SHA-256 `82DDA83C604BE7C46276331BF4F9B65D974C167E58635407C943F8285757CEEF`)
- Family-3 v2 implementation plan: `docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md` (SHA-256 `036B9690A06267099C62F78B98C973A9B283037BAB449AF074CB6A878A049658`)
- Increment 8 English spec: `docs/superpowers/specs/2026-08-18-increment8-budgeted-lifecycle-design.md` (SHA-256 `1E75BFF12CBE72B6EB42E4F6E7D9C99DF7F426445C4EC9FD481EA6DC2EB86913`)
- Increment 8 Chinese spec: `docs/superpowers/specs/2026-08-18-increment8-budgeted-lifecycle-design_zh.md` (SHA-256 `2CDB11522339E8950799E09A1ADDFA24EDF34A3795C49BA5CBA7156182FFF96A`)
- Final design verification: three independent read-only reviews PASS; both files have 14 main sections/29 total headings, identical parseable criteria JSON, no TODO/TBD/FIXME/placeholder, and exact agreement on split/method/seed/budget/row/cardinality/state-machine contracts.
- Phase A plan: `docs/superpowers/plans/2026-08-26-increment8-phase-a-preflight-plan.md`.
- Phase A notes/report: `docs/superpowers/notes/2026-08-26-increment8-phase-a-implementation-notes.md` and `docs/implementation_reports/task-8-phase-a-report.md`.
- Interruption boundary: **STABLE / TASK 1 IMPLEMENTED / FIX ROUND 1 GREEN / TASK 1 REVIEW PENDING / NO PROCESS IN FLIGHT.** The exact twelve-gate artifact remains unchanged. The frozen config/baseline now bind the literal 5/2/3 split, 43/7/7 adapter contract, seven public-only methods, matched `gamma=0/1`, seeds 17/29/43, 12,000/2,400/50 budgets, and literal certificate/cache hash-size inventory. No adapter, runner, smoke, training, validation, or test has run. Exact next action: Task 1 review.
- Task 4 fix round 1 boundary: **STABLE / REVIEW PENDING.** Regression RED ran 19 methods in 0.076s and failed exactly I1/I2/M1 (`failures=3, errors=2`). Affected focused GREEN passed 19 methods in 0.071s; the single authorized Tasks 2–4 combined run passed 24 methods in 0.081s. Caller-visible binding evidence contains no raw authorization handle, all anomaly successors use public model-owned `transition_integrity_failure`, and singleton first-effect closure records no branch residue. SHA-256: model `f7848d2ac0343d2ffb79b24d584a81da1fa5daa51c7f97d35134948d90020f2c`; model test `36a8bf08e5d0dc337fac80447f5ff8e6bcc95fde0293beebd551433886a9efc1`; authority `0aca9e16347a8e0c128b0dcaf632a3223556a6c9d79adbf4c9fe776fe030588d`; policy unchanged `2ebbb936567c0ca65ec616cc91e4e5c708d939394c7f41b31d00c0c8a2f4e0a6`; environment `764ec0132b09d2fcdcbf6339f2d6b8013e7e06ded05849f4611a2f2d532f9663`; authority/environment test `63ce6fd58a6e55b93c4293664f55ec2c73f1bfddb9ca25cc54d18a5f3dd38eeb`. Gate authority remains `BASELINE_FROZEN / 0 / 1`; exact next action is independent Task 4 fix-round re-review before Task 5.
- Task 5 boundary: **STABLE / FOCUSED GREEN.** The exact missing-audit RED was `ModuleNotFoundError: No module named 'pa_rl.family3_v2_audit'` (`Ran 1 test in 0.000s`, exit 1). Final focused GREEN passed 7 methods in 27.802s. Reports passed with: Markov 20 analyses/314 occurrences/314 public groups/314 encoded groups/2,198 rows/1,256 valid actions/1,296 transitions; real-environment conformance 20 analyses/314 states/1,256 actions/1,416 replays including exact residues `{0,1,2,3,4}` and 200 first-effect residue replays; firewall 480 manifests/4,800 row checks; witnesses 40 cells; binding/no-repair 20 bindings/2,058 catalog rows/6 action types/882 no-repair checks/4 nonemitted guards/882 forced-invalid zero-delta checks. Audit/test SHA-256 and sizes: `36f590a1804369f05429142479a6d51fa0d9f50a9ffbdc0ba6bb00675ed6cb2c` / 44,665 bytes and `a848b77c80f74da487374ef3c40fe191140ceebc520cc24746617cca3c82d77f` / 11,815 bytes. Frozen Task 2–4 hashes match the Task 5 base manifest. Gate authority remains `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`; exact next action is **Implement Task 6 capped exact solver, independent reference, and artifact store**. No broad/combined tests, DP, solver, runner, training, tuning, or rebaseline ran.
- Task 5 fix round 1/5 boundary: **STABLE / FOCUSED GREEN / RE-REVIEW REQUIRED.** Affected regression RED ran 18 methods in 31.029s with the expected six missing-evidence/API errors. The single authorized affected GREEN passed 18 methods in 71.949s. Exact safety evidence now covers 294 no-repair states, 882 closed-offer rows, 294 disable guards, 20 execute guards, 314 complete nonemitted catalogs (2,198 rows), and 882 full-channel forced-invalid zero-delta replays. Task4 evidence now publishes immutable task snapshot and user-dispatch count without changing policy observation. SHA-256: environment `20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8`; environment test `daf5e80aea4569ac9fe8e007a5cf7a2f2eb680b69f6d28da78d5a0916de1d092`; audit `1ba1dc3b660892410bb31bec9af3cb1a0d145f479851ffb58ee954ec049b98d5`; audit test `2ed2837d0e081947643e4def4b7893d431facaa5a631a23ec0f6b19b2fe708d0`. Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 6 is blocked. Exact next action is fresh independent Task 5 fix-round re-review.
- Task 5 fix round 2/5 boundary: **STABLE / INDEPENDENTLY APPROVED.** The two new regression methods first failed in 7.078s on the expected missing literal/stable-key evidence, then the identical two-method command passed once in 14.976s. Production independently checks 294 ordered emitted literals, 314 pure and 314 real ordered no-coverage literals, and 882 complete dataclass stable keys plus 882 exact forced-invalid closures. Fresh focused review returned Spec PASS / Quality PASS / APPROVE with C1/C2 addressed and no new finding; 14/14 frozen source and 72/72 frozen result files still match. Audit SHA-256 `92ef0f7794536581a5fbb51719ea8b4a79436b61b4b0bc61eb3632a020b45921` (64,280 bytes); audit-test SHA-256 `de07886c8609204b0a9539f1a514e85bcfe6e9b69e9fea10ceffd845cd37fe48` (22,466 bytes). Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 6 brief hash remains `7d57ab70c77be1fd8add1a68f7232c6fd6373fd85a69a14155a707f064f61581`. Exact next action is Task 6 capped solver/reference/artifact implementation.
- Task 6 boundary: **STOPPED / NOT GREEN / HUMAN INSPECTION REQUIRED.** The missing-solver RED was exact. Three disjoint modules were then created. The single combined GREEN attempt ran 12 methods in 5.311s: 11 passed; one error occurred only when Windows `TemporaryDirectory` tried to unlink `values.sqlite3` still held by the test's `sqlite3.Connection`. No Bellman/reference/artifact assertion failed. No fix or retry ran. Evidence: `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-6-green-failure.md`. Gate authority remains `BASELINE_FROZEN / 0 / 1`; exact next action is human approval or rejection of a minimal test-only explicit connection close and one rerun.
- Task 6 closeout: **FOCUSED GREEN / INDEPENDENT REVIEW PENDING.** Authorized test-only repair added `contextlib.closing` around the test-owned guard-tampering SQLite connection; no production code, scientific assertion, parameter, cache, certificate, run config, or gate changed. The same focused command was rerun once and passed all 12 methods in 5.260s (`OK`, no warning). Final hashes/bytes: solver `027d4d8da118eb2f6d66c8898bf8e0824c521c3890bc237564fed27298a01a2b` / 36,031; reference `5f51a22ee949e8693259464f28db1a9a14bca66a206d71e4ca3b0131329078ff` / 11,935; artifacts `a02918478f9eae0ca0b48981a2d6334560417bb61056c4dbe3839bd3289dff6b` / 29,226; solver test `52cf4227293ac924cf6fbe57205e7033e7efa89ed453c24cf362eefd60adc5aa` / 7,172; reference test `45462581c71a1fe09e1a7bdf0298b43bb7b87b71c60085ee1f6c5bcb1e2f2ec6` / 3,400; artifact test `04ae0e068fc1b79cc40d0949bc0400be8f5c2905a8f9d4b6fa31e14d8e897e28` / 7,127. Task 2–5 frozen manifest is unchanged. Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 7 remains blocked pending independent Task 6 spec+quality APPROVE. Evidence: `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-6-report.md`.
- Task 6 fix round 1/5 boundary: **BLOCKED / INVALID GROUPED RED.** The single prescribed command ran 29 methods in 15.407s and returned 13 expected behavioral failures plus one fixture error. The error happened before production construction because the wrong-output helper hashed a nonexistent `wrong_output/run_config.json`. The stop rule prohibited repair, production edits, or GREEN. Three production hashes remain at their reviewed base; only the three focused tests contain the new regressions. Gate authority remains `BASELINE_FROZEN / 0 / 1`, Task 7 remains blocked, and the exact next action is human authorization for a fresh round starting by repairing that fixture before a newly authorized RED.
- Task 6 fix round 1/5 continuation: **FOCUSED GREEN / SCOPED RE-REVIEW REQUIRED.** Controller ruled the pre-constructor fixture error was not a scientific failure and authorized only canonical run-config fixture setup before a replacement RED. Valid RED ran 29 methods in 8.455s with 14 behavior failures and zero errors; the single post-fix GREEN passed all 29 in 7.616s. C1/I1–I6/M1 fixes bind output ancestors/containment, restart/evidence shapes, immutable baseline SHA, canonical SQLite schema, same-graph reference traversal, mandatory pressure/negative coverage, and reference-result row invariants. Gate remains `BASELINE_FROZEN / 0 / 1`; Task 7 remains blocked pending review of `task-6-fix-1-review-package.md`.
- Task 6 final approval: **COMPLETE / INDEPENDENTLY APPROVED.** Fresh scoped review of fix round 1 returned Spec PASS / Task Quality PASS / APPROVE, with C1/I1–I6/M1 addressed and no new Critical, Important, or Minor finding. The review recomputed the final six Task 6 hashes/bytes, confirmed all Task 2–5 hashes unchanged, retained RED/invalid-fixture/valid-RED/GREEN history, and verified the fixed root has only checkpoint, baseline, and JSONL. Gate authority remains `BASELINE_FROZEN / 0 / 1`. Task 7 is authorized/pending under `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-7-brief.md`; its exact next action is **Implement Task 7 ordered twelve-gate preflight under frozen brief**. No Task 7 test, DP, preflight, compilation, training, run config, Gate, cache, or certificate has run/been created.
- Task 7 runner boundary: **FOCUSED GREEN / READINESS REVIEW REQUIRED.** The single RED failed only on the required missing runner import (`Ran 1 test in 0.000s`). The single focused GREEN passed 16/16 methods in 0.417s (`OK`). New hashes/bytes: runner `1044da7eebb0710218157187c265a4889a57c3821960045cf8c12f2b4d42c976` / 48,890; test `65012d3d1ca5b0a07178c8cea16987e64f7a81ef34a6429e3d0a00594f3aacaa` / 23,379. All 19 Task 2–6 hashes/bytes remain unchanged. Gate authority remains `BASELINE_FROZEN / 0 / 1`; fixed root still contains only baseline, checkpoint, and progress JSONL. No adjacent regression, compile, real ten-graph preflight, run config, Gate, cache, certificate, failure, interruption, or verdict was produced. Next action: independent Task 7 readiness review of `task-7-implementation-review-package.md`.
- Task 7 fix round 1/5 boundary: **BLOCKED / INVALID GROUPED RED.** The exact grouped command ran once: 44 methods in 14.340s, 22 failures, zero errors. Expected C1/I1–I3/M1 behavior gaps appeared, but the new typed Gate-3 I4 fixture encoded a 20/10/10 cell partition while declaring 40/0/0 counts, so one failure was caused by contradictory test setup. Stop rule enforced: no fixture repair, production edit, GREEN, adjacent regression, compile, or real preflight. Only the two focused tests changed; runner/artifact-store production hashes remain reviewed-base values. Gate remains `BASELINE_FROZEN / 0 / 1`; fixed root remains three files. Exact next action is fresh authorization to correct only those fixture counts before a new grouped RED.
- Task 7 fix round 1 continuation: **FOCUSED GREEN / SCOPED READINESS REVIEW REQUIRED.** Controller authorized the same round to change only typed witness declarations 40/0/0→20/10/10. Valid replacement RED: 44 methods / 13.108s / 21 behavioral failures / zero errors. Single grouped GREEN: 44 methods / 15.173s / `OK`. C1 added strict disk-reconciled recovery across handler/commit/finalize boundaries; I1–I4/M1 strengthen dependency closure, committed Gate4→5 binding, Gate1 proof, real-handler coverage, and Gate6 evidence. Final four hashes are recorded in `task-7-fix-1-review-package.md`; the store/test reopening is controller-authorized and the other 17 Task 2–5 entries remain unchanged. Gate remains `BASELINE_FROZEN / 0 / 1`, fixed root remains three files, and adjacent/compile/real preflight remain unrun.
- Task 7 fix round 2 boundary: **STOPPED / INDEPENDENT `DO_NOT_RUN` / FIRST REAL READINESS FAILURE.** Grouped RED was valid (54 methods / 29.720s / 12 C1/I2 behavior failures / zero errors) and grouped GREEN passed once (54 methods / 24.949s / `OK`), but fresh static review found a remaining Critical C1 recovery-before-checkpoint defect and Important I4 gaps in Gate-3 predicates and real atomic persistence boundaries; I2 is closed and I1/I3/M1 remain closed. Review SHA-256 `fb2388f506fa41c8ad00ac7bff42370de3456ce416965c38d90f1abdebfc26da` / 10,776 bytes. Per stop rule, adjacent regressions, compile, DP, and the real preflight were not run. Gate remains `BASELINE_FROZEN / 0 / 1`; exact next action is human discussion before any fix round 3.
- Task 7 final boundary: **COMPLETE / `CERTIFIED_PASS`.** Fix round 3 independently closed C1/I4 with no remaining finding. Ordered execution evidence is v2 suite 110/110, legacy adjacent 68/68, 13-module compile exit 0, and one real twelve-gate run exit 0. All 10 exact graph certificates report initial `4/5`; all request Q gaps are `3/5`. The 72-file fixed-root audit verified 20 certificates/caches, all SQLite `quick_check=ok`, 314 nonterminal rows, 29.43 MiB peak RSS, exact frozen v0/v1 preservation, and zero path escape. The first audit-helper call used the wrong assumed SQLite table name and was corrected without modifying the product or artifacts. This boundary certifies exact benchmark construction and integrity only; it is not DDQN evidence.
- Diagnostic boundary: **V4 COMPUTATIONAL UNKNOWN RESOLVED / FAMILY-3 V1 STILL REJECTED.** Terminal-history over-separation was sufficient to cause the old v4 block, but the independent `s3_v3=13/25<3/5` construct/feasibility failure remains unchanged. Therefore all-forty and v1 spec freeze remain blocked. Results: `results/increment8_v1_terminal_cache_bypass_diagnostic`; English/Chinese reports: `docs/research_audits/2026-08-27-terminal-cache-bypass-diagnostic/terminal-cache-bypass-diagnostic-report.md` and `_zh.md`. Source SHA-256 `1217EC43CE64D9B4DA12C9C1CB75DD6B8C24536EF8B3061DDEA1F60C6AABAF4F`; v4 certificate SHA-256 `964C48026DD4563992E79A3A2AA1715F37CBB66596C87F3882639403F5BC2D39`.
- Rough source files: `src/pa_rl/baselines.py`, `src/pa_rl/g2_rough.py`
- Focused rough test: `tests/test_g2_rough.py`
- Minimal replay source/test: `src/pa_rl/replay.py`, `tests/test_replay_minimal.py`
- Review source of truth: `docs/implementation_reviews/task-3b2b1-review.md`
- Rough report: `docs/implementation_reports/task-4-rough-report.md`
- Minimal replay report: `docs/implementation_reports/task-3b2-minimal-report.md`
- Increment 5 spec: `docs/superpowers/specs/2026-08-18-increment5-masked-ddqn-design.md`
- Increment 5 plan: `docs/superpowers/plans/2026-08-18-increment5-masked-ddqn-plan.md`
- Increment 5 source: `src/pa_rl/ddqn_features.py`, `src/pa_rl/ddqn.py`,
  `src/pa_rl/evaluation_criteria.py`, and `src/pa_rl/increment5_rough.py`
- Increment 5 criteria/test: `configs/evaluation/rough_v0.json` and
  `tests/test_increment5_rough.py`
- Increment 5 report: `docs/implementation_reports/task-5-rough-report.md`
- Increment 6 audit: `docs/superpowers/notes/2026-08-18-increment6-audit.md`
- Increment 6 spec: `docs/superpowers/specs/2026-08-18-increment6-multiscenario-full-action-design.md`
- Increment 6 Chinese spec: `docs/superpowers/specs/2026-08-18-increment6-multiscenario-full-action-design_zh.md`
- Increment 6 plan: `docs/superpowers/plans/2026-08-18-increment6-multiscenario-full-action-plan.md`
- Increment 6 Task 1 source/test: `src/pa_rl/multiscenario_policy.py` and
  `tests/test_increment6_pilot.py`
- Increment 6 Task 1 report:
  `docs/implementation_reports/task-6-task1-report.md`
- Increment 6 Task 2 source/report: `src/pa_rl/pilot_outcome.py` and
  `docs/implementation_reports/task-6-task2-report.md`
- Frozen Increment 6 artifacts: `results/increment6_multiscenario_v0/result.json`
  (SHA-256 `b79247f824b20ab6f16e6b4b3a733a7896608844f18e456c57daefe482c895c1`)
  and `results/increment6_multiscenario_v0/run_manifest.json` (SHA-256
  `dc7360aaf81a203f4e1e40aca9395619ed728ac8ef6db99ed414b338e10a356a`)
- Frozen criteria: `configs/evaluation/multiscenario_v0.json` (SHA-256
  `87c1a25a0b70745d66b4307ddfd3246aba50df54e960221510cb19d98eda3de3`)
- Pilot report: `docs/implementation_reports/task-6-pilot-report.md`
- Increment 7 Task 1 source/test: `src/pa_rl/increment7_scenarios.py` and
  `tests/test_increment7_pilot.py`
- Increment 7 suite hash:
  `d8ef5d5cd47b465ef88c43e89bf686ee3942334435ed8587786973fe86176eb3`
- Increment 7 split hash:
  `79a2ac01c4c58333c38044735c50e0d2956d03a65d1f2c7585b135925baca320`
- Increment 7 Task 3 source/profile: `src/pa_rl/heldout_criteria.py` and
  `configs/evaluation/heldout_context_v0.json`
- Increment 7 Task 3 report:
  `.superpowers/sdd/2026-08-18-increment7-heldout-context-plan/task-3-report.md`
- Frozen Increment 7 results: `results/increment7_paired_v0/`; formal report:
  `docs/implementation_reports/task-7-heldout-context-report.md`; approved
  Task 5 review:
  `.superpowers/sdd/2026-08-18-increment7-heldout-context-plan/task-5-review.md`.
- Exact next action: Task 1 fix round 2/re-review. Task 2 may start only after
  Task 1 receives spec and quality approval. Do not start smoke, training,
  validation, or test before their separately authorized boundaries.

## Increment 7 Task 5 READY_FOR_FROZEN_RUN boundary

- Frozen at `2026-08-18T13:30:47.136+08:00` after the Task 4 fix-round
  independent verdict `Spec: PASS / Quality: APPROVED`.
- Official output path:
  `results/increment7_paired_v0`; the directory, `result.json`, and
  `run_manifest.json` were all absent before execution. No completed official
  run exists.
- Exact one-time command:
  `$env:PYTHONPATH='src'; python -m pa_rl.increment7_pilot --criteria
  configs\evaluation\heldout_context_v0.json --output
  results\increment7_paired_v0`.
- Frozen suite: 40 members; suite SHA-256
  `d8ef5d5cd47b465ef88c43e89bf686ee3942334435ed8587786973fe86176eb3`;
  split SHA-256
  `79a2ac01c4c58333c38044735c50e0d2956d03a65d1f2c7585b135925baca320`.
- Canonical frozen default config SHA-256:
  `e02aed5070c55103f86ecfeaf6dd16608b8013905db4d460b9341fce77123fac`.
  Seeds are `17/29/43`; training is 500 transitions per each of 24 train
  scenarios per learner; evaluation is 50 episodes per each of eight
  validation and eight test scenarios per method and seed.
- Canonical criteria mapping SHA-256:
  `c34a7dd32257e7e3d3e5965de59178335c562eaa73c347e3541a8cc6477dc144`;
  profile-file SHA-256:
  `d94a57d228660e2bd781f9361bdd576a689e242c48a4d67b0ea3850772cd616f`.
- Feature-layout SHA-256:
  `7869ae077a38a8b100e5e63cb00f1f49d1165ba9f22a75359622a83f82cdd0c1`.
- Required runner source SHA-256 values: suite generator
  `0cc29726110dbc245725b46cd5463c4bb4a16684dc654fd55a9b005f94a54faf`;
  runner `5221108917aadb5934b3240267b8cacb0ec2d8696e06a4461eebcb0b6fcbbc17`;
  encoder `981054ae53e836328baccd805caa21f4183b8574eaf2e5da87e7a182170d83d8`;
  DDQN `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1`;
  criteria `1494b28fc82cc438ba8a86bc90d449ab73d972365cb3a52e683a354aca5cb1a3`;
  Rule `752aaac9a1d75b16e721f4c28cd9672052ad3d76f0edb9fbd52e138cf1a1a21b`;
  protocol tracker
  `7ce8acf5b3a2781a571343db11e363983d842e5f16db0f3aaa37568a3cb159e5`.
- Focused Increment 7 test SHA-256:
  `4847bc4e40db499b742def16b8ee0e03218f12417bd7213d64f618102828a27b`.
- Status: `READY_FOR_FROZEN_RUN`. After this boundary, source, config, and
  tests are immutable for the run. Any orchestration/output-capture failure
  stops execution and requires explicit authorization before an identical
  recovery command.

## Increment 7 Task 5 frozen completion boundary

- Exactly one official default command ran. Exit `0`; complete stdout was
  `{"classification": "PARITY", "gate_status": "EVALUATED", "output":
  "results\\increment7_paired_v0"}`; stderr was empty. Tool wall time was
  `1081.5 s` and runner time was `1078.4561935000238 s`. There were no
  interruptions, restarts, recovery commands, tuning changes, or reseeds.
- Durable checkpoints completed in order for seeds 17, 29, and 43. Validation
  froze the exact checkpoints before the single test boundary. Final official
  progress is `COMPLETE / artifacts_complete / error=null`.
- Test macro protocol/base: Random `0.0525/0.1375`; Rule
  `0.8750/0.8750`; Tabular-Q `0.0533/0.1242`; DDQN `0.8750/0.7917`.
  DDQN and Rule each solve seven of eight test protocol families; both fail
  `f2_disable_refresh`.
- Gate recomputation: DDQN-minus-Random `0.8225`; DDQN-minus-best-simple
  `0.0000`; paired seed wins `0`; scenarios worse by more than 0.10 `0`;
  prompt ratio to Rule `1.0909`; all safety counts `0`. Core checks pass, but
  advantage-margin and paired-win checks fail, so classification is `PARITY`.
- Read-only verification parsed all JSON, regenerated the exact all-40 suite,
  checked 24/8/8 registries, the complete 192-row/50-episode grid, all exact
  500-per-train-scenario quotas, every source/config/criteria/feature/scenario/
  result/checkpoint hash, loaded all checkpoints, matched frozen learner
  fingerprints, and exactly recomputed all aggregates and the gate from raw
  rows without training.
- Focused post-run verification:
  `$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot -v`
  passed all three methods (`Ran 3 tests in 13.934s`, exit 0). Targeted
  compilation of Increment 7 source/test exited 0 without output.
- Official artifact SHA-256: result
  `1aa2c9a6334bc51c35e96472bbfa3ae27a37ddc330413c2a5f33d553fa9f4ba0`;
  run manifest
  `79bd638550036125ee1ae4cba9c42a6642007f345a652501730f7f248ce95853`;
  suite manifest
  `38b0fd577ad431a89a96c6d3fd4fb4d0e136d6f71ce16fc2e26582fb684c4ef0`;
  progress
  `24cad8e50bdf36f10501223832954385ccc54b8a4024063229d88e79d4d36e9f`.
  Checkpoints 17/29/43:
  `fe45fbd736d23ad4aff352ed7c76dac50944284cf3ffb13e4d863eaf1f3ebc46`,
  `bc6876feab77aabadabea3eb2827f81e7bf12de10d72a6f621ee2a896fadb68d`,
  `fde7feca5d9cc4084e35d38b6cf1642646098c033e0571707e1f4dc2302e583b`.
- Durable report:
  `docs/implementation_reports/task-7-heldout-context-report.md`. Descriptive
  bundle: `results/increment7_paired_v0/analysis-output/`, including two
  grayscale vector PDFs. Statistical units are eight held-out scenarios and
  three training seeds, not repeated episodes or users; no significance,
  Deep-RL superiority, population-generalization, or deployment claim is
  allowed.

## Increment 7 Task 4 RED boundary

- The existing third focused method was extended before Task 4 production
  code. Exact command: `$env:PYTHONPATH='src'; python -m unittest
  tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke
  -v`.
- Expected RED: `ModuleNotFoundError: No module named
  'pa_rl.increment7_checkpoints'`; exit 1, `Ran 1 test in 0.000s`.
- Approved reduced-smoke contract: when `len(config.seeds) != 3`, the runner
  must not fabricate formal gate rows. It serializes `gate=null` and
  `gate_status=NOT_EVALUATED_REDUCED_SMOKE`; only an exactly three-seed run may
  call the formal held-out gate.
- Library runs write progress only under their explicit `output_dir`; they do
  not mutate this repository checkpoint. This section is the explicit Task 4
  implementation-boundary update. The Task 5 frozen pilot remains prohibited.

## Increment 7 Task 4 GREEN boundary

- Added evaluation-only atomic Tabular/DDQN checkpoints, balanced 24-scenario
  train-only registries, separate eight-scenario validation/test registries,
  public-only four-method evaluation, immutable learner digests, test-once
  progress protection, CLI, and atomic suite/result/run artifacts.
- Reduced smoke uses seed 7, exactly 20 transitions per train scenario and
  learner, and two episodes per validation/test scenario. It serializes
  `gate=null` with `NOT_EVALUATED_REDUCED_SMOKE`; only the exact default frozen
  configuration is eligible for the formal gate.
- Test/source boundary hashes are frozen in `progress_checkpoint.json` before
  test and checked after test. A prior `test_started_frozen` or
  `test_complete_once` boundary fails closed for manual recovery rather than
  rerunning the test split.
- Focused Task 4 GREEN: exact third method passed (`Ran 1 test in 11.180s`).
  Prior Increment 6/5/G2 regressions passed (`Ran 7 tests in 45.571s`). The
  targeted compile command exited 0. No Task 5 run occurred and no
  `results/increment7_paired_v0` directory was created.
- Source/test SHA-256: `ddqn.py`
  `8FD49FFE8FFC9DE5F3D5DA0FB256D08787F65BB8953DA190B5DD729ECCE7DDB1`;
  `increment7_checkpoints.py`
  `F8433A3D11BDBDAF36BD88D8A5FEEE4CE3FC4B85F9E78AFF75A3C0C9795A469E`;
  `increment7_pilot.py`
  `5221108917AADB5934B3240267B8CACB0EC2D8696E06A4461EEBCB0B6FCBBC17`;
  `test_increment7_pilot.py`
  `4847BC4E40DB499B742DEF16B8EE0E03218F12417BD7213D64F618102828A27B`.

## Increment 7 Task 4 fix round 1 boundary

- Recovery RED: a valid partial two-seed progress record retained seed 7, but
  the old runner spy observed Tabular/DDQN training for both seeds 7 and 11.
  Recovery now strictly validates the complete frozen boundary, completed seed
  keys, checkpoint relative paths/byte hashes/model-Q identity, learner
  contract, environment-step total, and both exact 24-scenario quota maps.
  Verified completed seeds restore bookkeeping and are never overwritten;
  only missing seed 11 trains in the regression, while seed 7 hash/mtime stays
  unchanged.
- Loss RED: a patched NaN `observe()` return was ignored and surfaced only as
  later DDQN step-accounting drift. `_train_ddqn` now accepts `None` or a
  finite exact float only and fails immediately on non-finite loss before any
  completed checkpoint. The regression confirms no checkpoint and an empty
  completed-seed failure record.
- Final exact third method: `Ran 1 test in 13.013s - OK`; specified Increment
  6/5/G2 regressions: `Ran 7 tests in 41.956s - OK`; targeted compilation:
  exit 0. Task 5/default run remains prohibited.

## Increment 7 Task 3 boundary

- Genuine RED command: `$env:PYTHONPATH='src'; python -m unittest
  tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke
  -v`. Result: expected `ModuleNotFoundError: No module named
  'pa_rl.heldout_criteria'` (`Ran 1 test`, error, exit 1).
- Focused GREEN: the identical command initially passed (`Ran 1 test in 0.058s
  -- OK`). A follow-up exact-0.05 boundary regression then produced a genuine
  assertion RED and passed after tolerance-aware threshold comparisons (`Ran 1
  test in 0.013s -- OK`). The final complete Increment 7 focused file passed
  all three methods (`Ran 3 tests in 1.177s -- OK`), and targeted compilation
  of `heldout_criteria.py` and `test_increment7_pilot.py` exited 0.
- The exact JSON profile is evaluation-only. The gate validates all four method
  keys, all scenario/seed rows, strict numeric domains, safety counts, and
  positive-infinity prompt rates. It derives aggregate, per-scenario, and
  per-seed best-simple comparisons and returns `NO_GO`, `PARITY`, or
  `ADVANTAGE_SIGNAL` from separate core and advantage checks.
- SHA-256: `heldout_context_v0.json`
  `D94A57D228660E2BD781F9361BDD576A689E242C48A4D67B0EA3850772CD616F`;
  `heldout_criteria.py`
  `1494B28FC82CC438BA8A86BC90D449AB73D972365CB3A52E683A354ACA5CB1A3`;
  `test_increment7_pilot.py`
  `4B2DF4157B201F17BA64FE8631626E476FC145C8CEDA2215BBC1FC9249190470`.
- Git provenance is unavailable: `git status --short` exits 1 with `fatal: not
  a git repository`. File hashes are the stable review boundary.
- Changed only the Task 3 profile/module, the existing test file's exactly third
  method/imports, this checkpoint, and the Task 3 report. No runner, learner,
  training, evaluation checkpoint, result artifact, environment, monitor,
  tracker, suite, encoder, or Rule implementation changed.

## Increment 7 Task 3 fix round 1 boundary

- The independent review's sole Important finding was reproduced before the
  production change. Six otherwise-successful scenario rows and two otherwise-
  winning seed rows were both accepted; the focused command reported exactly
  two `ValueError not raised` subtest failures (`Ran 1 test in 0.012s --
  FAILED (failures=2)`).
- `evaluate_heldout_gate` now rejects `per_scenario` unless it has exactly eight
  rows and rejects `per_seed_macro` unless it has exactly three rows. Existing
  non-empty scenario-ID, exact-integer seed-ID, and exact four-method row checks
  remain unchanged.
- The identical focused command passed (`Ran 1 test in 0.015s -- OK`); the
  permitted complete Increment 7 suite passed (`Ran 3 tests in 1.134s -- OK`),
  and targeted compilation exited 0.
- Updated SHA-256: `heldout_criteria.py`
  `1494B28FC82CC438BA8A86BC90D449AB73D972365CB3A52E683A354ACA5CB1A3`;
  `test_increment7_pilot.py`
  `4B2DF4157B201F17BA64FE8631626E476FC145C8CEDA2215BBC1FC9249190470`.
- Changed only the approved Task 3 source/test and this checkpoint/report.
  Task 4 remains untouched.

## Increment 7 Task 2 boundary

- RED: the second focused test was added before Task 2 production code. From
  the project directory, `$env:PYTHONPATH='src'; python -m unittest discover
  -s tests -p test_increment7_pilot.py -v` failed because
  `PUBLIC_STATE_INDEX_V1` was not exported from `pa_rl.multiscenario_policy`.
- GREEN: the identical discovery command passed both focused Increment 7
  methods (`Ran 2 tests in 1.083s — OK`). Targeted compilation of
  `increment7_scenarios.py`, `multiscenario_policy.py`, `public_rule.py`, and
  `test_increment7_pilot.py` exited 0.
- All 40 legal traces replay through a one-manifest environment with a pre-step
  public row and a post-step trusted audit passed only to the protocol tracker.
  Every legal replay returned protocol reward 1 with zero mask violations,
  unauthorized committed effects, and monitor-blocked attempts. Eight
  executable representative deviations returned protocol reward 0; the timeout
  canonical trace succeeds only through clean truncation.
- `PUBLIC_STATE_INDEX_V1` and `PUBLIC_CANDIDATE_INDEX_V1` are immutable named
  v1 maps protected by import-time layout assertions. `choose_public_rule`
  reads only decision tensors, actions, semantic IDs, and mask; the named Rule
  test selects ESCALATE only for `unavailable_resolution` after denial.
- SHA-256: `multiscenario_policy.py`
  `981054AE53E836328BACCD805CAA21F4183B8574EAF2E5DA87E7A182170D83D8`;
  `public_rule.py`
  `752AAAC9A1D75B16E721F4C28CD9672052AD3D76F0EDB9FBD52E138CF1A1A21B`;
  `test_increment7_pilot.py`
  `69056B8288E22631F01C3484FDE45A1068FB14BCEB6A4C966E00A7855D33865E`.
- Changed only the Task 2 policy/layout/test surfaces, this checkpoint, and the
  Task 2 report. No runner, gate, training, learner, environment, tracker,
  evaluator, replay, or fixture source changed.
- Documentation fix round 1: the exact dotted focused Task 2 command was
  rerun from the project directory and passed (`Ran 1 test in 1.390s — OK`):
  `$env:PYTHONPATH='src'; python -m unittest
  tests.test_increment7_pilot.Increment7PilotTests.test_all_protocols_replay_negative_controls_and_named_rule
  -v`. Task 2 source/test hashes remain
  `981054AE53E836328BACCD805CAA21F4183B8574EAF2E5DA87E7A182170D83D8`,
  `752AAAC9A1D75B16E721F4C28CD9672052AD3D76F0EDB9FBD52E138CF1A1A21B`, and
  `69056B8288E22631F01C3484FDE45A1068FB14BCEB6A4C966E00A7855D33865E`.

## Increment 7 Task 1 boundary

- Suite version: `increment7_paired_context_v0`; deterministic suite/split
  hashes are `d8ef5d5cd47b465ef88c43e89bf686ee3942334435ed8587786973fe86176eb3`
  and `79a2ac01c4c58333c38044735c50e0d2956d03a65d1f2c7585b135925baca320`.
- Genuine RED command: `$env:PYTHONPATH='src'; python -m unittest
  tests.test_increment7_pilot.Increment7PilotTests.test_suite_split_and_policy_firewall_invariants
  -v`. Result: expected `ModuleNotFoundError: No module named
  'pa_rl.increment7_scenarios'`.
- GREEN: the identical focused command passed (`Ran 1 test in 0.144s — OK`).
  `python -m compileall -q src\pa_rl\increment7_scenarios.py
  tests\test_increment7_pilot.py` exited 0.
- Frozen evidence: 40 unique scenarios across eight protocol families and five
  public scope carriers; split sizes are exactly 24 train / 8 validation / 8
  test. Split labels, scenario/family/carrier identities, legal traces, hidden
  outcomes, scripted future responses, evaluator facts, and audit facts do not
  enter the v1 policy decision.
- Changed files: `src/pa_rl/increment7_scenarios.py`,
  `tests/test_increment7_pilot.py`, this checkpoint, and
  `.superpowers/sdd/2026-08-18-increment7-heldout-context-plan/task-1-report.md`.
- Stable boundary: no authority, environment, evaluator, monitor, replay,
  Increment-6 result, or existing feature layout changed.
- Next exact task: add Task 2's canonical all-40 replay/negative controls and
  named public Rule only.

## Increment 7 Task 1 fix round 1 boundary

- Review finding 1 RED: the focused Task 1 command failed because the public
  task text was `Complete one protected operation.` rather than the literal
  neutral contract `Complete the requested protected task.` (`Ran 1 test in
  0.015s — FAILED`). All eight families now use that single neutral task text,
  and the same test rejects protocol-bearing authorization, future-decision,
  denial, human-owner, and escalation terms.
- Review finding 2 RED: after the text fix was GREEN, malformed
  `SuiteMember` construction did not raise (`Ran 1 test in 0.016s — FAILED`).
  `SuiteMember` now binds family, carrier, frozen split, scenario ID, and the
  complete canonical manifest. `Increment7Suite` now accepts only the exact
  8 x 5 Cartesian product with 40 unique pairs and 24/8/8 split counts while
  retaining order-independent valid construction.
- Final focused GREEN: `$env:PYTHONPATH='src'; python -m unittest
  tests.test_increment7_pilot.Increment7PilotTests.test_suite_split_and_policy_firewall_invariants
  -v` passed (`Ran 1 test in 0.153s — OK`). Targeted compilation exited 0.
- Recomputed suite hash:
  `d8ef5d5cd47b465ef88c43e89bf686ee3942334435ed8587786973fe86176eb3`.
  The frozen split did not change; split hash remains
  `79a2ac01c4c58333c38044735c50e0d2956d03a65d1f2c7585b135925baca320`.
- Changed only Task 1 source, its existing focused test method, this
  checkpoint, and the Task 1 report. Task 2+ remains untouched.
- Next exact action: independent Task 1 re-review; Task 2 must not begin before
  the corrected suite boundary is accepted.

## Increment 6 Task 1 boundary

- Genuine RED command:

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot.Increment6PilotTests.test_public_v1_full_mask_and_firewall -v
  ```

  Result: expected `ModuleNotFoundError: No module named
  'pa_rl.multiscenario_policy'`.
- GREEN: the identical focused command ran one test successfully. Targeted
  compilation (`python -m compileall -q src\pa_rl\multiscenario_policy.py
  tests\test_increment6_pilot.py`) exited 0.
- Changed files: `src/pa_rl/multiscenario_policy.py`,
  `tests/test_increment6_pilot.py`, this checkpoint, and
  `docs/implementation_reports/task-6-task1-report.md`.
- Stable scope: frozen public-only `state[75]` and full-catalog
  `candidate[N,36]` decision view, exact environment mask, semantic-ID-to-slot
  resolution, and metadata with no scenario identity or oracle/audit fields.
  No authority, execution, environment, evaluator, replay, policy-interface,
  scenario, or fixture source changed.
- Next exact task: add only Task 2's trusted pilot-outcome wrapper and the
  second focused test method. Do not expose its canonical trace through the
  public policy module.

## Increment 6 Task 2 boundary

- RED: `$env:PYTHONPATH='src'; python -m unittest
  tests.test_increment6_pilot.Increment6PilotTests.test_protocol_wrapper_rejects_shortcuts_and_accepts_canonical_traces
  -v` produced the expected missing `pa_rl.pilot_outcome` import.
- GREEN: Task 1 plus Task 2 focused methods passed (`Ran 2 tests ... OK`), and
  `python -m compileall -q src\pa_rl\pilot_outcome.py
  tests\test_increment6_pilot.py` exited 0.
- Stable scope: private canonical action/task signatures and permission choices
  are compared with selected public rows and trusted authorization audit events.
  Scenarios 1–9 require exact terminal base-reward-1 completion; scenario 10
  requires exact base-reward-0 clean truncation. Shortcut variants for 4–9 and
  a nonconforming clean scenario-10 truncation return protocol reward 0.
- Changed files: `src/pa_rl/pilot_outcome.py`, the second test method in
  `tests/test_increment6_pilot.py`, this checkpoint, and
  `docs/implementation_reports/task-6-task2-report.md`. No protected kernel,
  policy projection, replay, or fixtures changed.
- Next exact task: Task 3 DDQN dimension generalization with Increment 5
  compatibility; do not add another Increment 6 focused test method yet.

## Increment 6 design boundary

- All ten canonical fixtures were inspected against the real evaluator rather
  than the prose in their manifests.
- Seven fixtures contain a reward shortcut or missing positive outcome under
  full-action learning: scenario 4 can skip disable/refresh; scenarios 5/6 can
  replace refresh with a new request; scenarios 7--9 can terminate safely at
  the first step; scenario 10 receives no positive reward for its intended
  clean truncation.
- The current observation also omits structured public scope fields, producing
  harmful aliases for multi-scenario learning.
- Recommended next action: after user approval, write the Increment 6 design
  spec for a public observation v1 and an Increment-6-only canonical-protocol
  binary outcome wrapper. Do not edit the authority, reference monitor,
  evaluator, replay, or fixture kernel before that approval.

## Stable state before the current fix round

- B2B1 round-0 implementation passed its local focused suite, combined replay
  suite, full suite, and `compileall`, but independent adversarial review found
  five semantic gaps. Passing tests from that snapshot are **not** approval.
- Round-0 review verdict: no Critical finding; five Important findings and
  three Minor findings.
- A real-environment regression for a refresh grant-delivery fault has already
  produced a genuine RED: the legal public prefix
  `permission_requested -> permission_granted -> verified_error` was rejected
  as `public_semantics_invalid`.

## Current exact RED boundary

- Production remains unchanged from the reviewed round-0 snapshot:
  `src/pa_rl/replay.py` SHA-256
  `61C365742C89A1F42EBA815788258E667D5024B7B4C0A604DBAEBA36D2E71F83`.
- `tests/test_replay_semantics.py` now contains complete regressions for I1–I5.
  I2–I5 attacks rebuild every affected inner chain/head, observation/history,
  evaluator result/digest where applicable, and the outer trace hash; each
  attack passes `validate_episode_trace` before semantic verification.
- Minor M1 has a focused spy regression proving `_semantic_ledger` itself must
  call `AuthorizationService.replay(..., ())`; M2 now uses a reusable grant and
  asserts the real endpoint `authorization_expired -> verified_error` prefix.
- Last combined RED command:

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_replay_semantics.SemanticHappyPathTests.test_refresh_grant_delivery_fault_is_a_legal_committed_prefix tests.test_replay_semantics.SemanticHappyPathTests.test_empty_ledger_still_runs_the_authorization_replay_validator tests.test_replay_semantics.SemanticFailureBoundaryTests.test_self_asserted_finalization_change_cannot_downgrade_safe_success tests.test_replay_semantics.SemanticFailureBoundaryTests.test_verified_error_codes_require_an_independently_proven_phase tests.test_replay_semantics.SemanticFailureBoundaryTests.test_request_record_scope_is_bound_to_the_selected_candidate tests.test_replay_semantics.SemanticFailureBoundaryTests.test_endpoint_expiry_requires_the_complete_eligible_ledger_set tests.test_replay_semantics.SemanticFailureBoundaryTests.test_blocked_monitor_check_vector_is_recomputed_from_prestate -v
  ```

  Result: `Ran 7 tests`; expected `FAILED (failures=8, errors=1)`. I1 raised
  `public_semantics_invalid`; M1 found no replay call; I2 endpoint and three
  action-step subcases, I3, I4, and I5 were incorrectly accepted.
- Files changed since the prior checkpoint: `tests/test_replay_semantics.py`
  and this checkpoint only. Production is stable, not in flight.
- B2B1's next exact action remains the reviewed semantic fix, but it is paused
  under the rough-first decision and must not be confused with the active rough
  prototype path.

## Rough Increment 5 completion boundary

- Implemented the frozen public-only `state[23]` / `candidate[N,16]` encoder,
  shared candidate Q scorer, deep CPU replay snapshots, masked behavior policy,
  and masked Double-DQN target/update. Policy decisions are resolved candidate
  IDs; catalog slots are used only at the environment step boundary.
- Added exact hot-swappable JSON criteria and a Random/Rule/Tabular-Q/DDQN
  runner on `one_time_grant_success`. Reward remains the existing terminal
  `{0,1}` and all methods use the same public two-action diagnostic filter.
- Genuine RED command:

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_increment5_rough -v
  ```

  Initial result: expected import failure,
  `ModuleNotFoundError: No module named 'pa_rl.ddqn'`.
- First functioning run: exactly two tests passed in `22.440s`. Final fresh
  verification: exactly two tests passed in `20.892s`; targeted `compileall`
  exited 0.
- Frozen default: seeds `(17,29,43)`, 1,000 training transitions/seed, 200
  evaluation episodes/seed, gamma `0.9`, epsilon `0.80 -> 0.05`, Adam `1e-3`,
  batch 32, replay 2,000, warmup 64, optimize every 4 transitions, target copy
  every 100 optimizer steps, Huber loss, and gradient clip 5.0.
- Default recovery run result: mean success Random `0.2333`, Rule `1.000`,
  Tabular-Q `1.000`, DDQN `1.000`; per-seed Random `0.22/0.25/0.23` and all
  other methods `1.00`. DDQN used 235 optimizer steps per seed. Training and
  evaluation DDQN invalid selections and unauthorized committed effects were
  all zero.
- All `rough_v0` checks passed: DDQN success at least 0.90, improvement over
  Random at least 0.30, evaluation invalid actions at most 0, and evaluation
  unauthorized effects at most 0. Internal runtime `91.6692s`; shell wall time
  `94.9s`.
- Execution record: the first default invocation completed after about 74s,
  but stdout/exit code were lost because the orchestration wrapper read the
  wrong result field. Terminal recovery was unavailable. Root authorized one
  identical recovery invocation; code, criteria, seeds, and parameters were
  unchanged. The captured recovery exited 0. No tuning occurred.
- SHA-256:
  - `ddqn_features.py`: `59A316B7AC88889CE6712BBB93CC15D29C6B73F4CB4AB9B9628DDF9247119D2C`
  - `ddqn.py`: `3E071FB5B6514C7778538E7437864FE771AE0C4863132CCE3A693F942FD063EA`
  - `evaluation_criteria.py`: `E0A5D53C303DFA3958C02CD12BFBA6993E907675F9244F3A44E8DAA173AA7528`
  - `increment5_rough.py`: `16C9AAD71C447DFB57F1B4968E9876C8C48C6C1DA37E2B787C10842D338FCF0A`
  - `rough_v0.json`: `50E6EE5F018CBDD896A55E456EFE70B547D50CAD8C938AF741C76E827BEBE1C6`
  - `test_increment5_rough.py`: `89C137B65C239B0C597C82A772765DC6CEC5BABDC28BE1464E15D78FDAB10196`
  - `task-5-rough-report.md`: `464DD45E9D1D89BDBF120B59BD84B6F8DE293A3164CC496C5BD10ACFAD36D381`
  - `pyproject.toml`: `1C2B2A7DEDFE55CDAC796FB9FFA498E60C3CA552AAA28C38A39601FB450CB96E`
- Stable boundary: no B2B/replay/environment/authority/evaluator/fixture file
  changed. Next action is a human choice between a multi-scenario/formally
  matched experiment and broadening the public observation/interaction model.

## Rough Increment 4 completion boundary

- Added a dependency-free tabular Q learner and an equal-budget
  `gamma=0` versus `gamma=0.9` runner on `one_time_grant_success`.
- Q keys use the full public observation hash and resolved candidate IDs, never
  raw catalog positions. The documented toy filter uses request/deny before a
  grant and execute/deny after a grant.
- Fixed run: seeds `(17, 29, 43)`, 400 training transitions and 500 evaluation
  episodes per seed/gamma, `alpha=0.2`, epsilon `0.40 -> 0.05`, reward `0/1`.
- Result: gamma 0 mean upstream `Q(request)-Q(deny)=0.000`, success `0.504`;
  gamma 0.9 gap `0.900`, success `1.000`. The minimal delayed dependency is
  present, so environment redesign is not required at this rough gate.
- Last focused command:

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_g2_rough -v
  ```

  Final fresh result: `Ran 2 tests in 4.581s — OK`.
- Rough run command: `$env:PYTHONPATH='src'; python -m pa_rl.g2_rough`;
  exit 0 in 55.7 seconds. Targeted `compileall` exited 0.
- Files added: `src/pa_rl/baselines.py`, `src/pa_rl/g2_rough.py`,
  `tests/test_g2_rough.py`, and
  `docs/implementation_reports/task-4-rough-report.md`. This checkpoint was
  updated. No approved kernel, replay, fixture, authority, or evaluator source
  was changed.
- Frozen rough source/test SHA-256: `baselines.py`
  `6693073845D3EEEAEF7899D6B972982C0415B87B8690033072FA8D9CA9A0CD69`;
  `g2_rough.py`
  `C0F2AD39D73D673E01AC4E1116C20AE774FDC388959654CCEA367C6175EA27EF`;
  `test_g2_rough.py`
  `CB05B774C7499D8A024440A846568B0375DEE902F922BCF8018B97447B7860D6`.
  `replay.py` remains the untouched round-0 hash
  `61C365742C89A1F42EBA815788258E667D5024B7B4C0A604DBAEBA36D2E71F83`.
- Next action: choose the next rough neural baseline module while retaining the
  tabular smoke as a sanity oracle; do not call this formal G2 evidence.

## Minimal Increment 3B2 completion boundary

- Added `verify_and_replay_minimal(...) -> ReplayVerification` for built-in
  scripted-user/default-tool-plan traces only.
- The API validates the sealed schema first, constructs exactly one trusted
  default environment, resets once with the recorded seed/scenario, replays
  recorded action indices, requires exact closure, reseals, and applies
  type-sensitive whole-trace equality. Its result contains safe metadata only.
- Focused command:

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_replay_minimal -v
  ```

  Final fresh result: `Ran 3 tests in 0.518s — OK`.
- Targeted `compileall` for `replay.py` and `test_replay_minimal.py` exited 0.
- Normal terminal, fixture-10 truncation, and a structurally valid default
  tool-plan mismatch are covered. Custom adapters/tool plans and live S-QSTN
  are explicitly unsupported.
- The five known B2B1 RED hardening findings remain unchanged and were not run;
  this closes only the user-authorized minimal prototype boundary, not hardened
  semantic replay.
- Next action: retain this deterministic replay as the prototype regression
  oracle while proceeding to the next explicitly scoped rough module.

## Required fixes in this round

1. Accept only the exact legal refresh delivery-fault prefixes while rejecting
   missing-middle and post-error continuation histories.
2. Bind each `verified_error` code to an independently established cause and
   phase; in particular, prevent a forged `finalization_semantic_change` from
   downgrading an independently valid reward-1 result.
3. Bind request/refresh authorization scope, issued step, public source event,
   expiry, predecessor, and supersession tail to the selected candidate.
4. Derive the complete required `expire_eligible` event set at execution time
   and at `H+1`; preserve ledger service order and separately enforce sorted
   public expiry publication (or its exact delivery-fault prefix).
5. Independently derive blocked monitor checks and the exact failure reason
   from the pre-transition trusted task and authorization state.
6. Close the three Minor items: call authorization replay for an empty chain,
   use a reusable grant in the expiry-delivery-fault test, and update the stale
   module description.

## Resume procedure

1. Read this file and the complete B2B1 review before editing.
2. Inspect the active worker/reviewer state; do not run the same tests while the
   implementation worker is editing shared files.
3. Require fully rehashed RED tests for findings 2–5 before production fixes.
4. After the implementation worker reports a stable GREEN and stops editing,
   ask the same independent reviewer for a fix-round adversarial re-review.
5. Only after reviewer PASS, independently run from
   `ai_agent_permission_experiment/rl_personal_assistant/`:

   ```powershell
   $env:PYTHONPATH='src'; python -m unittest tests.test_replay_semantics -v
   $env:PYTHONPATH='src'; python -m unittest tests.test_environment_replay tests.test_replay_semantics -v
   $env:PYTHONPATH='src'; python -m unittest discover -s tests -v
   python -m compileall -q src tests
   ```

6. Record exact counts, failures, hashes, and reviewer verdict here and in the
   implementation report/progress log.
7. Start Task 3B2B2 only after B2B1 reviewer approval and root verification.

## Non-negotiable stop conditions

- Do not start B2B2 or claim hardened replay while B2B1 is pending. Rough Increment 4 may proceed under ADR-IMPL-010.
- Do not mark Task 3 or G1 complete before B2B2 passes independent review.
- If the future matched `gamma > 0` arm does not reliably outperform
  `gamma = 0`, stop before Deep RL and revise the environment/scenarios.
- Do not treat unkeyed trace hashes as hostile-storage origin authentication.

## Interruption protocol

Before a planned pause—or immediately after reconnecting from an unplanned
disconnect—replace the **Current checkpoint** and append a short entry below
containing:

- timestamp and phase;
- last completed action and exact command/result;
- files changed since the previous checkpoint;
- whether production files are in a stable or in-flight state;
- remaining blockers;
- one precise next action.

### Checkpoint history

- **2026-09-20 — Learner/Baseline Pilot Task 1 boundary complete; review next.** Baseline `41aeb93fe4b77bf7c989db6e5640353c884f0c95f6ee2676ffb5f110a9bfed4e`, config `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`, criteria `11abe65fd023614635def7133721861edaa9fbdf4b7a1b6afaf7c7c61ee5f5b7`, and focused test `b80025966f8178737d04ad948b095a577d16854d81e50bf0286b5a13cb64573e` were created. The single authorized RED failed only with missing `pa_rl.family3_v2_pilot_criteria`; the identical GREEN passed one test in 0.084s. No certified source/artifact changed and no formal experiment ran. Next: Task 1 review.

- **2026-09-20 — Family-3 v2 Learner/Baseline Pilot written specs formally approved; implementation plan complete and independently approved.** The exact twelve-gate artifact remains immutable. The frozen study retains the literal 5/2/3 split, adds only an external 43/7/7 adapter and separate learner runner, and compares Random-valid, forecast-ablated Rule, forecast-aware Rule, diagnostic Tabular-Q `gamma=0/1`, and Masked DDQN `gamma=0/1`. It freezes seeds 17/29/43, 12,000 transitions per learner/seed, 50 paired evaluation episodes, matched initialization/RNG derivation, validation-qualified seed cohorts, test-once recovery, and expanded exact-zero safety/integrity gates. Scientific closeout is `APPROVE`; bilingual audit is `PASS`; final plan audit is `APPROVE`. English/Chinese spec SHA-256 are `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9` and `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`; plan SHA-256 is `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`. This remains documentation-only: no learner source, test, config, smoke, training, server job, result, or API call exists. Next action is explicit user approval to execute the plan, beginning with dependency freeze and config boundary.

- **2026-08-31 — Family-3 v2 Task 7 exact preflight COMPLETE / `CERTIFIED_PASS`.**
  Fix round 3 passed independent readiness review; the ordered v2 110/110,
  legacy 68/68, and 13-module compile checks all passed once. The sole real
  run committed all 12 Gates for 10 graphs with exact initial values `4/5`
  and Q gaps `3/5`. Read-only postflight audit verified 72 fixed-root files,
  20 certificates and 20 healthy SQLite caches (314 total nonterminal rows),
  peak RSS 29.43 MiB, unchanged frozen v0/v1 evidence, and no escaped path.
  Its first helper invocation assumed the wrong table name and was corrected;
  no product or artifact failed or changed. This is an exact feasibility and
  integrity certificate, not a learner run or DDQN-advantage result.

- **2026-08-27 — Family-3 v2 design approved / bilingual spec reader-tested.**
  The user approved forecast-conditioned scope reservation as a separately
  versioned replacement construct for Family-3 research. English and Chinese
  specs freeze two legal early request scopes, deterministic public reusable
  consent terms, exact scope binding, an irreversible offer window, delayed
  exact/broader branches, ten literal graphs, and algebraic `V*=4/5` with
  request Q-gap `3/5`. Reader testing corrected runtime ambiguities including
  grant lifetime, deterministic tool commit, exact unbiased mod-5 draws,
  failure precedence, policy/raw-scope separation, seven-row masks, evidence
  allowlists, and nonemitted no-coverage guards. Final implementation-reader,
  math/FSM, and bilingual reviews all PASS with no Critical/Important findings.
  No production or experiment work began. Next action is written spec approval,
  followed by a minimal implementation plan.

- **2026-08-27 — terminal-cache-bypass diagnostic COMPLETE / VALID.** New
  isolated solver/schema/signature and seven focused tests were implemented
  with witnessed RED/GREEN. Ordered controls matched `s3_v5=1` and
  `s3_v3=13/25`; the single fresh `s3_v4` run certified exact value `1` with
  193,537 cached nonterminal rows, 1,053,226 terminal returns, and no resume.
  Fresh adjacent regression ran 18 tests with zero failures; targeted
  compilation exited 0. SQLite/certificate/signature/source provenance passed
  local and independent read-only verification; final artifact verdict VALID.
  Production is stable and no process is active. Family-3 v1 remains rejected
  solely because v3 is below `3/5`; next action requires a separately approved
  Family-3 v2 task-definition design, not another target/exposure search.

- **2026-08-18 — Increment 6 frozen pilot PARITY / documentation complete.**
  The one authorized default execution completed in 1,001.810 seconds with
  seeds 17/29/43 and is preserved at
  `results/increment6_multiscenario_v0/`. DDQN macro base/protocol success was
  `0.867/0.800`, versus Rule `0.900/0.900`, Tabular-Q `0.867/0.867`, and
  Random `0.163/0.054`. All required gates passed: DDQN improved on Random by
  0.746, was 0.100 below best simple (allowed), solved 7/10 scenarios at the
  0.80 protocol threshold, and had zero invalid actions/unauthorized effects.
  The separate 0.05 Deep-RL advantage check failed (DDQN was 0.100 below Rule),
  producing PARITY; prefer Rule on this deterministic canonical suite. The
  temporary protocol wrapper is a benchmark oracle, not policy/replay input or
  a final reward. No retraining is authorized. B2B1 hardening debt, held-out
  evaluation, uncertainty analysis, and broader RL/Deep-RL claims remain open.

- **2026-08-18 — Increment 6 Task 4 record fix GREEN.** Before the default
  pilot, the result now retains JSON-serializable per-seed/per-method metrics
  and aggregates each scenario's outcome kinds rather than dropping them. The
  CLI additionally writes the non-self-hashing `run_manifest.json` required by
  the plan, with environment provenance, config/criteria/fixture hashes,
  optimizer steps, runtime, and the result-file SHA-256. This is artifact
  bookkeeping only: learning, policies, rule tensor indices, configuration,
  gate, and fixture behavior are unchanged. `$env:PYTHONPATH='src'; python -m
  unittest tests.test_increment6_pilot -v` passed (`Ran 3 tests in 17.509s`)
  and targeted compilation exited zero. The default pilot remains unrun; next
  action is the single frozen Task 5 execution.

- **2026-08-18 — Increment 6 Task 4 GREEN.** Added the exact replaceable
  `multiscenario_v0` gate profile, strict criteria/classification module, and
  ten-scenario full-action Random/Rule/Tabular/DDQN runner. The runner uses
  public v1 tensors and semantic IDs with the exact environment mask, keeps one
  Tabular/DDQN learner per seed, schedules exact per-scenario round-robin
  transition quotas, and uses the trusted protocol wrapper only as reward.
  The third and final focused Increment-6 method captured the missing-runner
  RED, then passed with `(7,)`, 80 transitions/scenario, and five evaluation
  episodes/scenario. `$env:PYTHONPATH='src'; python -m unittest
  tests.test_increment6_pilot -v` passed (`Ran 3 tests in 17.974s`), targeted
  compilation exited zero, and `$env:PYTHONPATH='src'; python -m unittest
  tests.test_increment5_rough tests.test_g2_rough -v` passed (`Ran 4 tests in
  27.235s`). Changed: `configs/evaluation/multiscenario_v0.json`,
  `src/pa_rl/multiscenario_criteria.py`, `src/pa_rl/increment6_pilot.py`,
  `tests/test_increment6_pilot.py`, and
  `docs/implementation_reports/task-6-task4-report.md`. The frozen default
  pilot has not been run; next action is explicitly authorized Task 5 execution
  exactly once, followed by stop-rule reporting.

- **2026-08-18 — Increment 6 Task 3 GREEN.** `DDQNModelSpec` makes the
  learner's state, candidate, and padded-action dimensions configurable while
  retaining exact Increment-5 defaults and state-dict layout. It accepts both
  legacy candidate IDs and v1 semantic candidate IDs through a structural
  tensor decision surface. `$env:PYTHONPATH='src'; python -m unittest
  tests.test_increment5_rough -v` passed (`Ran 2 tests in 23.946s`), and
  `python -m compileall -q src\pa_rl\ddqn.py` exited 0. Changed production:
  `src/pa_rl/ddqn.py`; report: `docs/implementation_reports/task-6-task3-report.md`.
  Production is stable. The combined Increment-6 integration checks remain the
  separate Task 2/runner boundary; no DDQN retuning is authorized.

- **2026-08-17 — B2B1 fix round 1 started.** Round-0 review is complete and
  recorded. One legal-prefix RED is confirmed. The worker is adding fully
  rehashed RED cases for the remaining findings; production must not be treated
  as stable until the worker reports the next boundary. Next action: obtain the
  exact RED matrix, then implement only the reviewed semantic fixes.
- **2026-08-17 — I1–I5 RED boundary complete.** Seven focused regression
  methods now reproduce all five Important findings plus M1; M2 was corrected
  to exercise a real reusable-grant expiry delivery fault. Production has not
  yet changed. Next action: minimal semantic verifier fix, followed by focused
  GREEN and full verification.
- **2026-08-17 — Rough-first pivot.** At the user's direction, B2B1 production
  repair stopped before edits; its RED tests and review remain as deferred
  hardening evidence. The next action is a minimal tabular Q-learning smoke run
  on the approved 3B1 environment, comparing `gamma=0` with `gamma>0`. Testing
  is limited to essential smoke and hand-checkable correctness checks.
- **2026-08-17 — Rough Increment 4 smoke complete.** Two focused tests passed,
  the three-seed equal-budget run produced a zero upstream margin for gamma 0
  and a 0.9 margin for gamma 0.9, and no approved kernel source changed. Next
  action: retain this as a rough sanity baseline and begin only the next
  explicitly scoped prototype module.
- **2026-08-17 — Minimal Increment 3B2 complete.** Canonical/default terminal
  and truncation traces now fresh-replay through exactly one environment/reset
  and must reseal to an identical trace. Three focused tests and targeted
  compilation pass. B2B1/B2B2 hardening remains deferred and no full-suite
  green claim is made.
- **2026-08-18 — Increment 5 design approved.** The user approved a minimal
  public-only candidate-scoring Masked Double DQN, replaceable criteria JSON,
  and Random/Rule/Tabular/DDQN rough comparison. The implementation is limited
  to two focused tests and one fixed run. If the functioning model misses the
  gate, record NO-GO and stop without tuning.
- **2026-08-18 — Increment 5 rough PASS.** The required missing-API RED was
  followed by two focused GREEN tests and clean targeted compilation. Under the
  frozen three-seed run, DDQN/Rule/Tabular each reached 1.000 success versus
  Random 0.2333, with zero DDQN evaluation invalid selections or unauthorized
  committed effects; every replaceable gate check passed. A root-authorized
  identical recovery run was needed only because the first run's stdout was
  dropped by the orchestration wrapper. Next action: human selection of the
  next experimental scope; do not present this as formal Deep-RL evidence.
- **2026-08-18 — Increment 6 audit complete.** The ten-scenario audit found
  seven base-reward shortcuts/missing outcomes and a structured-observation
  gap. No production code was changed. The recommended implementation is a
  pilot-only canonical-protocol binary outcome wrapper plus public observation
  v1; user approval is the next exact action.
- **2026-08-18 — Increment 6 Task 2 GREEN.** The tracker accepts all ten
  canonical traces, rejects required shortcuts, and preserves the oracle outside
  policy/replay inputs. Both current focused Increment 6 tests and targeted
  compilation pass. Next: Task 3 only.

```