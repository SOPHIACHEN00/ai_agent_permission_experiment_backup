"""Compile Twin-2K summaries × frozen permission conditions into QSTN personas.

This creates research-constructed synthetic agents.  A selected policy condition
is not claimed to be an observed trait or answer history of the Twin participant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_CARDS = (
    PROJECT_ROOT / "config" / "empirical_profile_prompt_cards_v2.json"
)
QUESTION_PLACEHOLDER = "{{QUESTION_PLACEHOLDER}}"
EXPECTED_POLICY_IDS = {
    "persistent_granters",
    "reconsent_seekers",
    "broad_restrictors",
}
SYSTEM_PROMPT = (
    "You are simulating a research-constructed synthetic survey respondent. "
    "Answer only from the supplied general persona, permission-policy condition, "
    "and permission scenario. The policy condition is assigned by researchers and "
    "does not describe an observed privacy history of the person underlying the "
    "general persona. Do not invent personal facts, prior approvals, motivations, "
    "or purposes."
)


def utc_now() -> str:
    """Return a timezone-aware timestamp suitable for manifests."""
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    """Calculate a stable content hash without loading an entire file at once."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write UTF-8 JSON with deterministic human-readable formatting."""
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def read_twin_table(path: Path) -> pd.DataFrame:
    """Read only the two Twin fields used by this construction."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        source = pd.read_csv(path, usecols=["pid", "persona_summary"])
    elif suffix in {".parquet", ".pq"}:
        source = pd.read_parquet(path, columns=["pid", "persona_summary"])
    else:
        raise ValueError("Twin input must be a .csv, .parquet, or .pq table.")

    required = {"pid", "persona_summary"}
    missing = required.difference(source.columns)
    if missing:
        raise ValueError(f"Twin input is missing columns: {sorted(missing)}")
    if source["pid"].isna().any():
        raise ValueError("Twin input contains an empty pid.")
    if source["persona_summary"].isna().any():
        raise ValueError("Twin input contains an empty persona_summary.")

    twin = source.rename(columns={"pid": "twin_id"}).copy()
    twin["twin_id"] = twin["twin_id"].astype(str).str.strip()
    twin["general_persona"] = twin["persona_summary"].astype(str).str.strip()
    twin = twin[["twin_id", "general_persona"]]
    if (twin["twin_id"] == "").any() or (twin["general_persona"] == "").any():
        raise ValueError("Twin ids and persona summaries must be non-empty after trimming.")
    if twin["twin_id"].duplicated().any():
        duplicates = twin.loc[twin["twin_id"].duplicated(), "twin_id"].head(5).tolist()
        raise ValueError(f"Twin ids must be unique; examples of duplicates: {duplicates}")
    return twin


def load_policy_cards(path: Path) -> dict[str, Any]:
    """Load the frozen three-condition policy card configuration."""
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {"card_version", "cards"}
    missing = required.difference(config)
    if missing:
        raise ValueError(f"Policy-card configuration is missing keys: {sorted(missing)}")
    cards = config["cards"]
    if not isinstance(cards, list) or not cards:
        raise ValueError("Policy-card configuration must contain a non-empty cards list.")

    required_card = {"profile_id", "profile_name", "prompt_card"}
    policy_ids: list[str] = []
    for card in cards:
        missing_card = required_card.difference(card)
        if missing_card:
            raise ValueError(
                f"Policy-card entry is missing keys: {sorted(missing_card)}"
            )
        if QUESTION_PLACEHOLDER in str(card["prompt_card"]):
            raise ValueError("A policy condition may not contain the QSTN placeholder.")
        policy_ids.append(str(card["profile_id"]))

    if len(policy_ids) != len(set(policy_ids)):
        raise ValueError("Policy-condition ids must be unique.")
    if set(policy_ids) != EXPECTED_POLICY_IDS:
        raise ValueError(
            "This compiler requires exactly the three approved permission conditions: "
            f"expected={sorted(EXPECTED_POLICY_IDS)}, found={sorted(policy_ids)}"
        )
    shared_rule = str(config.get("shared_decision_rule", "")).strip()
    if QUESTION_PLACEHOLDER in shared_rule:
        raise ValueError("The shared decision rule may not contain the QSTN placeholder.")
    config["shared_decision_rule"] = shared_rule
    return config


def deterministic_twin_subset(
    twin: pd.DataFrame, max_twins: int, seed: int
) -> pd.DataFrame:
    """Choose a reproducible subset independently of source row order."""
    if max_twins < 0:
        raise ValueError("--max-twins must be zero (all) or a positive integer.")
    if max_twins == 0 or max_twins >= len(twin):
        return twin.sort_values("twin_id", kind="stable").reset_index(drop=True)

    ranked = twin.copy()
    ranked["_selection_key"] = ranked["twin_id"].map(
        lambda twin_id: hashlib.sha256(f"{seed}:{twin_id}".encode("utf-8")).hexdigest()
    )
    return (
        ranked.sort_values(["_selection_key", "twin_id"], kind="stable")
        .head(max_twins)
        .drop(columns="_selection_key")
        .reset_index(drop=True)
    )


def truncate_persona(text: str, maximum_characters: int) -> tuple[str, bool]:
    """Optionally cap prompt size while retaining an auditable truncation flag."""
    if maximum_characters < 0:
        raise ValueError("--max-general-persona-chars must be zero (no cap) or positive.")
    if maximum_characters == 0 or len(text) <= maximum_characters:
        return text, False
    return text[:maximum_characters].rstrip(), True


def make_questionnaire_instruction(
    general_persona: str, policy_condition: str, shared_rule: str
) -> str:
    """Create the fixed portion of a QSTN single-item permission survey prompt."""
    shared_rule_section = (
        "\n\nShared privacy decision rule:\n" + shared_rule if shared_rule else ""
    )
    return (
        "Answer each AI-agent data-sharing permission question as this "
        "research-constructed synthetic agent would. The general persona provides "
        "broad contextual background. The permission-policy condition is an explicit "
        "decision prior supplied by the study design, not a claim about the Twin "
        "person's observed permission history. Apply it as a tendency rather than a "
        "hard rule, evaluate the exact data item, tool, and task separately, and do "
        "not invent missing facts or purposes. Choose exactly one offered option.\n\n"
        "General persona (Twin-2K persona_summary):\n"
        f"{general_persona}\n\n"
        "Permission-policy condition (research-assigned):\n"
        f"{policy_condition}"
        f"{shared_rule_section}\n\n"
        "Permission scenario:\n"
        f"{QUESTION_PLACEHOLDER}"
    )


def compile_personas(
    twin: pd.DataFrame, policy_config: dict[str, Any], max_persona_characters: int
) -> pd.DataFrame:
    """Return one explicitly labeled synthetic agent for every Twin × condition pair."""
    rows: list[dict[str, Any]] = []
    for twin_row in twin.itertuples(index=False):
        original_persona = str(twin_row.general_persona)
        general_persona, was_truncated = truncate_persona(
            original_persona, max_persona_characters
        )
        for card in policy_config["cards"]:
            policy_id = str(card["profile_id"])
            policy_name = str(card["profile_name"])
            policy_text = str(card["prompt_card"])
            synthetic_agent_id = f"twin_{twin_row.twin_id}__policy_{policy_id}"
            questionnaire_instruction = make_questionnaire_instruction(
                general_persona,
                policy_text,
                str(policy_config["shared_decision_rule"]),
            )
            if questionnaire_instruction.count(QUESTION_PLACEHOLDER) != 1:
                raise RuntimeError(
                    "Synthetic questionnaire instruction must contain exactly one placeholder."
                )
            rows.append(
                {
                    "persona_id": synthetic_agent_id,
                    "synthetic_agent_id": synthetic_agent_id,
                    "persona_kind": "synthetic_twin_cross_permission_policy",
                    "questionnaire_name": "permission_survey",
                    "twin_id": str(twin_row.twin_id),
                    "general_persona_source": "Twin-2K persona_summary",
                    "general_persona_chars_original": len(original_persona),
                    "general_persona_chars_used": len(general_persona),
                    "general_persona_truncated": was_truncated,
                    "general_persona": general_persona,
                    "policy_condition_id": policy_id,
                    "policy_condition_name": policy_name,
                    "policy_condition_source": "frozen_permission_policy_card",
                    "policy_condition_card_version": str(policy_config["card_version"]),
                    "policy_condition_text": policy_text,
                    "shared_decision_rule": str(policy_config["shared_decision_rule"]),
                    "persona_text": (
                        "General persona (Twin-2K persona_summary):\n"
                        f"{general_persona}\n\n"
                        "Permission-policy condition (research-assigned; not an observed "
                        "Twin trait):\n"
                        f"{policy_text}"
                    ),
                    "system_prompt": SYSTEM_PROMPT,
                    "questionnaire_instruction": questionnaire_instruction,
                    "synthetic_agent_claim_boundary": (
                        "This Twin × policy-condition pair is a study-constructed "
                        "synthetic agent, not an observed individual-level match."
                    ),
                }
            )
    compiled = pd.DataFrame(rows)
    if compiled.empty:
        raise ValueError("No synthetic personas were compiled.")
    if compiled["synthetic_agent_id"].duplicated().any():
        raise RuntimeError("Synthetic agent ids must be unique.")
    return compiled.sort_values(
        ["twin_id", "policy_condition_id"], kind="stable"
    ).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--twin-personas",
        required=True,
        type=Path,
        help="Local CSV/Parquet with Twin-2K columns pid and persona_summary.",
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="New directory for the compiled QSTN persona table and manifest.",
    )
    parser.add_argument(
        "--policy-cards",
        type=Path,
        default=DEFAULT_POLICY_CARDS,
        help="Frozen three-condition policy-card JSON. Defaults to empirical V2 cards.",
    )
    parser.add_argument(
        "--max-twins",
        type=int,
        default=0,
        help="Compile a deterministic subset; zero (default) compiles every supplied Twin.",
    )
    parser.add_argument(
        "--selection-seed",
        type=int,
        default=20260724,
        help="Seed used only when --max-twins selects a subset.",
    )
    parser.add_argument(
        "--max-general-persona-chars",
        type=int,
        default=0,
        help="Optional prompt-size cap; zero (default) preserves every persona_summary character.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing prior compiler outputs in --out.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.twin_personas.is_file():
        raise FileNotFoundError(f"Twin input does not exist: {args.twin_personas}")
    if not args.policy_cards.is_file():
        raise FileNotFoundError(f"Policy-card configuration does not exist: {args.policy_cards}")

    output_files = [
        args.out / "twin_synthetic_personas.csv",
        args.out / "twin_synthetic_persona_manifest.json",
        args.out / "twin_synthetic_policy_conditions.json",
    ]
    existing = [path for path in output_files if path.exists()]
    if existing and not args.overwrite:
        raise FileExistsError(
            "Compiler output already exists. Choose a new --out or pass --overwrite: "
            + ", ".join(str(path) for path in existing)
        )

    supplied_twin = read_twin_table(args.twin_personas)
    twin = deterministic_twin_subset(supplied_twin, args.max_twins, args.selection_seed)
    policy_config = load_policy_cards(args.policy_cards)
    compiled = compile_personas(twin, policy_config, args.max_general_persona_chars)

    expected_count = len(twin) * len(policy_config["cards"])
    if len(compiled) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} Twin × condition personas, got {len(compiled)}."
        )
    conditions_per_twin = compiled.groupby("twin_id")["policy_condition_id"].nunique()
    if not (conditions_per_twin == len(EXPECTED_POLICY_IDS)).all():
        raise RuntimeError("Every selected Twin must receive all three policy conditions.")

    args.out.mkdir(parents=True, exist_ok=True)
    persona_path = args.out / "twin_synthetic_personas.csv"
    manifest_path = args.out / "twin_synthetic_persona_manifest.json"
    conditions_path = args.out / "twin_synthetic_policy_conditions.json"
    compiled.to_csv(persona_path, index=False, encoding="utf-8")
    write_json(
        conditions_path,
        {
            "policy_condition_card_version": policy_config["card_version"],
            "policy_condition_source_file": str(args.policy_cards.resolve()),
            "policy_condition_source_sha256": sha256_file(args.policy_cards),
            "shared_decision_rule": policy_config["shared_decision_rule"],
            "cards": policy_config["cards"],
        },
    )
    manifest = {
        "status": "compiled",
        "compiled_at_utc": utc_now(),
        "api_called": False,
        "construction": {
            "general_persona": "Twin-2K persona_summary",
            "permission_policy_condition": sorted(EXPECTED_POLICY_IDS),
            "synthetic_agent": "(twin_id, policy_condition)",
            "response_contract": "QSTN(general_persona, policy_condition, scenario)",
        },
        "scientific_boundary": (
            "The cross-product is research-constructed. A policy condition is not "
            "claimed to be an observed property, permission record, or response of a "
            "Twin participant. Generated outputs are not human ground truth."
        ),
        "source": {
            "twin_personas_file": str(args.twin_personas.resolve()),
            "twin_personas_sha256": sha256_file(args.twin_personas),
            "fields_read": ["pid", "persona_summary"],
            "policy_cards_file": str(args.policy_cards.resolve()),
            "policy_cards_sha256": sha256_file(args.policy_cards),
        },
        "selection": {
            "supplied_twin_count": int(len(supplied_twin)),
            "compiled_twin_count": int(len(twin)),
            "max_twins": args.max_twins,
            "selection_seed": args.selection_seed,
        },
        "persona_summary_handling": {
            "max_general_persona_chars": args.max_general_persona_chars,
            "truncated_persona_count": int(compiled["general_persona_truncated"].sum()),
        },
        "policy_condition_card_version": policy_config["card_version"],
        "policy_condition_ids": sorted(EXPECTED_POLICY_IDS),
        "compiled_synthetic_agent_count": int(len(compiled)),
        "compiler_output_sha256": sha256_file(persona_path),
    }
    write_json(manifest_path, manifest)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
