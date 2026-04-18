# market_agent.py

from __future__ import annotations

import json
import re
from typing import Any

from app.services.llm_client import llm_call
from app.services.field_vocab import CANONICAL_FIELDS


ALLOWED_CONFIDENCE = {"low", "medium", "high"}


ADJACENT_FIELD_MAP = {
    "computer_science": [
        "data_science",
        "engineering",
        "management",
    ],
    "data_science": [
        "computer_science",
        "mathematics",
        "management",
    ],
    "mathematics": [
        "data_science",
        "computer_science",
        "physics",
        "management",
    ],
    "physics": [
        "engineering",
        "mathematics",
        "computer_science",
    ],
    "chemistry": [
        "biology",
        "physics",
    ],
    "biology": [
        "chemistry",
        "medicine",
        "psychology",
    ],
    "engineering": [
        "computer_science",
        "physics",
        "management",
    ],
    "medicine": [
        "biology",
        "psychology",
    ],
    "psychology": [
        "education",
        "medicine",
        "humanities_general",
    ],
    "history": [
        "literature",
        "education",
        "humanities_general",
        "law",
    ],
    "literature": [
        "history",
        "education",
        "humanities_general",
        "law",
    ],
    "law": [
        "history",
        "humanities_general",
        "management",
    ],
    "education": [
        "history",
        "literature",
        "psychology",
        "humanities_general",
    ],
    "humanities_general": [
        "history",
        "literature",
        "education",
        "law",
        "psychology",
    ],
    "design_arts": [
        "drama",
        "humanities_general",
        "management",
    ],
    "drama": [
        "design_arts",
        "humanities_general",
    ],
    "management": [
        "computer_science",
        "data_science",
        "engineering",
        "law",
        "design_arts",
    ],
}


def _unique_keep_order(items: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for x in items:
        key = json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, (dict, list)) else x
        if key not in seen:
            seen.add(key)
            result.append(x)
    return result


