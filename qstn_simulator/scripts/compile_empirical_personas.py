"""Compile discovery-only empirical profiles into auditable QSTN persona prompts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT_ROOT / "outputs"
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "empirical_profile_prompt_cards.json"
QUESTION_PLACEHOLDER = "{{QUESTION_PLACEHOLDER}}"
SYSTEM_PROMPT = (
    "You are simulating a survey participant. Answer only from the supplied "
    "empirical permission-response profile, participant background, and permission "
    "scenario. Do not invent personal facts or purposes."
)
EVIDENCE_COLUMNS = [
    "always_allow_rate",
    "ask_yes_rate",
    "ask_no_rate",
    "never_share_rate",
    "necessary_request_share_score",
    "explicitly_unnecessary_request_share_score",
    "ask_next_time_rate",
    "necessity_discrimination",
    "n_participants",
]


def load_card_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required_keys = {
        "card_version",
        "source_profile_method",
        "source_response_split",
        "prompt_text_status",
        "intended_use",
        "cards",
    }
    missing = required_keys.difference(config)
    if missing:
        raise ValueError(f"Prompt-card configuration is missing keys: {sorted(missing)}")
    if not isinstance(config["cards"], list) or not config["cards"]:
        raise ValueError("Prompt-card configuration must contain a non-empty cards list.")
    required_card_keys = {"profile_id", "profile_name", "prompt_card"}
    for card in config["cards"]:
        missing_card_keys = required_card_keys.difference(card)
        if missing_card_keys:
            raise ValueError(
                f"Prompt-card entry is missing keys: {sorted(missing_card_keys)}"
            )
        if QUESTION_PLACEHOLDER in str(card["prompt_card"]):
            raise ValueError("Prompt cards must not contain the questionnaire placeholder.")
    profile_ids = [str(card["profile_id"]) for card in config["cards"]]
    if len(profile_ids) != len(set(profile_ids)):
        raise ValueError("Prompt-card profile ids must be unique.")
    shared_decision_rule = str(config.get("shared_decision_rule", "")).strip()
    if QUESTION_PLACEHOLDER in shared_decision_rule:
        raise ValueError("The shared decision rule must not contain the questionnaire placeholder.")
    config["shared_decision_rule"] = shared_decision_rule
    return config


def validate_inputs(
    base_personas: pd.DataFrame,
    assignments: pd.DataFrame,
    centers: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    required_base_columns = {
        "persona_id",
        "participant_id",
        "questionnaire_name",
        "persona_text",
    }
    required_assignment_columns = {
        "participant_id",
        "profile_id",
        "profile_name",
        "selected_k",
    }
    required_center_columns = {"profile_id", "profile_name", *EVIDENCE_COLUMNS}
    for name, frame, required_columns in [
        ("base personas", base_personas, required_base_columns),
        ("profile assignments", assignments, required_assignment_columns),
        ("profile centers", centers, required_center_columns),
    ]:
        missing = required_columns.difference(frame.columns)
        if missing:
            raise ValueError(f"{name} is missing columns: {sorted(missing)}")
    if base_personas["participant_id"].duplicated().any():
        raise ValueError("Base persona participant ids must be unique.")
    if assignments["participant_id"].duplicated().any():
        raise ValueError("Profile assignment participant ids must be unique.")
    if centers["profile_id"].duplicated().any():
        raise ValueError("Profile center ids must be unique.")
    selected_k = set(pd.to_numeric(assignments["selected_k"], errors="raise"))
    if selected_k != {3}:
        raise ValueError(f"Expected selected_k=3 profile assignments, got {selected_k}.")
    center_profiles = set(centers["profile_id"].astype(str))
    card_profiles = {str(card["profile_id"]) for card in config["cards"]}
    if center_profiles != card_profiles:
        raise ValueError(
            "Prompt-card ids must exactly match learned center ids: "
            f"centers={sorted(center_profiles)}, cards={sorted(card_profiles)}"
        )
    for center in centers.itertuples(index=False):
        card = next(
            candidate
            for candidate in config["cards"]
            if candidate["profile_id"] == center.profile_id
        )
        if card["profile_name"] != center.profile_name:
            raise ValueError(
                f"Prompt-card name for {center.profile_id} does not match learned center."
            )
    if set(base_personas["participant_id"].astype(str)) != set(
        assignments["participant_id"].astype(str)
    ):
        raise ValueError("Base personas and empirical profile assignments disagree on participants.")


def make_questionnaire_instruction(
    prompt_card: str, participant_background: str, shared_decision_rule: str = ""
) -> str:
    shared_rule_section = (
        "\n\nShared privacy decision rule:\n" + shared_decision_rule
        if shared_decision_rule
        else ""
    )
    return (
        "Answer each AI-agent data-sharing permission question as this participant "
        "would. Apply the stable empirical permission-response profile as a behavioral "
        "tendency and use the participant background only as supplied context. Choose "
        "exactly one option.\n\n"
        "Stable empirical permission-response profile:\n"
        f"{prompt_card}"
        f"{shared_rule_section}\n\n"
        "Participant background:\n"
        f"{participant_background}\n\n"
        "Permission scenario:\n"
        f"{QUESTION_PLACEHOLDER}"
    )


def make_prototype_instruction(prompt_card: str, shared_decision_rule: str = "") -> str:
    shared_rule_section = (
        "\n\nShared privacy decision rule:\n" + shared_decision_rule
        if shared_decision_rule
        else ""
    )
    return (
        "Answer each AI-agent data-sharing permission question as this canonical "
        "empirical profile would. Apply the profile as a behavioral tendency; it is not "
        "a license to invent facts or motivations. Choose exactly one option.\n\n"
        "Stable empirical permission-response profile:\n"
        f"{prompt_card}"
        f"{shared_rule_section}\n\n"
        "Additional participant background: Not supplied for this canonical prototype.\n\n"
        "Permission scenario:\n"
        f"{QUESTION_PLACEHOLDER}"
    )


def compile_participant_personas(
    base_personas: pd.DataFrame,
    assignments: pd.DataFrame,
    cards: dict[str, dict[str, Any]],
    card_version: str,
    shared_decision_rule: str,
) -> pd.DataFrame:
    profile_columns = assignments[
        [
            "participant_id",
            "profile_id",
            "profile_name",
            "cluster_id",
            "n_discovery_responses",
            "n_heldout_responses",
            "selected_k",
        ]
    ].copy()
    merged = base_personas.merge(
        profile_columns,
        on="participant_id",
        how="left",
        validate="one_to_one",
    )
    merged["profile_card_version"] = card_version
    merged["profile_card_source"] = "discovery_only_empirical_cluster"
    merged["profile_card_text"] = merged["profile_id"].map(
        {profile_id: card["prompt_card"] for profile_id, card in cards.items()}
    )
    if merged["profile_card_text"].isna().any():
        raise ValueError("A participant was not assigned a prompt card.")
    merged["base_persona_text"] = merged["persona_text"]
    merged["persona_text"] = merged.apply(
        lambda row: (
            "Empirical permission-response profile:\n"
            f"{row['profile_card_text']}\n\n"
            "Participant background:\n"
            f"{row['base_persona_text']}"
        ),
        axis=1,
    )
    merged["system_prompt"] = SYSTEM_PROMPT
    merged["questionnaire_instruction"] = merged.apply(
        lambda row: make_questionnaire_instruction(
            row["profile_card_text"], row["base_persona_text"], shared_decision_rule
        ),
        axis=1,
    )
    if merged["questionnaire_instruction"].str.contains(
        QUESTION_PLACEHOLDER, regex=False
    ).eq(False).any():
        raise ValueError("A participant persona is missing the QSTN question placeholder.")
    return merged


def compile_prototypes(
    centers: pd.DataFrame,
    cards: dict[str, dict[str, Any]],
    card_version: str,
    shared_decision_rule: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for center in centers.sort_values("profile_id").itertuples(index=False):
        card = cards[center.profile_id]
        rows.append(
            {
                "persona_id": f"prototype_{center.profile_id}",
                "persona_kind": "canonical_empirical_profile",
                "questionnaire_name": "permission_survey",
                "system_prompt": SYSTEM_PROMPT,
                "questionnaire_instruction": make_prototype_instruction(
                    card["prompt_card"], shared_decision_rule
                ),
                "persona_text": (
                    "Empirical permission-response profile:\n" + card["prompt_card"]
                ),
                "profile_id": center.profile_id,
                "profile_name": center.profile_name,
                "profile_card_version": card_version,
                "profile_card_source": "discovery_only_empirical_cluster_center",
                "n_discovery_cluster_members": int(center.n_participants),
                **{
                    column: float(getattr(center, column))
                    for column in EVIDENCE_COLUMNS
                    if column != "n_participants"
                },
            }
        )
    return pd.DataFrame(rows)


def build_cards_artifact(
    config: dict[str, Any], centers: pd.DataFrame
) -> dict[str, Any]:
    center_lookup = centers.set_index("profile_id")
    cards: list[dict[str, Any]] = []
    for configured_card in config["cards"]:
        center = center_lookup.loc[configured_card["profile_id"]]
        cards.append(
            {
                **configured_card,
                "n_discovery_cluster_members": int(center["n_participants"]),
                "learned_center_evidence": {
                    column: float(center[column])
                    for column in EVIDENCE_COLUMNS
                    if column != "n_participants"
                },
            }
        )
    return {
        key: value for key, value in config.items() if key != "cards"
    } | {"cards": cards}


def write_report(
    path: Path,
    config: dict[str, Any],
    centers: pd.DataFrame,
    participant_personas: pd.DataFrame,
    prototypes: pd.DataFrame,
) -> None:
    lines = [
        "# Empirical Profile to QSTN Persona Compilation",
        "",
        "## 目的",
        "",
        "本步骤把 discovery-only K=3 的经验型权限回答画像编译为 QSTN 可读取的 prompt inputs。它不调用 LLM API，也不使用 held-out 标签。",
        "",
        "## 学到的内容与人工内容",
        "",
        "- **从数据学到**：participant-to-profile assignment、三个 profile 的 cluster center、群组人数。",
        "- **人工编写但受证据约束**：英文 prompt card 的自然语言措辞。它只总结中心中可观察到的授权持久性、再次确认倾向、总体限制倾向和必要性区分；不包含具体回答比例。",
        "- **不声称学到**：心理人格、动机、风险偏好或人口总体比例。",
        "",
        "## QSTN 接入方式",
        "",
        "QSTN 没有独立的 persona inference 模块。每一个 persona 是一个 `LLMPrompt`，其中固定的 `system_prompt` 和 `questionnaire_instruction` 会与 `{{QUESTION_PLACEHOLDER}}` 所渲染的 permission scenario 一起发送给模型。",
        "",
        "## 输出",
        "",
        f"- `personas_with_empirical_profiles.csv`：{len(participant_personas)} 个校准用 persona。每人保留匿名背景字段，并附上仅由其 discovery 回答得到的 profile card。",
        f"- `qstn_empirical_profile_prototypes.csv`：{len(prototypes)} 个 canonical prototype persona，用于后续 simulator/RL 设计；不包含真实参与者背景。",
        "- `empirical_profile_cards.json`：prompt card、其版本和从 cluster centers 自动导出的证据审计记录。",
        "",
        "## 三张卡的审计摘要",
        "",
    ]
    card_lookup = {card["profile_id"]: card for card in config["cards"]}
    for center in centers.sort_values("profile_name").itertuples(index=False):
        lines.extend(
            [
                f"### {center.profile_name} (n={int(center.n_participants)})",
                "",
                card_lookup[center.profile_id]["prompt_card"],
                "",
            ]
        )
    lines.extend(
        [
            "## 评价边界",
            "",
            "后续校准必须仅使用 held-out response rows。应比较 raw participant profile only 与 raw participant profile plus empirical profile card，避免把 profile card 的作用与基础人口/AI 自报字段混为一谈。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--base-personas", type=Path)
    parser.add_argument("--assignments", type=Path)
    parser.add_argument("--centers", type=Path)
    args = parser.parse_args()

    base_path = args.base_personas or args.out / "personas.csv"
    assignment_path = args.assignments or args.out / "empirical_profile_assignments.csv"
    center_path = args.centers or args.out / "empirical_profile_centers.csv"
    config = load_card_config(args.config)
    base_personas = pd.read_csv(base_path)
    assignments = pd.read_csv(assignment_path)
    centers = pd.read_csv(center_path)
    validate_inputs(base_personas, assignments, centers, config)

    cards = {str(card["profile_id"]): card for card in config["cards"]}
    participant_personas = compile_participant_personas(
        base_personas,
        assignments,
        cards,
        str(config["card_version"]),
        str(config["shared_decision_rule"]),
    )
    prototypes = compile_prototypes(
        centers,
        cards,
        str(config["card_version"]),
        str(config["shared_decision_rule"]),
    )
    cards_artifact = build_cards_artifact(config, centers)

    args.out.mkdir(parents=True, exist_ok=True)
    participant_personas.to_csv(
        args.out / "personas_with_empirical_profiles.csv", index=False, encoding="utf-8"
    )
    prototypes.to_csv(
        args.out / "qstn_empirical_profile_prototypes.csv", index=False, encoding="utf-8"
    )
    (args.out / "empirical_profile_cards.json").write_text(
        json.dumps(cards_artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_report(
        args.out / "EMPIRICAL_PERSONA_COMPILATION_REPORT_zh.md",
        config,
        centers,
        participant_personas,
        prototypes,
    )
    summary = {
        "card_version": config["card_version"],
        "source_profile_method": config["source_profile_method"],
        "source_response_split": config["source_response_split"],
        "participant_personas": int(len(participant_personas)),
        "prototype_personas": int(len(prototypes)),
        "profile_ids": sorted(cards),
        "question_placeholder": QUESTION_PLACEHOLDER,
        "label_leakage_guard": (
            "Profile cards use discovery-only assignments; held-out labels are not "
            "read by this compiler."
        ),
    }
    (args.out / "empirical_persona_compilation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
