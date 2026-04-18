# preferences_agent.py

from __future__ import annotations

import json
import re
from typing import Any, Dict

from app.services.llm_client import llm_call


ALLOWED_VALUES = {
    "job_style_preference": {"thinking", "hands_on", "unclear"},
    "work_environment_preference": {"team", "alone", "mixed", "unclear"},
    "preferred_field": {"humanities", "science", "hands_on_work", "arts", "unclear"},
    "self_learning_comfort": {"yes", "no", "unclear"},
    "long_learning_willingness": {"yes", "no", "unclear"},
    "learning_structure_preference": {"structured", "flexible", "mixed", "unclear"},
    "openness_to_new_fields": {"yes", "no", "unclear"},
}

ALLOWED_CONFIDENCE = {"low", "medium", "high"}


DEFAULT_RESULT = {
    "agent_name": "preferences_agent",
    "job_style_preference": "unclear",
    "work_environment_preference": "unclear",
    "preferred_field": "unclear",
    "self_learning_comfort": "unclear",
    "long_learning_willingness": "unclear",
    "learning_structure_preference": "unclear",
    "openness_to_new_fields": "unclear",
    "confidence": "low",
    "short_reason": "Could not reliably determine user preferences from the provided answers.",
}


def build_preferences_profile(
    *,
    job_style_preference: str,
    work_environment_preference: str,
    preferred_field: str,
    self_learning_comfort: str,
    long_learning_willingness: str,
    learning_structure_preference: str,
    openness_to_new_fields: str,
) -> dict[str, Any]:
    return {
        "job_style_preference": job_style_preference,
        "work_environment_preference": work_environment_preference,
        "preferred_field": preferred_field,
        "self_learning_comfort": self_learning_comfort,
        "long_learning_willingness": long_learning_willingness,
        "learning_structure_preference": learning_structure_preference,
        "openness_to_new_fields": openness_to_new_fields,
    }


