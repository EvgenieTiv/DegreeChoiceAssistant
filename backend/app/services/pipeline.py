from __future__ import annotations

from typing import Any

from app.services.past_agent import build_past_profile, analyze_past_profile
from app.services.preferences_agent import (
    build_preferences_profile,
    analyze_preferences_profile,
)
from app.services.market_retrieval import retrieve_market_context
from app.services.market_agent import build_market_profile, analyze_market_profile
from app.services.final_agent import analyze_final_recommendation


def run_full_pipeline(
    *,
    country: str,
    study_inputs: dict[str, Any],
    preferences_inputs: dict[str, Any],
    model: str | None = None,
) -> dict[str, Any]:
    # 1. Past agent
    past_profile = build_past_profile(
        country=country,
        has_high_school_graduation=study_inputs["has_high_school_graduation"],
        wants_to_continue_same_field=study_inputs["wants_to_continue_same_field"],
        main_school_focus=study_inputs["main_school_focus"],
        advanced_subjects=study_inputs["advanced_subjects"],
        favorite_subjects=study_inputs["favorite_subjects"],
        best_subjects=study_inputs["best_subjects"],
    )

    past_result = analyze_past_profile(
        past_profile,
        model=model,
    )

    # 2. Preferences agent
    preferences_profile = build_preferences_profile(
        job_style_preference=preferences_inputs["job_style_preference"],
        work_environment_preference=preferences_inputs["work_environment_preference"],
        preferred_field=preferences_inputs["preferred_field"],
        self_learning_comfort=preferences_inputs["self_learning_comfort"],
        long_learning_willingness=preferences_inputs["long_learning_willingness"],
        learning_structure_preference=preferences_inputs["learning_structure_preference"],
        openness_to_new_fields=preferences_inputs["openness_to_new_fields"],
    )

    preferences_result = analyze_preferences_profile(
        preferences_profile,
        model=model,
    )

    # 3. Market retrieval
    market_retrieval_result = retrieve_market_context(
        country=country,
        past_analysis=past_result,
        preferences_analysis=preferences_result,
    )

    # 4. Market agent
    market_profile = build_market_profile(
        country=country,
        past_analysis=past_result,
        preferences_analysis=preferences_result,
        market_context=market_retrieval_result["market_context"],
    )

    market_result = analyze_market_profile(
        market_profile,
        model=model,
    )

    # 5. Final agent
    final_result = analyze_final_recommendation(
        past_result=past_result,
        preferences_result=preferences_result,
        market_result=market_result,
    )

    return {
        "country": country,
        "past_profile": past_profile,
        "preferences_profile": preferences_profile,
        "market_retrieval": market_retrieval_result,
        "past_result": past_result,
        "preferences_result": preferences_result,
        "market_profile": market_profile,
        "market_result": market_result,
        "final_result": final_result,
    }