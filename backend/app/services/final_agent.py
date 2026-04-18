# final_agent.py

from __future__ import annotations

from typing import Any

from app.services.field_vocab import CANONICAL_FIELDS


ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_FINAL_LABELS = {"recommended", "possible", "not_recommended"}
ALLOWED_CONFLICT_TYPES = {
    "none",
    "fit_vs_market",
    "market_vs_fit",
    "preferences_vs_past",
    "uncertain",
}


# Kept aligned with the family logic already used in past_agent / market_rag.
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
    "psychology",
}

ARTS_FIELDS = {
    "design_arts",
    "drama",
    "management",
}

THINKING_STYLE_FIELDS = {
    "computer_science",
    "data_science",
    "mathematics",
    "law",
    "history",
    "literature",
    "psychology",
}

HANDS_ON_STYLE_FIELDS = {
    "engineering",
    "biology",
    "chemistry",
    "medicine",
    "design_arts",
    "drama",
    "management",
}


DEFAULT_RESULT = {
    "agent_name": "final_agent",
    "can_recommend": False,
    "user_result": {
        "top_3_recommendations": [],
        "summary": "The system could not form a reliable final recommendation from the available agent outputs.",
        "warning": "Some signals were missing or too weak to support a confident result.",
    },
    "debug_result": {
        "all_fields": [],
        "top_conflicts": [],
        "agent_influence": {
            "past_agent_weight": 0.4,
            "preferences_agent_weight": 0.2,
            "market_agent_weight": 0.4,
        },
        "notes": [
            "This final agent is deterministic and rule-based.",
            "Preferences act as modifiers, not as a standalone ranking list.",
        ],
    },
}