def _extract_json_text(raw: str) -> str:
    """
    Accept either:
    - pure JSON
    - fenced markdown block like ```json ... ```
    - text that contains a JSON object
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Market Agent returned empty output")

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1].strip()

    return raw


def _normalize_confidence(value: Any) -> str:
    if value is None:
        return "medium"

    text = str(value).strip().lower()
    if text in ALLOWED_CONFIDENCE:
        return text

    return "medium"


def _normalize_string_list(value: Any, *, max_items: int) -> list[str]:
    if not isinstance(value, list):
        return []

    cleaned = []
    for x in value:
        if isinstance(x, str):
            s = x.strip()
            if s:
                cleaned.append(s)

    return _unique_keep_order(cleaned)[:max_items]


def _normalize_path_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    field = item.get("field")
    if not isinstance(field, str):
        return None

    field = field.strip()
    if field not in CANONICAL_FIELDS:
        return None

    career_outcomes = _normalize_string_list(
        item.get("career_outcomes", []),
        max_items=3,
    )

    reason = item.get("reason", "")
    if not isinstance(reason, str):
        reason = str(reason)

    reason = reason.strip()[:220]

    return {
        "field": field,
        "career_outcomes": career_outcomes,
        "reason": reason,
    }


def _normalize_path_list(value: Any, *, max_items: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    result = []
    seen_fields = set()

    for item in value:
        normalized = _normalize_path_item(item)
        if not normalized:
            continue

        field = normalized["field"]
        if field in seen_fields:
            continue

        seen_fields.add(field)
        result.append(normalized)

        if len(result) >= max_items:
            break

    return result


def _candidate_fields_from_past(past_analysis: dict[str, Any]) -> list[str]:
    result: list[str] = []

    recommended = past_analysis.get("recommended_fields", [])
    uncertain = past_analysis.get("uncertain_fields", [])

    if isinstance(recommended, list):
        result.extend([x for x in recommended if isinstance(x, str) and x in CANONICAL_FIELDS])

    if isinstance(uncertain, list):
        result.extend([x for x in uncertain if isinstance(x, str) and x in CANONICAL_FIELDS])

    expanded = list(result)
    for field in result:
        expanded.extend(ADJACENT_FIELD_MAP.get(field, []))

    return _unique_keep_order([x for x in expanded if x in CANONICAL_FIELDS])


def build_market_profile(
    *,
    country: str,
    past_analysis: dict[str, Any],
    preferences_analysis: dict[str, Any],
    market_context: str,
) -> dict[str, Any]:
    country = (country or "").strip()
    if not country:
        raise ValueError("country must be a non-empty string")

    if not isinstance(past_analysis, dict):
        raise ValueError("past_analysis must be a dict")

    if not isinstance(preferences_analysis, dict):
        raise ValueError("preferences_analysis must be a dict")

    market_context = (market_context or "").strip()
    if not market_context:
        raise ValueError("market_context must be a non-empty string")

    candidate_fields = _candidate_fields_from_past(past_analysis)

    return {
        "country": country,
        "past_analysis": past_analysis,
        "preferences_analysis": preferences_analysis,
        "candidate_fields": candidate_fields,
        "market_context": market_context,
    }


def normalize_market_agent_output(output: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(output, dict):
        raise ValueError("Market Agent output must be a JSON object")

    normalized = {
        "agent_name": "market_agent",
        "can_recommend": output.get("can_recommend", True),
        "recommended_paths": _normalize_path_list(output.get("recommended_paths", []), max_items=3),
        "uncertain_paths": _normalize_path_list(output.get("uncertain_paths", []), max_items=3),
        "confidence": _normalize_confidence(output.get("confidence", "medium")),
        "short_reason": output.get("short_reason", ""),
    }

    if not isinstance(normalized["can_recommend"], bool):
        normalized["can_recommend"] = False

    if not isinstance(normalized["short_reason"], str):
        normalized["short_reason"] = str(normalized["short_reason"])

    normalized["short_reason"] = normalized["short_reason"].strip()[:320]

    return normalized


def apply_market_agent_hard_rules(profile: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    past_analysis = profile.get("past_analysis", {})
    degree_or_course = past_analysis.get("degree_or_course", "uncertain")

    recommended_paths = output.get("recommended_paths", [])
    uncertain_paths = output.get("uncertain_paths", [])

    used_fields = set()
    clean_recommended = []
    for item in recommended_paths:
        field = item["field"]
        if field not in used_fields:
            used_fields.add(field)
            clean_recommended.append(item)

    clean_uncertain = []
    for item in uncertain_paths:
        field = item["field"]
        if field not in used_fields:
            used_fields.add(field)
            clean_uncertain.append(item)

    output["recommended_paths"] = clean_recommended[:3]
    output["uncertain_paths"] = clean_uncertain[:3]

    if degree_or_course == "course" and output.get("confidence") == "high":
        output["confidence"] = "medium"

    short_reason = (output.get("short_reason") or "").strip()
    if not short_reason:
        short_reason = (
            "The market evidence suggests a small set of practical directions that appear stronger than other nearby options."
        )

    output["short_reason"] = short_reason
    return output


def validate_market_agent_output(data: dict[str, Any]) -> dict[str, Any]:
    required_keys = {
        "agent_name",
        "can_recommend",
        "recommended_paths",
        "uncertain_paths",
        "confidence",
        "short_reason",
    }

    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Missing keys: {sorted(missing)}")

    if data["agent_name"] != "market_agent":
        raise ValueError("agent_name must be 'market_agent'")

    if not isinstance(data["can_recommend"], bool):
        raise ValueError("can_recommend must be bool")

    if data["confidence"] not in ALLOWED_CONFIDENCE:
        raise ValueError("invalid confidence")

    if not isinstance(data["short_reason"], str):
        raise ValueError("short_reason must be a string")

    for key in ["recommended_paths", "uncertain_paths"]:
        if not isinstance(data[key], list):
            raise ValueError(f"{key} must be list")
        if len(data[key]) > 3:
            raise ValueError(f"{key} too long")

        seen_fields = set()
        for item in data[key]:
            if not isinstance(item, dict):
                raise ValueError(f"{key} items must be dict")

            if set(item.keys()) != {"field", "career_outcomes", "reason"}:
                raise ValueError(f"{key} items must contain exactly: field, career_outcomes, reason")

            field = item["field"]
            if field not in CANONICAL_FIELDS:
                raise ValueError(f"{key} invalid field: {field}")

            if field in seen_fields:
                raise ValueError(f"{key} contains duplicate field: {field}")
            seen_fields.add(field)

            if not isinstance(item["career_outcomes"], list):
                raise ValueError(f"{key}.career_outcomes must be list")
            if len(item["career_outcomes"]) > 3:
                raise ValueError(f"{key}.career_outcomes too long")

            for outcome in item["career_outcomes"]:
                if not isinstance(outcome, str):
                    raise ValueError(f"{key}.career_outcomes items must be strings")

            if not isinstance(item["reason"], str):
                raise ValueError(f"{key}.reason must be string")

    recommended_fields = {item["field"] for item in data["recommended_paths"]}
    uncertain_fields = {item["field"] for item in data["uncertain_paths"]}
    overlap = recommended_fields & uncertain_fields
    if overlap:
        raise ValueError(f"Fields cannot appear in both recommended_paths and uncertain_paths: {sorted(overlap)}")

    return data


def analyze_market_profile(
    profile: dict[str, Any],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    allowed_fields_text = ", ".join(CANONICAL_FIELDS)

    system_prompt = f"""
