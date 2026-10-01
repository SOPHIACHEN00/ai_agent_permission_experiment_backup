"""Label-free, static S-QSTN v2 prompt assembly for the ICL pilot.

The backend reads existing simulator assets and renders one question at a time.
It never calls a model, writes an artifact, or feeds a supplied human answer into
the prompt. Every question starts with a new state store and an empty event list.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from importlib.metadata import version as package_version
import json
from pathlib import Path
import sys
from typing import Any, Mapping


LABELS = (
    "No, never share",
    "No, but ask me next time",
    "Yes, but ask me next time",
    "Yes, always share",
)
BACKEND_VERSION = "1.0.1"
CONTEXT_FIELDS = (
    "query_id",
    "domain",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
)


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def parse_answer(raw: str) -> tuple[str, int]:
    """Parse exactly one QSTN JSON answer using the benchmark's label order."""
    if not isinstance(raw, str):
        raise ValueError("The model response must be a JSON string.")
    try:
        value = json.loads(raw, object_pairs_hook=_json_object)
    except json.JSONDecodeError as exc:
        raise ValueError("The model response is not valid JSON.") from exc
    if not isinstance(value, dict) or set(value) != {"answer"}:
        raise ValueError("Expected a JSON object containing only the 'answer' key.")
    answer = value["answer"]
    if not isinstance(answer, str) or answer not in LABELS:
        raise ValueError(f"Unsupported permission label: {answer!r}")
    return answer, LABELS.index(answer)


def _text(row: Mapping[str, Any], field: str) -> str:
    if field not in row or row[field] is None:
        raise ValueError(f"Missing required context field: {field}")
    text = " ".join(str(row[field]).strip().split())
    if not text or text.lower() in {"nan", "<na>"}:
        raise ValueError(f"Empty required context field: {field}")
    return text


