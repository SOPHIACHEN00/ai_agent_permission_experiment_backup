"""Provider-neutral adapter to the current standalone S-QSTN default interface.

Only the generator sees calibrated reference evidence and the synthetic profile.
The ICL predictor receives neither. No API calls, dotenv access or artifact writes.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
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
BACKEND_VERSION = "current_retrieval_calibrated"


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def parse_answer(raw: str) -> tuple[str, int]:
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


class SQSTNBackend:
    """Use s-qstn's public RetrievalSimulator, never an old compiler snapshot."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.simulator_dir = self.project_dir / "s-qstn"
        if not (self.simulator_dir / "sqstn" / "__init__.py").is_file():
            raise FileNotFoundError(f"Missing current S-QSTN package: {self.simulator_dir}")
        sys.path.insert(0, str(self.simulator_dir))
        import sqstn
        if not Path(sqstn.__file__).resolve().is_relative_to(self.simulator_dir.resolve()):
            raise RuntimeError("A different sqstn package is already loaded")
        if tuple(sqstn.LABELS) != LABELS:
            raise ValueError("S-QSTN and ICL label order differ")
        self._simulator = sqstn.RetrievalSimulator(self.simulator_dir)
        assets = {}
        for directory in ("sqstn", "config", "data"):
            for path in sorted((self.simulator_dir / directory).rglob("*")):
                if "__pycache__" in path.parts or not path.is_file():
                    continue
                if path.name == ".env" or path.name.startswith(".env."):
                    raise RuntimeError("Credential file found inside simulator assets")
                if directory == "sqstn" and path.suffix != ".py":
                    continue
                assets[path.relative_to(self.simulator_dir).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._metadata = {
            "backend_version": BACKEND_VERSION,
            "simulator_dir": str(self.simulator_dir),
            "public_interface": "sqstn.RetrievalSimulator.compile",
            "generation_mode": "static_independent_single_item",
            "user_definition": "stable synthetic sample_id with frozen population profile assignment",
            "state_reset": "empty_memory_per_question",
            "human_demographics_used": False,
            "generator_uses_reference_human_answers": True,
            "evaluation_row_labels_used": False,
            "predictor_receives_profile_rules_references": False,
            "calibration": deepcopy(self._simulator.calibration),
            "reference_corpus": deepcopy(self._simulator.corpus.manifest),
            "input_hashes": assets,
            "labels": list(LABELS),
        }

    def metadata(self) -> dict[str, Any]:
        return deepcopy(self._metadata)

    def profile_for(self, participant_id: str) -> str:
        if not str(participant_id).strip():
            raise ValueError("Synthetic user id must not be empty")
        return self._simulator.profile_for(str(participant_id))

    def messages_for(self, participant_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
        participant_id = str(participant_id)
        if "participant_id" in row and _text(row, "participant_id") != participant_id:
            raise ValueError("Row belongs to another synthetic user")
        query = _text(row, "query")
        tool = _text(row, "tool")
        data = _text(row, "raw_data_type")
        try:
            query_id = int(_text(row, "query_id"))
        except ValueError as exc:
            raise ValueError("query_id must be an integer") from exc
        key = (str(query_id), tool, data)
        question = self._simulator.wrapper.questions.get(key)
        expected = f"User request: {query}\nTool: {tool}\nData item requested: {data}"
        if question is None or question["question_content"] != expected:
            raise ValueError("No exact original Wu query/tool/data match")
        if "questionnaire_item_id" in row and _text(row, "questionnaire_item_id") != question["questionnaire_item_id"]:
            raise ValueError("Questionnaire item id differs from the supplied context")
        profile = self.profile_for(participant_id)
        compiled = self._simulator.compile(profile, query_id, tool, data, sample_id=participant_id)
        return {
            **compiled,
            "profile_id": profile,
            "persona_id": participant_id,
            "rulepack_version": compiled["rule_audit"]["version"],
        }