def _unique_keep_order(items: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for x in items:
        key = repr(x)
        if key not in seen:
            seen.add(key)
            result.append(x)
    return result


def _safe_string(value: Any, *, max_len: int = 300) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[:max_len]


def _safe_str_list(value: Any, *, max_items: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []

    cleaned: list[str] = []
    for item in value:
        if isinstance(item, str):
            s = item.strip()
            if s:
                cleaned.append(s)

    cleaned = _unique_keep_order(cleaned)
    if max_items is not None:
        cleaned = cleaned[:max_items]
    return cleaned


def _safe_field_list(value: Any, *, max_items: int | None = None) -> list[str]:
    fields = [x for x in _safe_str_list(value) if x in CANONICAL_FIELDS]
    if max_items is not None:
        fields = fields[:max_items]
    return fields


def _safe_confidence(value: Any, *, default: str = "medium") -> str:
    text = _safe_string(value, max_len=20).lower()
    if text in ALLOWED_CONFIDENCE:
        return text
    return default


def _safe_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _field_family(field: str) -> str:
    if field in SCIENCE_FIELDS:
        return "science"
    if field in HUMANITIES_FIELDS:
        return "humanities"
    if field in ARTS_FIELDS:
        return "arts"
    return "other"


def _normalize_past_result(past_result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(past_result, dict):
        raise ValueError("past_result must be a dict")

    degree_or_course = _safe_string(past_result.get("degree_or_course"), max_len=20).lower()
    if degree_or_course not in {"degree", "course", "uncertain"}:
        degree_or_course = "uncertain"

    return {
        "agent_name": "past_agent",
        "can_recommend": _safe_bool(past_result.get("can_recommend"), default=True),
        "degree_or_course": degree_or_course,
        "recommended_fields": _safe_field_list(past_result.get("recommended_fields"), max_items=3),
        "not_recommended_fields": _safe_field_list(past_result.get("not_recommended_fields"), max_items=3),
        "uncertain_fields": _safe_field_list(past_result.get("uncertain_fields"), max_items=3),
        "confidence": _safe_confidence(past_result.get("confidence"), default="medium"),
        "short_reason": _safe_string(past_result.get("short_reason"), max_len=320),
    }


def _normalize_path_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    field = _safe_string(item.get("field"), max_len=80)
    if field not in CANONICAL_FIELDS:
        return None

    return {
        "field": field,
        "career_outcomes": _safe_str_list(item.get("career_outcomes"), max_items=3),
        "reason": _safe_string(item.get("reason"), max_len=220),
    }


def _normalize_path_list(value: Any, *, max_items: int = 3) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    result: list[dict[str, Any]] = []
    used_fields: set[str] = set()

    for item in value:
        normalized = _normalize_path_item(item)
        if not normalized:
            continue
        field = normalized["field"]
        if field in used_fields:
            continue
        used_fields.add(field)
        result.append(normalized)
        if len(result) >= max_items:
            break

    return result


def _normalize_market_result(market_result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(market_result, dict):
        raise ValueError("market_result must be a dict")

    recommended_paths = _normalize_path_list(market_result.get("recommended_paths"), max_items=3)
    uncertain_paths = _normalize_path_list(market_result.get("uncertain_paths"), max_items=3)

    recommended_fields = {item["field"] for item in recommended_paths}
    uncertain_paths = [item for item in uncertain_paths if item["field"] not in recommended_fields]

    return {
        "agent_name": "market_agent",
        "can_recommend": _safe_bool(market_result.get("can_recommend"), default=True),
        "recommended_paths": recommended_paths,
        "uncertain_paths": uncertain_paths[:3],
        "confidence": _safe_confidence(market_result.get("confidence"), default="medium"),
        "short_reason": _safe_string(market_result.get("short_reason"), max_len=320),
    }


def _normalize_preferences_result(preferences_result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(preferences_result, dict):
        raise ValueError("preferences_result must be a dict")

    preferred_field = _safe_string(preferences_result.get("preferred_field"), max_len=30).lower()
    if preferred_field not in {"humanities", "science", "hands_on_work", "arts", "unclear"}:
        preferred_field = "unclear"

    def enum_yes_no_unclear(key: str) -> str:
        value = _safe_string(preferences_result.get(key), max_len=20).lower()
        if value in {"yes", "no", "unclear"}:
            return value
        return "unclear"

    job_style = _safe_string(preferences_result.get("job_style_preference"), max_len=30).lower()
    if job_style not in {"thinking", "hands_on", "unclear"}:
        job_style = "unclear"

    work_env = _safe_string(preferences_result.get("work_environment_preference"), max_len=30).lower()
    if work_env not in {"team", "alone", "mixed", "unclear"}:
        work_env = "unclear"

    structure = _safe_string(preferences_result.get("learning_structure_preference"), max_len=30).lower()
    if structure not in {"structured", "flexible", "mixed", "unclear"}:
        structure = "unclear"

    return {
        "agent_name": "preferences_agent",
        "job_style_preference": job_style,
        "work_environment_preference": work_env,
        "preferred_field": preferred_field,
        "self_learning_comfort": enum_yes_no_unclear("self_learning_comfort"),
        "long_learning_willingness": enum_yes_no_unclear("long_learning_willingness"),
        "learning_structure_preference": structure,
        "openness_to_new_fields": enum_yes_no_unclear("openness_to_new_fields"),
        "confidence": _safe_confidence(preferences_result.get("confidence"), default="medium"),
        "short_reason": _safe_string(preferences_result.get("short_reason"), max_len=320),
    }


def _build_candidate_pool(
    past_result: dict[str, Any],
    market_result: dict[str, Any],
) -> list[str]:
    candidate_fields: list[str] = []
    candidate_fields.extend(past_result["recommended_fields"])
    candidate_fields.extend(past_result["uncertain_fields"])
    candidate_fields.extend(past_result["not_recommended_fields"])
    candidate_fields.extend([item["field"] for item in market_result["recommended_paths"]])
    candidate_fields.extend([item["field"] for item in market_result["uncertain_paths"]])

    return _unique_keep_order([field for field in candidate_fields if field in CANONICAL_FIELDS])


def _market_lookup(market_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in market_result["recommended_paths"] + market_result["uncertain_paths"]:
        lookup[item["field"]] = item
    return lookup


def _past_signal(field: str, past_result: dict[str, Any]) -> tuple[str, float]:
    if field in past_result["recommended_fields"]:
        return "strong_positive", 3.0
    if field in past_result["uncertain_fields"]:
        return "positive", 1.0
    if field in past_result["not_recommended_fields"]:
        return "negative", -3.0
    return "absent", 0.0


def _market_signal(field: str, market_result: dict[str, Any]) -> tuple[str, float]:
    recommended_fields = {item["field"] for item in market_result["recommended_paths"]}
    uncertain_fields = {item["field"] for item in market_result["uncertain_paths"]}

    if field in recommended_fields:
        return "strong_positive", 3.0
    if field in uncertain_fields:
        return "positive", 1.0
    return "absent", 0.0


def _preferences_score(
    field: str,
    *,
    past_result: dict[str, Any],
    preferences_result: dict[str, Any],
    market_result: dict[str, Any],
) -> tuple[str, float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    family = _field_family(field)
    preferred_field = preferences_result["preferred_field"]

    past_supported = field in past_result["recommended_fields"] or field in past_result["uncertain_fields"]
    market_recommended = field in {item["field"] for item in market_result["recommended_paths"]}
    market_supported = market_recommended or field in {item["field"] for item in market_result["uncertain_paths"]}
    market_only = market_supported and not past_supported

    # Preferred family bonus
    if preferred_field in {"science", "humanities", "arts"} and preferred_field == family:
        score += 2.0
        reasons.append("matches preferred field family")

    # hands_on_work as a softer practical modifier
    if preferred_field == "hands_on_work" and market_recommended:
        score += 1.0
        reasons.append("fits practical market-backed direction")

    # Openness to new fields
    if preferences_result["openness_to_new_fields"] == "no" and market_only:
        score -= 1.0
        reasons.append("penalized because user is less open to new fields")
    elif preferences_result["openness_to_new_fields"] == "yes" and market_only:
        score += 1.0
        reasons.append("boosted because user is open to new fields")

    # Self-learning comfort
    if preferences_result["self_learning_comfort"] == "no" and market_only:
        score -= 1.0
        reasons.append("penalized because transition may require more self-learning")

    # Long learning willingness + course-leaning past
    if (
        preferences_result["long_learning_willingness"] == "no"
        and past_result["degree_or_course"] == "course"
        and market_recommended
    ):
        score += 1.0
        reasons.append("boosted because it looks more practical for a shorter path")

    # Structured learning helps consensus fields
    if (
        preferences_result["learning_structure_preference"] == "structured"
        and past_supported
        and market_supported
    ):
        score += 1.0
        reasons.append("benefits from being supported by both past and market")

    # Optional small style bias
    if preferences_result["job_style_preference"] == "thinking" and field in THINKING_STYLE_FIELDS:
        score += 0.5
        reasons.append("matches thinking-oriented work style")
    elif preferences_result["job_style_preference"] == "hands_on" and field in HANDS_ON_STYLE_FIELDS:
        score += 0.5
        reasons.append("matches hands-on work style")

    if score > 0:
        signal = "supportive"
    elif score < 0:
        signal = "restrictive"
    else:
        signal = "neutral"

    return signal, score, reasons


def _detect_conflict_type(
    *,
    field: str,
    past_signal: str,
    market_signal: str,
    preferences_result: dict[str, Any],
) -> str:
    family = _field_family(field)
    preferred_field = preferences_result["preferred_field"]

    if past_signal in {"strong_positive", "positive"} and market_signal in {"strong_positive", "positive"}:
        if preferred_field in {"science", "humanities", "arts"} and preferred_field != family:
            return "preferences_vs_past"
        return "none"

    if past_signal in {"strong_positive", "positive"} and market_signal == "absent":
        return "fit_vs_market"

    if market_signal in {"strong_positive", "positive"} and past_signal in {"negative", "absent"}:
        return "market_vs_fit"

    if preferred_field in {"science", "humanities", "arts"} and preferred_field != family and past_signal in {
        "strong_positive",
        "positive",
    }:
        return "preferences_vs_past"

    return "uncertain"


def _build_dominant_reason(
    *,
    field: str,
    final_label: str,
    past_signal: str,
    market_signal: str,
    preferences_signal: str,
    market_reason: str,
) -> str:
    if past_signal in {"strong_positive", "positive"} and market_signal in {"strong_positive", "positive"}:
        return "Supported by both past profile and market evidence."
    if past_signal in {"strong_positive", "positive"} and market_signal == "absent":
        return "Strong fit from past profile, but weaker market support."
    if market_signal in {"strong_positive", "positive"} and past_signal == "negative":
        return "Market evidence exists, but the past profile argues against it."
    if market_signal in {"strong_positive", "positive"} and preferences_signal == "supportive":
        return "Market-supported option helped by user preferences."
    if market_reason:
        return market_reason
    if final_label == "recommended":
        return "Strong overall balance between fit and practicality."
    if final_label == "possible":
        return "A plausible option, but with mixed evidence."
    return "The combined signals do not support this option strongly enough."


def _final_label_from_score(
    *,
    score: float,
    field: str,
    past_result: dict[str, Any],
    market_result: dict[str, Any],
) -> str:
    market_recommended_fields = {item["field"] for item in market_result["recommended_paths"]}

    if field in past_result["not_recommended_fields"] and field not in market_recommended_fields:
        return "not_recommended"

    if score >= 6.0:
        return "recommended"
    if score >= 3.0:
        return "possible"
    return "not_recommended"


def _confidence_from_signals(
    *,
    past_signal: str,
    market_signal: str,
    preferences_signal: str,
    conflict_type: str,
) -> str:
    if (
        past_signal in {"strong_positive", "positive"}
        and market_signal in {"strong_positive", "positive"}
        and preferences_signal != "restrictive"
        and conflict_type == "none"
    ):
        return "high"

    supporting_agents = 0
    if past_signal in {"strong_positive", "positive"}:
        supporting_agents += 1
    if market_signal in {"strong_positive", "positive"}:
        supporting_agents += 1
    if preferences_signal == "supportive":
        supporting_agents += 1

    if supporting_agents >= 2 and conflict_type != "uncertain":
        return "medium"

    return "low"


def _user_reason(
    *,
    past_signal: str,
    market_signal: str,
    preferences_signal: str,
    market_career_outcomes: list[str],
) -> str:
    if past_signal in {"strong_positive", "positive"} and market_signal in {"strong_positive", "positive"}:
        base = "Strong overall balance between personal fit and market prospects."
    elif past_signal in {"strong_positive", "positive"} and market_signal == "absent":
        base = "Strong personal fit, though market support is more limited."
    elif market_signal in {"strong_positive", "positive"} and past_signal in {"negative", "absent"}:
        base = "Promising market direction, but less strongly supported by past profile."
    elif preferences_signal == "supportive":
        base = "A reasonable compromise between your interests and practical opportunities."
    else:
        base = "A mixed option with some support but also some uncertainty."

    if market_career_outcomes:
        top_outcomes = ", ".join(market_career_outcomes[:2])
        base += f" Possible entry paths include {top_outcomes}."
    return base


def _top_conflicts(all_fields: list[dict[str, Any]], *, max_items: int = 3) -> list[dict[str, str]]:
    conflict_items = [
        item for item in all_fields
        if item["conflict_type"] != "none"
        and item["conflict_type"] != "uncertain"
    ]

    conflict_items.sort(
        key=lambda x: (
            0 if x["conflict_type"] != "uncertain" else 1,
            -float(x["final_score"]),
        )
    )

    result: list[dict[str, str]] = []
    for item in conflict_items[:max_items]:
        result.append(
            {
                "field": item["field"],
                "conflict_type": item["conflict_type"],
                "explanation": item["dominant_reason"],
            }
        )
    return result


def validate_final_agent_output(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("final agent output must be a dict")

    required_top = {"agent_name", "can_recommend", "user_result", "debug_result"}
    missing_top = required_top - set(data.keys())
    if missing_top:
        raise ValueError(f"Missing keys: {sorted(missing_top)}")

    if data["agent_name"] != "final_agent":
        raise ValueError("agent_name must be 'final_agent'")

    if not isinstance(data["can_recommend"], bool):
        raise ValueError("can_recommend must be bool")

    user_result = data["user_result"]
    debug_result = data["debug_result"]

    if not isinstance(user_result, dict):
        raise ValueError("user_result must be dict")
    if not isinstance(debug_result, dict):
        raise ValueError("debug_result must be dict")

    user_required = {"top_3_recommendations", "summary", "warning"}
    missing_user = user_required - set(user_result.keys())
    if missing_user:
        raise ValueError(f"user_result missing keys: {sorted(missing_user)}")

    if not isinstance(user_result["top_3_recommendations"], list):
        raise ValueError("top_3_recommendations must be list")
    if len(user_result["top_3_recommendations"]) > 3:
        raise ValueError("top_3_recommendations too long")

    for item in user_result["top_3_recommendations"]:
        if not isinstance(item, dict):
            raise ValueError("top_3_recommendations items must be dict")
        required = {"field", "label", "confidence", "reason"}
        missing = required - set(item.keys())
        if missing:
            raise ValueError(f"recommendation item missing keys: {sorted(missing)}")
        if item["field"] not in CANONICAL_FIELDS:
            raise ValueError(f"invalid recommendation field: {item['field']}")
        if item["label"] not in ALLOWED_FINAL_LABELS:
            raise ValueError(f"invalid recommendation label: {item['label']}")
        if item["confidence"] not in ALLOWED_CONFIDENCE:
            raise ValueError(f"invalid recommendation confidence: {item['confidence']}")

    debug_required = {"all_fields", "top_conflicts", "agent_influence", "notes"}
    missing_debug = debug_required - set(debug_result.keys())
    if missing_debug:
        raise ValueError(f"debug_result missing keys: {sorted(missing_debug)}")

    if not isinstance(debug_result["all_fields"], list):
        raise ValueError("debug_result.all_fields must be list")

    for item in debug_result["all_fields"]:
        if not isinstance(item, dict):
            raise ValueError("debug_result.all_fields items must be dict")
        required = {
            "field",
            "final_label",
            "final_score",
            "confidence",
            "past_signal",
            "preferences_signal",
            "market_signal",
            "conflict_type",
            "dominant_reason",
            "market_career_outcomes",
            "market_reason",
        }
        missing = required - set(item.keys())
        if missing:
            raise ValueError(f"all_fields item missing keys: {sorted(missing)}")
        if item["field"] not in CANONICAL_FIELDS:
            raise ValueError(f"invalid all_fields field: {item['field']}")
        if item["final_label"] not in ALLOWED_FINAL_LABELS:
            raise ValueError(f"invalid final_label: {item['final_label']}")
        if item["confidence"] not in ALLOWED_CONFIDENCE:
            raise ValueError(f"invalid all_fields confidence: {item['confidence']}")
        if item["conflict_type"] not in ALLOWED_CONFLICT_TYPES:
            raise ValueError(f"invalid conflict_type: {item['conflict_type']}")
        if not isinstance(item["market_career_outcomes"], list):
            raise ValueError("market_career_outcomes must be list")

    return data


def analyze_final_recommendation(
    *,
    past_result: dict[str, Any],
    preferences_result: dict[str, Any],
    market_result: dict[str, Any],
) -> dict[str, Any]:
    past = _normalize_past_result(past_result)
    preferences = _normalize_preferences_result(preferences_result)
    market = _normalize_market_result(market_result)

    candidate_pool = _build_candidate_pool(past, market)
    if not candidate_pool:
        return validate_final_agent_output(DEFAULT_RESULT)

    market_info = _market_lookup(market)

    all_fields: list[dict[str, Any]] = []

    for field in candidate_pool:
        past_signal, past_score = _past_signal(field, past)
        market_signal, market_score = _market_signal(field, market)
        preferences_signal, preferences_score, preference_reasons = _preferences_score(
            field,
            past_result=past,
            preferences_result=preferences,
            market_result=market,
        )

        final_score = round(past_score + market_score + preferences_score, 2)

        conflict_type = _detect_conflict_type(
            field=field,
            past_signal=past_signal,
            market_signal=market_signal,
            preferences_result=preferences,
        )

        final_label = _final_label_from_score(
            score=final_score,
            field=field,
            past_result=past,
            market_result=market,
        )

        market_meta = market_info.get(field, {})
        market_reason = _safe_string(market_meta.get("reason"), max_len=220)
        market_career_outcomes = _safe_str_list(market_meta.get("career_outcomes"), max_items=3)

        dominant_reason = _build_dominant_reason(
            field=field,
            final_label=final_label,
            past_signal=past_signal,
            market_signal=market_signal,
            preferences_signal=preferences_signal,
            market_reason=market_reason,
        )

        confidence = _confidence_from_signals(
            past_signal=past_signal,
            market_signal=market_signal,
            preferences_signal=preferences_signal,
            conflict_type=conflict_type,
        )

        all_fields.append(
            {
                "field": field,
                "final_label": final_label,
                "final_score": final_score,
                "confidence": confidence,
                "past_signal": past_signal,
                "preferences_signal": preferences_signal,
                "market_signal": market_signal,
                "conflict_type": conflict_type,
                "dominant_reason": dominant_reason,
                "market_career_outcomes": market_career_outcomes,
                "market_reason": market_reason,
                "_preference_reasons": preference_reasons,  # internal helper, removed below
            }
        )

    def sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
        label_rank = {
            "recommended": 0,
            "possible": 1,
            "not_recommended": 2,
        }[item["final_label"]]
        market_rank = 1 if item["market_signal"] == "strong_positive" else 0
        past_rank = 1 if item["past_signal"] == "strong_positive" else 0
        conf_rank = {"high": 2, "medium": 1, "low": 0}[item["confidence"]]
        return (label_rank, -float(item["final_score"]), -market_rank, -past_rank, -conf_rank, item["field"])

    all_fields.sort(key=sort_key)

    user_candidates = [x for x in all_fields if x["final_label"] == "recommended"]
    if len(user_candidates) < 3:
        user_candidates.extend([x for x in all_fields if x["final_label"] == "possible"])

    top_3 = []
    used_fields: set[str] = set()
    for item in user_candidates:
        if item["field"] in used_fields:
            continue
        used_fields.add(item["field"])
        top_3.append(
            {
                "field": item["field"],
                "label": item["final_label"],
                "confidence": item["confidence"],
                "reason": _user_reason(
                    past_signal=item["past_signal"],
                    market_signal=item["market_signal"],
                    preferences_signal=item["preferences_signal"],
                    market_career_outcomes=item["market_career_outcomes"],
                ),
            }
        )
        if len(top_3) >= 3:
            break

    can_recommend = len(top_3) > 0

    if can_recommend:
        summary = "The best options are the ones that balance personal fit with realistic future opportunities."
        warning = "Some personally suitable fields may still have weaker market support."
    else:
        summary = "No strong final recommendation could be formed from the available signals."
        warning = "The current agent outputs are too weak or too conflicting."

    cleaned_all_fields = []
    for item in all_fields:
        copied = dict(item)
        copied.pop("_preference_reasons", None)
        cleaned_all_fields.append(copied)

    result = {
        "agent_name": "final_agent",
        "can_recommend": can_recommend,
        "user_result": {
            "top_3_recommendations": top_3,
            "summary": summary,
            "warning": warning,
        },
        "debug_result": {
            "all_fields": cleaned_all_fields,
            "top_conflicts": _top_conflicts(cleaned_all_fields, max_items=3),
            "agent_influence": {
                "past_agent_weight": 0.4,
                "preferences_agent_weight": 0.2,
                "market_agent_weight": 0.4,
            },
            "notes": [
                "Final ranking is deterministic and score-based.",
                "Preferences modify the ranking rather than acting as a separate field recommender.",
            ],
        },
    }

    return validate_final_agent_output(result)


if __name__ == "__main__":
    past_result = {
        "agent_name": "past_agent",
        "can_recommend": True,
        "degree_or_course": "degree",
        "recommended_fields": ["history", "literature"],
        "not_recommended_fields": ["physics"],
        "uncertain_fields": ["education"],
        "confidence": "medium",
        "short_reason": "Strong repeated signals support a humanities direction.",
    }

    preferences_result = {
        "agent_name": "preferences_agent",
        "job_style_preference": "thinking",
        "work_environment_preference": "mixed",
        "preferred_field": "humanities",
        "self_learning_comfort": "no",
        "long_learning_willingness": "yes",
        "learning_structure_preference": "structured",
        "openness_to_new_fields": "no",
        "confidence": "medium",
        "short_reason": "The user prefers analytical work and humanities-related directions.",
    }

    market_result = {
        "agent_name": "market_agent",
        "can_recommend": True,
        "recommended_paths": [
            {
                "field": "education",
                "career_outcomes": ["teaching assistant", "training coordinator"],
                "reason": "Good entry-level accessibility and practical demand.",
            },
            {
                "field": "law",
                "career_outcomes": ["legal assistant", "compliance support"],
                "reason": "Some realistic support roles exist at entry level.",
            },
            {
                "field": "management",
                "career_outcomes": ["operations coordinator", "project coordination"],
                "reason": "A practical adjacent direction with labor-market relevance.",
            },
        ],
        "uncertain_paths": [
            {
                "field": "history",
                "career_outcomes": ["research assistant", "education support"],
                "reason": "The fit is plausible, but direct demand is narrower.",
            },
            {
                "field": "literature",
                "career_outcomes": ["content support", "editing support"],
                "reason": "There are some nearby roles, but the path is less direct.",
            },
            {
                "field": "psychology",
                "career_outcomes": ["hr support", "training support"],
                "reason": "Relevant support roles exist, but the path can be mixed.",
            },
        ],
        "confidence": "medium",
        "short_reason": "The strongest market paths combine demand and practical entry paths.",
    }

    result = analyze_final_recommendation(
        past_result=past_result,
        preferences_result=preferences_result,
        market_result=market_result,
    )

    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))