You are Market Agent in a career-choice system for young people without higher education.

Your task:
1. Analyze ONLY the external market context that was already collected by a separate RAG/search layer.
2. Use the user's country, past analysis, preferences analysis, and candidate fields.
3. Recommend exactly 3 strongest market-supported learning paths.
4. Mark exactly 3 uncertain learning paths.
5. Each path must include:
   - field
   - 1 to 3 realistic career_outcomes
   - a short reason

IMPORTANT:
- Your role is different from Past Agent and Preferences Agent.
- You may recommend adjacent fields that are NOT in past_analysis.recommended_fields,
  but only if they are close transitions from the user's background and supported by market evidence.
- Do NOT recommend institutions, colleges, universities, or courses providers.
- Recommend only WHAT to study, not WHERE to study.
- Career outcomes should be realistic entry-level or near-entry roles, not senior roles.
- Use only these canonical fields:
  [{allowed_fields_text}]

CRITICAL MARKET RULES:
- Do NOT answer from general memory if the market_context does not support it.
- Treat market_context as the evidence boundary.
- If evidence is weak or mixed, place the field in uncertain_paths, not recommended_paths.
- Consider demand, accessibility, and closeness to the user's background.
- If past_analysis.degree_or_course = "course", avoid reasoning that depends on long degree-only entry paths.
- Do NOT simply repeat Past Agent. Your job is market reasoning.
- It is acceptable to recommend close transitions such as technical -> management if the market evidence supports it.

STRICT OUTPUT RULES:
- Return valid JSON only.
- Do not wrap the JSON in markdown fences.
- Return exactly 3 items in recommended_paths.
- Return exactly 3 items in uncertain_paths.
- Each field should appear at most once across both lists.
- Use this exact schema.

Return exactly this schema:
{{
  "agent_name": "market_agent",
  "can_recommend": true,
  "recommended_paths": [
    {{
      "field": "computer_science",
      "career_outcomes": ["software development", "backend roles"],
      "reason": "High demand and realistic entry paths in the given country."
    }},
    {{
      "field": "data_science",
      "career_outcomes": ["data analyst", "junior data roles"],
      "reason": "Strong adjacent option for technical backgrounds with useful market demand."
    }},
    {{
      "field": "management",
      "career_outcomes": ["operations", "project coordination"],
      "reason": "A realistic nearby transition with labor market relevance."
    }}
  ],
  "uncertain_paths": [
    {{
      "field": "mathematics",
      "career_outcomes": ["analytics", "research support"],
      "reason": "Some relevance exists, but direct entry may be less accessible."
    }},
    {{
      "field": "physics",
      "career_outcomes": ["technical roles", "research support"],
      "reason": "The field is adjacent, but the market path appears less direct."
    }},
    {{
      "field": "chemistry",
      "career_outcomes": ["lab support", "research support"],
      "reason": "Market access appears weaker or more education-dependent."
    }}
  ],
  "confidence": "medium",
  "short_reason": "The strongest market paths combine demand, accessibility, and closeness to the user's background."
}}
""".strip()

    user_prompt = f"""
Market profile JSON:
{json.dumps(profile, ensure_ascii=False, indent=2)}
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    kwargs = {"model": model} if model else {}
    raw = llm_call(messages, max_new_tokens=650, **kwargs)

    json_text = _extract_json_text(raw)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Market Agent returned invalid JSON:\n{raw}") from e

    parsed = normalize_market_agent_output(parsed)
    parsed = apply_market_agent_hard_rules(profile, parsed)

    return validate_market_agent_output(parsed)