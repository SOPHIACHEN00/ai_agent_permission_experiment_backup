"""Offline validation helpers for QSTN permission prompts."""

from __future__ import annotations

from qstn.inference.multimodal import prompt_content_text
from qstn.prompt_builder import LLMPrompt
from qstn.utilities.constants import QuestionnairePresentation


LABELS = {
    "No, never share",
    "No, but ask me next time",
    "Yes, but ask me next time",
    "Yes, always share",
}


def validate_rendered_prompt(prompt: LLMPrompt) -> str:
    """Ensure QSTN renders the scenario and all constrained options before inference."""
    item = prompt.get_question(0)
    _, rendered_prompt = prompt.get_prompt_for_questionnaire_type(
        QuestionnairePresentation.SINGLE_ITEM,
        item_id=item.item_id,
    )
    rendered_text = prompt_content_text(rendered_prompt)
    expected_question = prompt.generate_question_prompt(item)
    if expected_question not in rendered_text:
        raise ValueError("QSTN did not insert the permission question into the prompt.")
    missing_labels = sorted(label for label in LABELS if label not in rendered_text)
    if missing_labels:
        raise ValueError(f"QSTN prompt is missing answer options: {missing_labels}")
    return rendered_text
