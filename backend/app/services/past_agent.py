from __future__ import annotations

import json
import re
from typing import Any

from app.services.llm_client import llm_call
from app.services.field_vocab import (
    CANONICAL_FIELDS,
    MAIN_SCHOOL_FOCUS,
    SUBJECT_FIELDS,
    YES_NO_PREFER_NOT,
    YES_NO_UNSURE,
)


FORBIDDEN_NON_FIELD_VALUES = {"degree", "course", "uncertain"}
ALLOWED_DEGREE_OR_COURSE = {"degree", "course", "uncertain"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


SCIENCE_FIELDS = {
    "computer_science",
    "data_science",
    "mathematics",
    "engineering",
    "biology",
    "chemistry",
    "physics",
    "medicine",
    "psychology",
}

HUMANITIES_FIELDS = {
    "history",
    "literature",
    "law",
    "education",
    "humanities_general",
}

ARTS_FIELDS = {
    "design_arts",
    "drama",
}


def _unique_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result


def _focus_to_fields(main_school_focus: str) -> set[str]:
    if main_school_focus == "science":
        return SCIENCE_FIELDS
    if main_school_focus == "humanities":
        return HUMANITIES_FIELDS
    if main_school_focus == "arts":
        return ARTS_FIELDS
    return set()


def _extract_json_text(raw: str) -> str:
    """
    Accept either:
    - pure JSON
    - fenced markdown block like ```json ... ```
    - text that contains a JSON object
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Past Agent returned empty output")

    # Case 1: fenced json block
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    # Case 2: raw contains a JSON object somewhere
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1].strip()

    return raw


def build_past_profile(
    *,
    country: str,
    has_high_school_graduation: str,
    wants_to_continue_same_field: str,
    main_school_focus: str,
    advanced_subjects: list[str],
    favorite_subjects: list[str],
    best_subjects: list[str],
) -> dict[str, Any]:
    country = (country or "").strip()

    if has_high_school_graduation not in YES_NO_PREFER_NOT:
        raise ValueError(
            "has_high_school_graduation must be one of: "
            "yes, no, prefer_not_to_answer"
        )

    if wants_to_continue_same_field not in YES_NO_UNSURE:
        raise ValueError(
            "wants_to_continue_same_field must be one of: yes, no, unsure"
        )

    if main_school_focus not in MAIN_SCHOOL_FOCUS:
        raise ValueError(
            "main_school_focus must be one of: humanities, science, arts, other"
        )

    for name, values in {
        "advanced_subjects": advanced_subjects,
        "favorite_subjects": favorite_subjects,
        "best_subjects": best_subjects,
    }.items():
        if not isinstance(values, list):
            raise ValueError(f"{name} must be a list")

        invalid = [v for v in values if v not in SUBJECT_FIELDS]
        if invalid:
            raise ValueError(f"{name} contains invalid values: {invalid}")

    return {
        "country": country,
        "has_high_school_graduation": has_high_school_graduation,
        "wants_to_continue_same_field": wants_to_continue_same_field,
        "main_school_focus": main_school_focus,
        "advanced_subjects": _unique_keep_order(advanced_subjects),
        "favorite_subjects": _unique_keep_order(favorite_subjects),
        "best_subjects": _unique_keep_order(best_subjects),
    }


def analyze_past_profile(
    profile: dict[str, Any],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    allowed_fields_text = ", ".join(CANONICAL_FIELDS)

    system_prompt = f"""
You are Past Agent in a career-choice system for young people without higher education.

Your task:
1. Analyze ONLY the student's school/past profile.
2. Decide whether this profile leans more toward degree, course, or is uncertain.
3. Recommend fields that fit the student's past signals.
4. Mark fields that are not recommended.
5. Mark fields where the signal is mixed/uncertain.

CRITICAL LOGIC RULE:
- Do NOT treat absence of evidence as negative evidence.
- If there is simply no signal for a field, do NOT include it anywhere.

STRICT RULES FOR not_recommended_fields:
- Use "not_recommended_fields" rarely.
- Include a field there ONLY if there is a clear negative reason or strong mismatch.

STRONG PREFERENCE RULE:
- If wants_to_continue_same_field = "no", treat same-focus fields cautiously.
- Prefer moving them to "uncertain_fields" unless evidence is overwhelming.

HARD ELIGIBILITY RULE:
- If has_high_school_graduation = "no", do NOT recommend "degree".

RULES FOR SHORT_REASON:
- short_reason must be a short reasoning, NOT a list.
- Do NOT mention specific fields unless they appear in the output lists.
- Prefer general phrasing like:
  "technical direction", "humanities direction", "science ability".
- Highlight:
  - strong ability
  - preferences
  - conflicts between them
- Keep it to 1–2 sentences.

VERY IMPORTANT:
- Use this exact key name: "degree_or_course"
- Do NOT use alternative names like "education_type"
- Fields must be from:
  [{allowed_fields_text}]
- Max 3 items per list
- Return valid JSON only
- Do not wrap the JSON in markdown fences

Return exactly this schema:
{{
  "agent_name": "past_agent",
  "can_recommend": true,
  "degree_or_course": "degree",
  "recommended_fields": ["computer_science"],
  "not_recommended_fields": [],
  "uncertain_fields": ["chemistry"],
  "confidence": "medium",
  "short_reason": "Strong repeated signals support a technical direction."
}}
""".strip()

    user_prompt = f"""
Student past profile JSON:
{json.dumps(profile, ensure_ascii=False, indent=2)}
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    kwargs = {"model": model} if model else {}
    raw = llm_call(messages, max_new_tokens=350, **kwargs)

    json_text = _extract_json_text(raw)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Past Agent returned invalid JSON:\n{raw}") from e

    parsed = normalize_past_agent_output(parsed)
    parsed = apply_past_agent_hard_rules(profile, parsed)

    return validate_past_agent_output(parsed)


def normalize_past_agent_output(output: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(output, dict):
        raise ValueError("Past Agent output must be a JSON object")

    # accept some common wrong key names from the model
    degree_value = output.get("degree_or_course", output.get("education_type", "uncertain"))

    normalized = {
        "agent_name": "past_agent",
        "can_recommend": output.get("can_recommend", True),
        "degree_or_course": degree_value,
        "recommended_fields": output.get("recommended_fields", []),
        "not_recommended_fields": output.get("not_recommended_fields", []),
        "uncertain_fields": output.get("uncertain_fields", []),
        "confidence": output.get("confidence", "medium"),
        "short_reason": output.get("short_reason", ""),
    }

    if not isinstance(normalized["can_recommend"], bool):
        normalized["can_recommend"] = False

    if normalized["degree_or_course"] not in ALLOWED_DEGREE_OR_COURSE:
        normalized["degree_or_course"] = "uncertain"

    if normalized["confidence"] not in ALLOWED_CONFIDENCE:
        normalized["confidence"] = "medium"

    if not isinstance(normalized["short_reason"], str):
        normalized["short_reason"] = str(normalized["short_reason"])

    for key in ["recommended_fields", "not_recommended_fields", "uncertain_fields"]:
        value = normalized[key]
        if not isinstance(value, list):
            value = []

        cleaned = [
            x for x in value
            if isinstance(x, str)
            and x in CANONICAL_FIELDS
            and x not in FORBIDDEN_NON_FIELD_VALUES
        ]

        normalized[key] = _unique_keep_order(cleaned)[:3]

    return normalized


def apply_past_agent_hard_rules(profile, output):
    graduation_status = profile.get("has_high_school_graduation")
    wants_same = profile.get("wants_to_continue_same_field")
    focus_fields = _focus_to_fields(profile.get("main_school_focus"))

    if graduation_status == "no":
        output["degree_or_course"] = "course"

        # avoid exaggerated certainty here
        if output.get("confidence") == "high":
            output["confidence"] = "medium"

    if wants_same == "no":
        rec = output["recommended_fields"]
        moved = [x for x in rec if x in focus_fields]
        kept = [x for x in rec if x not in focus_fields]

        if moved:
            if not kept:
                kept = moved[:1]
                moved = moved[1:]

            output["recommended_fields"] = kept
            output["uncertain_fields"] = _unique_keep_order(
                output["uncertain_fields"] + moved
            )[:3]

            output["confidence"] = "medium"

    # keep reason aligned with hard rules
    short_reason = (output.get("short_reason") or "").strip()

    if graduation_status == "no":
        if short_reason:
            if "graduation" not in short_reason.lower():
                if not short_reason.endswith("."):
                    short_reason += "."
                short_reason += (
                    " Without a high school graduation certificate, a course path is currently more realistic than a degree."
                )
        else:
            short_reason = (
                "Without a high school graduation certificate, a course path is currently more realistic than a degree."
            )

    if not short_reason:
        short_reason = "The profile provides enough information for a cautious past-based recommendation."

    output["short_reason"] = short_reason
    return output


def validate_past_agent_output(data: dict[str, Any]) -> dict[str, Any]:
    required_keys = {
        "agent_name",
        "can_recommend",
        "degree_or_course",
        "recommended_fields",
        "not_recommended_fields",
        "uncertain_fields",
        "confidence",
        "short_reason",
    }

    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Missing keys: {sorted(missing)}")

    if data["agent_name"] != "past_agent":
        raise ValueError("agent_name must be 'past_agent'")

    if not isinstance(data["can_recommend"], bool):
        raise ValueError("can_recommend must be bool")

    if data["degree_or_course"] not in ALLOWED_DEGREE_OR_COURSE:
        raise ValueError("invalid degree_or_course")

    if data["confidence"] not in ALLOWED_CONFIDENCE:
        raise ValueError("invalid confidence")

    if not isinstance(data["short_reason"], str):
        raise ValueError("short_reason must be a string")

    for key in ["recommended_fields", "not_recommended_fields", "uncertain_fields"]:
        if not isinstance(data[key], list):
            raise ValueError(f"{key} must be list")
        if len(data[key]) > 3:
            raise ValueError(f"{key} too long")

        invalid = [x for x in data[key] if x not in CANONICAL_FIELDS]
        if invalid:
            raise ValueError(f"{key} invalid: {invalid}")

    return data