def _context_key(row: Mapping[str, Any]) -> tuple[str, ...]:
    values = [_text(row, field) for field in CONTEXT_FIELDS]
    try:
        values[0] = str(int(values[0]))
    except ValueError as exc:
        raise ValueError("query_id must be an integer.") from exc
    return tuple(values)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class SQSTNBackend:
    """Render static prompts from ``project_dir / 'qstn_simulator'`` assets."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.simulator_dir = self.project_dir / "qstn_simulator"
        if not self.simulator_dir.is_dir():
            raise FileNotFoundError(f"Missing simulator directory: {self.simulator_dir}")
        if str(self.simulator_dir) not in sys.path:
            sys.path.insert(0, str(self.simulator_dir))

        # Import only rendering/compiler helpers; none of the API smoke runners.
        import pandas as pd
        from qstn.inference.multimodal import prompt_content_text
        from qstn.prompt_builder import LLMPrompt
        from qstn.utilities.constants import QuestionnairePresentation
        from scripts.build_qstn_inputs import clean_text
        from scripts.qstn_prompt_validation import LABELS as QSTN_LABELS
        from scripts.qstn_prompt_validation import validate_rendered_prompt
        from scripts.v1.compile_s_qstn_v1 import validate_inputs
        from scripts.v1_1.compile_s_qstn_v1_1 import validate_context
        from scripts.v1_1.rulepack_v1_1 import normalize_context_v1_1
        from scripts.v2 import rulepack_v2
        from scripts.v2.compile_s_qstn_v2 import context_for_question

        if set(LABELS) != set(QSTN_LABELS):
            raise ValueError("QSTN and the pilot disagree on the four permission labels.")
        self._pd = pd
        self._prompt_class = LLMPrompt
        self._presentation = QuestionnairePresentation.SINGLE_ITEM
        self._prompt_content_text = prompt_content_text
        self._validate_prompt = validate_rendered_prompt
        self._context_for_question = context_for_question
        self._clean_text = clean_text
        self._rules = rulepack_v2
        self.behavior_mode = "stateful_audit_compatible"
        self.skill_mode = "active_excerpt"

        output_dir = self.simulator_dir / "outputs"
        config_dir = self.simulator_dir / "config" / "v2.0"
        assets = {
            "personas": output_dir / "empirical_personas_v2" / "personas_with_empirical_profiles.csv",
            "questionnaire": output_dir / "questionnaire_items.csv",
            "context": output_dir / "questionnaire_context_v1.1.csv",
            "rulepack": config_dir / "security_behavior_rules.json",
            "contract": config_dir / "respondent_contract.en.md",
            "skill_catalog": config_dir / "privacy_security_rule_skill.md",
            "context_schema": config_dir / "context_schema.json",
            "event_schema": config_dir / "event_schema.json",
            "state_schema": config_dir / "state_schema.json",
            "retention_policy": config_dir / "retention_policy.json",
            "reason_codes": config_dir / "reason_codes.json",
            "backend_source": Path(__file__).resolve(),
            "question_builder_source": self.simulator_dir / "scripts" / "build_qstn_inputs.py",
            "prompt_validation_source": self.simulator_dir / "scripts" / "qstn_prompt_validation.py",
            "v1_rulepack_source": self.simulator_dir / "scripts" / "v1" / "rulepack_v1.py",
            "v1_1_rulepack_source": self.simulator_dir / "scripts" / "v1_1" / "rulepack_v1_1.py",
            "v2_rulepack_source": self.simulator_dir / "scripts" / "v2" / "rulepack_v2.py",
            "v2_state_store_source": self.simulator_dir / "scripts" / "v2" / "state_store_v2.py",
            "v2_compiler_source": self.simulator_dir / "scripts" / "v2" / "compile_s_qstn_v2.py",
        }
        for name, path in assets.items():
            if not path.is_file():
                raise FileNotFoundError(f"Missing S-QSTN asset {name}: {path}")

        personas = pd.read_csv(assets["personas"], keep_default_na=False)
        questionnaire = pd.read_csv(assets["questionnaire"], keep_default_na=False)
        context_frame = pd.read_csv(assets["context"], keep_default_na=False)
        validate_inputs(personas, questionnaire)
        validate_context(context_frame)
        self._personas: dict[str, dict[str, Any]] = {}
        persona_ids: set[str] = set()
        for persona in personas.to_dict(orient="records"):
            participant_id = _text(persona, "participant_id")
            persona_id = _text(persona, "persona_id")
            for field in ("profile_id", "questionnaire_name", "system_prompt", "questionnaire_instruction"):
                _text(persona, field)
            if participant_id in self._personas or persona_id in persona_ids:
                raise ValueError("Persona participant_id and persona_id must each be unique.")
            self._personas[participant_id] = persona
            persona_ids.add(persona_id)

        self._sidecar = {
            _text(item, "questionnaire_item_id"): item
            for item in context_frame.to_dict(orient="records")
        }
        if len(self._sidecar) != len(context_frame):
            raise ValueError("Normalized sidecar item IDs must be unique.")
        self._questions: dict[tuple[str, ...], dict[str, Any]] = {}
        question_ids: set[str] = set()
        for question in questionnaire.to_dict(orient="records"):
            item_id = _text(question, "questionnaire_item_id")
            key = (*_context_key(question), _text(question, "question_content"))
            if key in self._questions or item_id in question_ids:
                raise ValueError(f"Duplicate full questionnaire context or item ID: {item_id}")
            if item_id not in self._sidecar:
                raise ValueError(f"Missing context sidecar for questionnaire item: {item_id}")
            sidecar_row = self._sidecar[item_id]
            missing_context = set(CONTEXT_FIELDS).difference(sidecar_row)
            if missing_context:
                raise ValueError(f"Sidecar context fields missing for {item_id}: {sorted(missing_context)}")
            # The sidecar compiler canonicalizes unknown sentinels (for example,
            # generic_data_type='Unknown' becomes 'unknown'). Reuse that exact
            # normalization here while retaining strict equality for known text.
            question_context = normalize_context_v1_1(
                {field: question[field] for field in CONTEXT_FIELDS}
            )
            sidecar_context = normalize_context_v1_1(
                {field: sidecar_row[field] for field in CONTEXT_FIELDS}
            )
            if _context_key(sidecar_context) != _context_key(question_context):
                raise ValueError(f"Questionnaire and sidecar contexts disagree: {item_id}")
            if json.loads(str(question["answer_texts"])) != list(LABELS):
                raise ValueError(f"Questionnaire answer order differs from the benchmark: {item_id}")
            if str(question["response_generation_method"]) != "json_single":
                raise ValueError(f"Expected json_single response method: {item_id}")
            self._questions[key] = question
            question_ids.add(item_id)
        if set(self._sidecar) != question_ids:
            raise ValueError("Context sidecar must cover exactly the questionnaire item IDs.")
        if not self._personas or not self._questions:
            raise ValueError("Persona and questionnaire assets must not be empty.")

        self._rulepack = rulepack_v2.load_v2_rulepack(assets["rulepack"])
        self._contract = rulepack_v2.load_v2_contract(assets["contract"])
        self._skill = rulepack_v2.load_v2_skill(assets["skill_catalog"])
        context_schema = rulepack_v2.load_v2_context_schema(assets["context_schema"])
        self._event_schema = rulepack_v2.load_v2_event_schema(assets["event_schema"])
        self._state_schema = rulepack_v2.load_v2_state_schema(assets["state_schema"])
        self._retention_policy = rulepack_v2.load_v2_retention_policy(assets["retention_policy"])
        reason_codes = rulepack_v2.load_v2_reason_codes(assets["reason_codes"])
        if not self._contract or not self._skill or not reason_codes.get("codes"):
            raise ValueError("Contract, skill catalog, and reason-code assets must be nonempty.")
        self._metadata = {
            "backend_version": BACKEND_VERSION,
            "project_dir": str(self.project_dir),
            "simulator_dir": str(self.simulator_dir),
            "qstn_version": package_version("qstn"),
            "rulepack_version": str(self._rulepack["version"]),
            "parent_rulepack_version": str(self._rulepack["parent_rule_pack_version"]),
            "respondent_contract_version": "respondent_contract_v2.0.en",
            "skill_catalog_version": str(self._rulepack.get("skill_catalog_version", "2.0.0")),
            "context_schema_version": str(context_schema["version"]),
            "state_schema_version": str(self._state_schema["version"]),
            "profile_card_versions": sorted(set(personas["profile_card_version"].astype(str))),
            "behavior_mode": self.behavior_mode,
            "skill_mode": self.skill_mode,
            "generation_mode": "static_independent_single_item",
            "events": [],
            "state_reset": "new_empty_state_for_each_question",
            "subject_id_source": "persona_id",
            "current_turn": 0,
            "memory_horizon_turns": 0,
            "memory_horizon_source": "static_pilot_empty_history",
            "memory_fixture": None,
            "human_answer_columns_used": False,
            "human_calibration": "not_claimed",
            "context_match_fields": [*CONTEXT_FIELDS, "query"],
            "context_match_normalization": "source clean_text whitespace normalization; integer query_id",
            "sidecar_comparison_normalization": "source normalize_context_v1_1 unknown sentinels; known text remains exact",
            "input_rows_modified": False,
            "labels": list(LABELS),
            "persona_count": len(self._personas),
            "questionnaire_item_count": len(self._questions),
            "asset_paths": {name: str(path) for name, path in assets.items()},
            "input_hashes": {name: _sha256(path) for name, path in assets.items()},
        }

    def metadata(self) -> dict[str, Any]:
        """Return the asset/version snapshot captured when this backend was loaded."""
        return deepcopy(self._metadata)

    def messages_for(self, participant_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
        """Render one question using context fields only, ignoring answer columns."""
        participant_id = str(participant_id)
        if participant_id not in self._personas:
            raise ValueError(f"No empirical persona for participant: {participant_id!r}")
        if "participant_id" in row and _text(row, "participant_id") != participant_id:
            raise ValueError("The row participant_id differs from the requested participant.")
        query = _text(row, "query")
        tool = _text(row, "tool")
        raw_data_type = _text(row, "raw_data_type")
        question_content = (
            f"User request: {self._clean_text(query)}\n"
            f"Tool: {self._clean_text(tool)}\n"
            f"Data item requested: {self._clean_text(raw_data_type)}"
        )
        key = (*_context_key(row), self._clean_text(question_content))
        if key not in self._questions:
            raise ValueError(f"No questionnaire item matches the full supplied context: {key!r}")
        question = dict(self._questions[key])
        item_id = str(question["questionnaire_item_id"])
        if "questionnaire_item_id" in row and _text(row, "questionnaire_item_id") != item_id:
            raise ValueError("The supplied questionnaire_item_id disagrees with the full context.")
        persona = self._personas[participant_id]
        persona_id = str(persona["persona_id"])
        profile_id = str(persona["profile_id"])
        _, memory_view, transition_audit = self._rules.build_memory_view(
            event_schema=self._event_schema,
            state_schema=self._state_schema,
            retention_policy=self._retention_policy,
            events=[],
            subject_id=persona_id,
            current_turn=0,
            memory_horizon_turns=0,
            memory_horizon_source="static_pilot_empty_history",
        )
        if transition_audit or memory_view.get("visible_events"):
            raise RuntimeError("Static prompt assembly unexpectedly created memory events.")
        context = self._context_for_question(question, profile_id, self._sidecar)
        rendered_rules, evaluations, _ = self._rules.render_v2_rule_context(
            self._rulepack, context, memory_view, behavior_mode=self.behavior_mode
        )
        instruction = self._rules.inject_v2_context(
            str(persona["questionnaire_instruction"]),
            self._contract,
            rendered_rules,
            skill_text=self._skill,
            skill_mode=self.skill_mode,
        )
        prompt = self._prompt_class(
            questionnaire_source=self._pd.DataFrame([question]),
            questionnaire_name=str(persona["questionnaire_name"]),
            system_prompt=str(persona["system_prompt"]),
            prompt=instruction,
        )
        rendered_user = self._validate_prompt(prompt)
        rendered_system, rendered_content = prompt.get_prompt_for_questionnaire_type(
            self._presentation, item_id=item_id
        )
        if self._prompt_content_text(rendered_content) != rendered_user:
            raise RuntimeError("QSTN's validated prompt differs from the rendered content.")
        if not isinstance(rendered_system, str) or not rendered_system.strip():
            raise RuntimeError("QSTN did not render a nonempty system prompt.")
        for marker in (
            "Respondent contract v2.0:",
            "RulePack 2.0 bounded memory and categorical state:",
        ):
            if marker not in rendered_user:
                raise RuntimeError(f"The QSTN prompt is missing required context: {marker}")
        return {
            "messages": [
                {"role": "system", "content": rendered_system},
                {"role": "user", "content": rendered_user},
            ],
            "questionnaire_item_id": item_id,
            "profile_id": profile_id,
            "persona_id": persona_id,
            "memory_view": memory_view,
            "active_rule_ids": [item.rule_id for item in evaluations if item.status == "active"],
            "rulepack_version": str(self._rulepack["version"]),
        }
