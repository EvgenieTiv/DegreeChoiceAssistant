from pydantic import BaseModel
from typing import List


class StudyQuestionnaireRequest(BaseModel):
    country: str
    has_high_school_graduation: str
    wants_to_continue_same_field: str
    main_school_focus: str
    advanced_subjects: List[str]
    favorite_subjects: List[str]
    best_subjects: List[str]


class PreferencesQuestionnaireRequest(BaseModel):
    job_style_preference: str
    work_environment_preference: str
    preferred_field: str
    self_learning_comfort: str
    long_learning_willingness: str
    learning_structure_preference: str
    openness_to_new_fields: str


class FullQuestionnaireRequest(BaseModel):
    study: StudyQuestionnaireRequest
    preferences: PreferencesQuestionnaireRequest