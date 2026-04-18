# market_rag.py

from __future__ import annotations

from typing import Any

from app.services.field_vocab import CANONICAL_FIELDS


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
        "psychology",
    ],
    "engineering": [
        "computer_science",
        "physics",
        "management",
    ],
    "medicine": [
        "biology",
    ],
    "psychology": [
        "education",
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


FIELD_TO_SEARCH_ROLES = {
    "computer_science": [
        "junior developer",
        "qa tester",
        "it support",
    ],
    "data_science": [
        "data analyst",
        "business intelligence",
        "analytics support",
    ],
    "mathematics": [
        "analytics support",
        "finance analyst",
        "quantitative analyst",
    ],
    "physics": [
        "technical support",
        "engineering support",
        "lab support",
    ],
    "chemistry": [
        "lab technician",
        "quality control assistant",
        "lab support",
    ],
    "biology": [
        "lab support",
        "clinical support",
        "healthcare support",
    ],
    "engineering": [
        "engineering technician",
        "technical support",
        "operations support",
    ],
    "medicine": [
        "healthcare support",
        "clinical support",
        "medical assistant",
    ],
    "psychology": [
        "hr support",
        "training support",
        "mental health support",
    ],
    "history": [
        "research assistant",
        "education support",
        "content support",
    ],
    "literature": [
        "content writer",
        "editing support",
        "education support",
    ],
    "law": [
        "legal assistant",
        "compliance support",
        "policy support",
    ],
    "education": [
        "teaching assistant",
        "training coordinator",
        "education support",
    ],
    "humanities_general": [
        "communications support",
        "hr support",
        "education support",
    ],
    "design_arts": [
        "junior designer",
        "content designer",
        "media support",
    ],
    "drama": [
        "media production support",
        "creative assistant",
        "performance support",
    ],
    "management": [
        "operations coordinator",
        "project coordinator",
        "administrative support",
    ],
}


FIELD_CLUSTER_LABELS = {
    "computer_science": "tech",
    "data_science": "data",
    "mathematics": "analytics",
    "physics": "technical",
    "chemistry": "lab",
    "biology": "healthcare",
    "engineering": "engineering",
    "medicine": "healthcare",
    "psychology": "support",
    "history": "humanities",
    "literature": "writing",
    "law": "legal",
    "education": "education",
    "humanities_general": "communications",
    "design_arts": "creative",
    "drama": "media",
    "management": "operations",
}


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


def _unique_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result


def _safe_field_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [x for x in value if isinstance(x, str) and x in CANONICAL_FIELDS]


def _preferred_cluster_fields(preferred_field: str) -> list[str]:
    if preferred_field == "science":
        return [
            "computer_science",
            "data_science",
            "mathematics",
            "engineering",
            "biology",
            "chemistry",
            "physics",
            "medicine",
            "psychology",
        ]
    if preferred_field == "humanities":
        return [
            "history",
            "literature",
            "law",
            "education",
            "humanities_general",
            "psychology",
        ]
    if preferred_field == "arts":
        return [
            "design_arts",
            "drama",
            "management",
        ]
    return []


def _field_family(field: str) -> str:
    if field in SCIENCE_FIELDS:
        return "science"
    if field in HUMANITIES_FIELDS:
        return "humanities"
    if field in ARTS_FIELDS:
        return "arts"
    return "other"


def _base_candidate_fields(
    past_analysis: dict[str, Any],
    preferences_analysis: dict[str, Any],
) -> list[str]:
    result: list[str] = []

    recommended_fields = _safe_field_list(past_analysis.get("recommended_fields", []))
    uncertain_fields = _safe_field_list(past_analysis.get("uncertain_fields", []))

    result.extend(recommended_fields)
    result.extend(uncertain_fields)

    preferred_field = preferences_analysis.get("preferred_field")
    if not isinstance(preferred_field, str):
        return _unique_keep_order([x for x in result if x in CANONICAL_FIELDS])

    preferred_cluster = _preferred_cluster_fields(preferred_field)

    # If there is no useful past signal, allow the preference cluster.
    if not recommended_fields and not uncertain_fields:
        result.extend(preferred_cluster)
        return _unique_keep_order([x for x in result if x in CANONICAL_FIELDS])

    # If past already exists, only add preference fields that are already close
    # to the past family instead of injecting a whole foreign cluster.
    past_pool = recommended_fields + uncertain_fields
    past_families = {_field_family(x) for x in past_pool}

    if preferred_field in past_families:
        # same broad family -> allow matching cluster fields, but only those that
        # are already directly connected to past fields
        allowed_from_preference: list[str] = []
        past_related = set(past_pool)

        for field in past_pool:
            past_related.update(ADJACENT_FIELD_MAP.get(field, []))

        for field in preferred_cluster:
            if field in past_related:
                allowed_from_preference.append(field)

        result.extend(allowed_from_preference)
    else:
        # conflicting family -> do not inject full cluster
        # keep only the explicit overlapping fields if any
        overlap = [x for x in preferred_cluster if x in past_pool]
        result.extend(overlap)

    return _unique_keep_order([x for x in result if x in CANONICAL_FIELDS])


def _candidate_fields_from_past(
    past_analysis: dict[str, Any],
    preferences_analysis: dict[str, Any],
) -> list[str]:
    """
    Build candidate fields conservatively:
    - start with direct past/preference fields
    - expand only one adjacency step
    - do not recursively expand neighbors-of-neighbors
    """
    base_fields = _base_candidate_fields(past_analysis, preferences_analysis)

    adjacent_fields: list[str] = []
    for field in base_fields:
        adjacent_fields.extend(ADJACENT_FIELD_MAP.get(field, []))

    all_fields = base_fields + adjacent_fields
    return _unique_keep_order([x for x in all_fields if x in CANONICAL_FIELDS])


def _degree_phrase(degree_or_course: str) -> str:
    if degree_or_course == "course":
        return "without degree"
    if degree_or_course == "degree":
        return "degree required"
    return "education requirements"


def _general_market_query(country: str, degree_or_course: str) -> str:
    return f"entry level jobs in demand {country} {_degree_phrase(degree_or_course)}"


def _field_role_queries(country: str, field: str, degree_or_course: str) -> list[str]:
    roles = FIELD_TO_SEARCH_ROLES.get(field, [])
    queries: list[str] = []

    for role in roles[:2]:
        queries.append(f"{role} jobs {country} {_degree_phrase(degree_or_course)}")

    cluster = FIELD_CLUSTER_LABELS.get(field)
    if cluster:
        queries.append(f"entry level {cluster} jobs {country}")

    return queries


def _transition_query(country: str, source_field: str, target_field: str) -> str:
    source_label = FIELD_CLUSTER_LABELS.get(source_field, source_field.replace("_", " "))
    target_label = FIELD_CLUSTER_LABELS.get(target_field, target_field.replace("_", " "))
    return f"career transition from {source_label} to {target_label} jobs {country}"


def _seed_fields(
    past_analysis: dict[str, Any],
    preferences_analysis: dict[str, Any],
) -> tuple[list[str], list[str]]:
    recommended = _safe_field_list(past_analysis.get("recommended_fields", []))
    candidate_fields = _candidate_fields_from_past(past_analysis, preferences_analysis)

    if not recommended:
        recommended = candidate_fields[:2]

    return recommended[:2], candidate_fields


def build_market_search_queries(
    *,
    country: str,
    past_analysis: dict[str, Any],
    preferences_analysis: dict[str, Any],
    max_queries: int = 8,
) -> list[str]:
    country = (country or "").strip()
    if not country:
        raise ValueError("country must be a non-empty string")

    if not isinstance(past_analysis, dict):
        raise ValueError("past_analysis must be a dict")

    if not isinstance(preferences_analysis, dict):
        raise ValueError("preferences_analysis must be a dict")

    degree_or_course = past_analysis.get("degree_or_course", "uncertain")
    if not isinstance(degree_or_course, str):
        degree_or_course = "uncertain"

    recommended_seed_fields, candidate_fields = _seed_fields(
        past_analysis,
        preferences_analysis,
    )

    queries: list[str] = []

    # 1. broad practical query
    queries.append(_general_market_query(country, degree_or_course))

    # 2. role-based queries for main seed fields
    for field in recommended_seed_fields[:2]:
        queries.extend(_field_role_queries(country, field, degree_or_course))

    # 3. adjacent transition queries only for candidate-adjacent fields
    transition_pairs: list[tuple[str, str]] = []
    for source_field in recommended_seed_fields[:2]:
        for target_field in ADJACENT_FIELD_MAP.get(source_field, []):
            if target_field in candidate_fields and target_field != source_field:
                transition_pairs.append((source_field, target_field))

    dedup_pairs = []
    seen_pairs = set()
    for src, tgt in transition_pairs:
        key = (src, tgt)
        if key not in seen_pairs:
            seen_pairs.add(key)
            dedup_pairs.append((src, tgt))

    for source_field, target_field in dedup_pairs[:2]:
        queries.append(_transition_query(country, source_field, target_field))

    # 4. preference-based fallback
    preferred_field = preferences_analysis.get("preferred_field", "unclear")
    if preferred_field == "science":
        queries.append(f"entry level technical and data jobs {country}")
    elif preferred_field == "humanities":
        queries.append(f"entry level education writing legal support jobs {country}")
    elif preferred_field == "arts":
        queries.append(f"entry level creative media design jobs {country}")

    queries = _unique_keep_order([q.strip() for q in queries if q.strip()])
    return queries[:max_queries]


def build_market_rag_input(
    *,
    country: str,
    past_analysis: dict[str, Any],
    preferences_analysis: dict[str, Any],
) -> dict[str, Any]:
    queries = build_market_search_queries(
        country=country,
        past_analysis=past_analysis,
        preferences_analysis=preferences_analysis,
    )

    candidate_fields = _candidate_fields_from_past(past_analysis, preferences_analysis)

    return {
        "country": country.strip(),
        "candidate_fields": candidate_fields,
        "queries": queries,
    }