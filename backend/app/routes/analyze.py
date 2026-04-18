from fastapi import APIRouter, HTTPException

from app.models.schemas import FullQuestionnaireRequest
from app.services.pipeline import run_full_pipeline

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("")
def analyze_questionnaires(payload: FullQuestionnaireRequest):
    try:
        result = run_full_pipeline(
            country=payload.study.country,
            study_inputs=payload.study.model_dump(),
            preferences_inputs=payload.preferences.model_dump(),
            model=None,  # сюда позже можно поставить имя модели
        )

        return {
            "ok": True,
            "result": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))