def _extract_json_text(raw: str) -> str:
    """
    Accept either:
    - pure JSON
    - fenced markdown block like ```json ... ```
    - text that contains a JSON object
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Preferences Agent returned empty output")

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1].strip()

    return raw


def _normalize_yes_no(value: Any) -> str:
    if value is None:
        return "unclear"

    text = str(value).strip().lower()

    if text in {"yes", "y", "true", "comfortable", "open", "willing"}:
        return "yes"
    if text in {"no", "n", "false", "uncomfortable", "not_open", "not willing"}:
        return "no"

    if "yes" in text:
        return "yes"
    if "no" in text:
        return "no"

    return "unclear"


def _normalize_job_style(value: Any) -> str:
    if value is None:
        return "unclear"

    text = str(value).strip().lower()

    if text in {"thinking", "mental", "intellectual", "analytical"}:
        return "thinking"
    if text in {"hands_on", "hands-on", "practical", "manual"}:
        return "hands_on"

    if "hands" in text or "practical" in text or "manual" in text:
        return "hands_on"
    if "think" in text or "analytic" in text or "mental" in text:
        return "thinking"

    return "unclear"


def _normalize_work_environment(value: Any) -> str:
    if value is None:
        return "unclear"

    text = str(value).strip().lower()

    if text in {"team", "teamwork", "group"}:
        return "team"
    if text in {"alone", "independent", "solo"}:
        return "alone"
    if text in {"mixed", "both"}:
        return "mixed"

    if "team" in text or "group" in text:
        return "team"
    if "alone" in text or "solo" in text or "independent" in text:
        return "alone"
    if "both" in text or "mixed" in text:
        return "mixed"

    return "unclear"


def _normalize_preferred_field(value: Any) -> str:
    if value is None:
        return "unclear"

    text = str(value).strip().lower()

    mapping = {
        "humanities": "humanities",
        "science": "science",
        "hands_on_work": "hands_on_work",
        "hands-on work": "hands_on_work",
        "hands_on": "hands_on_work",
        "practical": "hands_on_work",
        "arts": "arts",
        "art": "arts",
    }

    if text in mapping:
        return mapping[text]

    if "humanit" in text:
        return "humanities"
    if "science" in text:
        return "science"
    if "hands" in text or "practical" in text or "manual" in text:
        return "hands_on_work"
    if "art" in text:
        return "arts"

    return "unclear"


def _normalize_learning_structure(value: Any) -> str:
    if value is None:
        return "unclear"

    text = str(value).strip().lower()

    if text in {"structured", "guided"}:
        return "structured"
    if text in {"flexible", "self_paced", "self-paced"}:
        return "flexible"
    if text in {"mixed", "both"}:
        return "mixed"

    if "structured" in text or "guided" in text:
        return "structured"
    if "flexible" in text or "self-paced" in text or "self paced" in text:
        return "flexible"
    if "both" in text or "mixed" in text:
        return "mixed"

    return "unclear"


def normalize_preferences_agent_output(output: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(output, dict):
        raise ValueError("Preferences Agent output must be a JSON object")

    normalized = {
        "agent_name": "preferences_agent",
        "job_style_preference": _normalize_job_style(output.get("job_style_preference")),
        "work_environment_preference": _normalize_work_environment(output.get("work_environment_preference")),
        "preferred_field": _normalize_preferred_field(output.get("preferred_field")),
        "self_learning_comfort": _normalize_yes_no(output.get("self_learning_comfort")),
        "long_learning_willingness": _normalize_yes_no(output.get("long_learning_willingness")),
        "learning_structure_preference": _normalize_learning_structure(output.get("learning_structure_preference")),
        "openness_to_new_fields": _normalize_yes_no(output.get("openness_to_new_fields")),
        "confidence": output.get("confidence", "medium"),
        "short_reason": output.get("short_reason", ""),
    }

    if normalized["confidence"] not in ALLOWED_CONFIDENCE:
        normalized["confidence"] = "medium"

    if not isinstance(normalized["short_reason"], str):
        normalized["short_reason"] = str(normalized["short_reason"])

    normalized["short_reason"] = normalized["short_reason"].strip()[:300]

    return normalized


def validate_preferences_agent_output(data: dict[str, Any]) -> dict[str, Any]:
    required_keys = {
        "agent_name",
        "job_style_preference",
        "work_environment_preference",
        "preferred_field",
        "self_learning_comfort",
        "long_learning_willingness",
        "learning_structure_preference",
        "openness_to_new_fields",
        "confidence",
        "short_reason",
    }

    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Missing keys: {sorted(missing)}")

    if data["agent_name"] != "preferences_agent":
        raise ValueError("agent_name must be 'preferences_agent'")

    for key in [
        "job_style_preference",
        "work_environment_preference",
        "preferred_field",
        "self_learning_comfort",
        "long_learning_willingness",
        "learning_structure_preference",
        "openness_to_new_fields",
    ]:
        if data[key] not in ALLOWED_VALUES[key]:
            raise ValueError(f"Invalid value in {key}: {data[key]}")

    if data["confidence"] not in ALLOWED_CONFIDENCE:
        raise ValueError("invalid confidence")

    if not isinstance(data["short_reason"], str):
        raise ValueError("short_reason must be a string")

    return data


def analyze_preferences_profile(
    profile: dict[str, Any],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    system_prompt = """
You are Preferences Agent in a career-choice system for young people without higher education.

Your task:
1. Analyze ONLY the user's work style and learning preferences.
2. Classify each preference into the allowed enum values.
3. Return strict JSON only.

Rules:
- Use only the allowed enum values.
- If the answer is ambiguous, use "unclear".
- If the user seems to like both team and alone, use "mixed".
- If the user seems to like both structured and flexible learning, use "mixed".
- "hands-on work" must be returned as "hands_on_work".
- "hands-on" job style must be returned as "hands_on".
- Keep short_reason to 1–2 sentences.
- Return valid JSON only.
- Do not wrap the JSON in markdown fences.

Return exactly this schema:
{
  "agent_name": "preferences_agent",
  "job_style_preference": "thinking",
  "work_environment_preference": "team",
  "preferred_field": "science",
  "self_learning_comfort": "yes",
  "long_learning_willingness": "yes",
  "learning_structure_preference": "structured",
  "openness_to_new_fields": "yes",
  "confidence": "medium",
  "short_reason": "The user prefers analytical work, science-related directions, and a structured learning path."
}
""".strip()

    user_prompt = f"""
User preferences profile JSON:
{json.dumps(profile, ensure_ascii=False, indent=2)}
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    kwargs = {"model": model} if model else {}
    raw = llm_call(messages, max_new_tokens=250, **kwargs)

    json_text = _extract_json_text(raw)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Preferences Agent returned invalid JSON:\n{raw}") from e

    parsed = normalize_preferences_agent_output(parsed)
    return validate_preferences_agent_output(parsed)