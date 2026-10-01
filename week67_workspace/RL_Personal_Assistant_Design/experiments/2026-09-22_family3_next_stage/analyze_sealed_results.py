"""Read-only archive analysis. Prints derived JSON/CSV; never runs a policy or env."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "ai_agent_permission_experiment/rl_personal_assistant_cuda_v1"
SDD = ROOT / "ai_agent_permission_experiment/.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot"
ARCHIVES = {
    "validation": (
        SDD / "server-formal/formal_evidence/formal_train_validate_v0_evidence.zip",
        "773fd06e1d3c03073713e080e54f1ff35480fd7daa39250b17b9aa84d884fc52",
        "formal_results", 4200, 100,
    ),
    "test": (
        SDD / "server-test/formal_test_evidence/formal_test_once_evidence.zip",
        "78ab4a43601799f90aeea06243d07420ef4a991216a70e8acb0890c066dac5e0",
        "formal_root", 6300, 23,
    ),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def table(header, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue()


def main():
    provenance = {
        "schema_version": "family3_v2_sealed_reanalysis_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_kind": "post_hoc_read_only_record_analysis_not_new_evaluation",
        "path_base": "Week67 workspace root",
        "script_sha256": digest(Path(__file__).read_bytes()),
        "archives": [],
    }
    phases = {}
    checkpoints = []
    source_bytes = None
    for phase, (path, expected_hash, prefix, expected_rows, expected_entries) in ARCHIVES.items():
        actual_hash = digest(path.read_bytes())
        assert actual_hash == expected_hash, (phase, "archive hash mismatch")
        with zipfile.ZipFile(path) as archive:
            assert len(archive.namelist()) == expected_entries
            frozen_source = archive.read(prefix + "/source_manifest.json")
            if source_bytes is not None:
                assert source_bytes == frozen_source, "train/test source manifests differ"
            source_bytes = frozen_source
            source = json.loads(frozen_source)
            for relative, sha, size in source["entries"]:
                local = (PROJECT / relative).resolve()
                assert local.is_relative_to(PROJECT.resolve())
                raw = local.read_bytes()
                assert len(raw) == size and digest(raw) == sha, relative
            member = prefix + "/" + phase + "/rows.jsonl"
            raw_rows = archive.read(member)
            records = [json.loads(line) for line in raw_rows.splitlines() if line]
            assert len(records) == expected_rows
            previous = "0" * 64
            coordinates = set()
            for sequence, record in enumerate(records):
                assert record["sequence"] == sequence
                assert record["previous_record_sha256"] == previous
                assert record["payload_sha256"] == digest(canonical(record["payload"]))
                prefix_record = {key: value for key, value in record.items() if key != "record_sha256"}
                assert record["record_sha256"] == digest(canonical(prefix_record))
                coord = tuple(record["coordinate_key"])
                assert coord not in coordinates
                coordinates.add(coord)
                payload = record["payload"]
                assert coord == tuple(payload[key] for key in (
                    "method_id", "evaluation_seed", "graph_id", "condition", "episode_ordinal"
                ))
                assert payload["phase"] == phase
                previous = record["record_sha256"]
            phases[phase] = [record["payload"] for record in records]
            provenance["archives"].append({
                "phase": phase, "path": path.relative_to(ROOT).as_posix(),
                "sha256": actual_hash, "byte_size": path.stat().st_size,
                "zip_entries": expected_entries, "rows_member": member,
                "rows_sha256": digest(raw_rows), "rows": len(records),
                "unique_coordinates": len(coordinates), "row_chain_verified": True,
                "source_files_verified": len(source["entries"]),
            })
            if phase == "validation":
                names = sorted(n for n in archive.namelist() if
                    "/attempts/0001/" in n and n.endswith("checkpoint_manifest.json"))
                for name in names:
                    manifest = json.loads(archive.read(name))
                    relative, sha, size = manifest["payload_ref"]
                    raw = archive.read(prefix + "/" + relative)
                    assert len(raw) == size and digest(raw) == sha
                    row = {
                        "method_id": manifest["method_id"],
                        "seed": manifest["training_seed"],
                        "transitions": manifest["training_metadata"]["transition_count"],
                        "payload_sha256": sha, "payload_bytes": size,
                        "fingerprint": manifest["evaluation_fingerprint_sha256"],
                    }
                    if row["method_id"].startswith("masked_ddqn"):
                        algo = manifest["algorithm_metadata"]
                        row.update({
                            "gamma": float.fromhex(algo["hyperparameters"]["gamma"]),
                            "optimizer_steps": manifest["training_metadata"]["optimizer_steps"],
                            "online_changed_from_initial": algo["online_state_sha256"] !=
                                dict(manifest["initial_state_hashes"])["ddqn_online"],
                        })
                    checkpoints.append(row)
    assert len(checkpoints) == 12
    assert sum(row["transitions"] for row in checkpoints) == 144000
    provenance["checkpoints"] = checkpoints

    # Only import verified pure schema/registry/RNG modules, never torch, runner, or env.
    sys.path.insert(0, str(PROJECT / "src"))
    from pa_rl.family3_v2_suite import build_family3_v2_suite
    from pa_rl.family3_v2_rng import draw_family3_v2_branch_residue, continuation_from_residue
    graphs = {graph.graph_id: graph for graph in build_family3_v2_suite().graphs}
    summaries, seed_summaries, paired_summaries = [], [], []
    diagnostics = {}
    for phase, rows in phases.items():
        methods = defaultdict(list)
        seeded = defaultdict(list)
        for row in rows:
            methods[row["method_id"]].append(row)
            seeded[(row["method_id"], row["evaluation_seed"])].append(row)
        for method, selected in sorted(methods.items()):
            successes = sum(row["terminal_success"] for row in selected)
            summaries.append([phase, method, successes, len(selected), successes / len(selected)])
        for (method, seed), selected in sorted(seeded.items()):
            successes = sum(row["terminal_success"] for row in selected)
            seed_summaries.append([phase, method, seed, successes, len(selected), successes / len(selected)])
        coord = lambda row: tuple(row[key] for key in
            ("evaluation_seed", "graph_id", "condition", "episode_ordinal"))
        learner = {coord(row): row for row in methods["masked_ddqn_gamma1"]}
        rule = {coord(row): row for row in methods["forecast_rule"]}
        assert learner.keys() == rule.keys()
        comparisons = {
            key: sum(learner[c][key] != rule[c][key] for c in learner)
            for key in ("root_seed", "root_semantic_candidate_id", "terminal_success",
                        "prompt_count", "termination_kind", "decision_count")
        }
        forecast_errors = outcome_errors = 0
        for row in learner.values():
            graph = graphs[row["graph_id"]]
            p_exact, p_broader = graph.forecast_exact_probability, graph.forecast_broader_probability
            if row["condition"] != "original":
                p_exact, p_broader = p_broader, p_exact
            preferred = "request_narrow" if p_exact > p_broader else "request_broader"
            forecast_errors += row["root_semantic_candidate_id"] != preferred
            residue = draw_family3_v2_branch_residue(
                row["root_seed"], graph.branch_coupling_uid, row["episode_ordinal"]
            ).residue
            branch = continuation_from_residue(p_exact, p_broader, residue)
            predicted = int((preferred == "request_narrow") == (branch.value == "exact"))
            outcome_errors += row["terminal_success"] != predicted
        interventions = defaultdict(dict)
        for row in learner.values():
            key = (row["evaluation_seed"], row["graph_id"], row["episode_ordinal"])
            interventions[key][row["condition"]] = row["root_semantic_candidate_id"]
        assert all(len(pair) == 2 for pair in interventions.values())
        flips = sum(len(set(pair.values())) == 2 for pair in interventions.values())
        hard = Counter()
        for row in rows:
            hard.update(row["hard_counts"])
        diagnostics[phase] = {
            "paired_ddqn_vs_forecast_episodes": len(learner),
            "ddqn_vs_forecast_mismatch_counts": comparisons,
            "forecast_formula_action_mismatches": forecast_errors,
            "realized_branch_formula_success_mismatches": outcome_errors,
            "counterfactual_pairs": len(interventions), "counterfactual_action_flips": flips,
            "ddqn_failure_terminations": dict(Counter(row["termination_kind"] for row in
                learner.values() if not row["terminal_success"])),
            "rule_failure_terminations": dict(Counter(row["termination_kind"] for row in
                rule.values() if not row["terminal_success"])),
            "row_hard_counts": dict(hard),
        }
        paired_summaries.append([phase, len(learner), *comparisons.values(),
                                 forecast_errors, outcome_errors, len(interventions), flips])
    provenance["execution_boundary"] = {
        "new_training": False, "new_evaluation": False, "environment_steps": 0,
        "network_or_api_calls": 0, "checkpoint_deserialization": False,
        "frozen_artifact_writes": False,
    }
    output = {
        "provenance": provenance, "diagnostics": diagnostics,
        "method_summary_csv": table(["phase", "method", "successes", "episodes", "success_rate"], summaries),
        "seed_summary_csv": table(["phase", "method", "training_or_pairing_seed", "successes", "episodes", "success_rate"], seed_summaries),
        "paired_summary_csv": table([
            "phase", "paired_episodes", "root_seed_mismatches", "initial_action_mismatches",
            "success_mismatches", "prompt_count_mismatches", "termination_kind_mismatches",
            "decision_count_mismatches", "forecast_formula_mismatches", "branch_formula_mismatches",
            "counterfactual_pairs", "counterfactual_action_flips",
        ], paired_summaries),
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
