from pydantic import BaseModel, Field


class InterviewQuestion(BaseModel):
    question: str = Field(min_length=10, max_length=1000)
    objective: str = Field(min_length=5, max_length=500)
    follow_up: str = Field(min_length=5, max_length=500)


class InterviewGuideRequest(BaseModel):
    candidate_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    vacancy_id: str = Field(min_length=1, max_length=100)


class InterviewGuideResponse(BaseModel):
    candidate_name: str
    vacancy_title: str
    technical_questions: list[InterviewQuestion] = Field(min_length=1, max_length=8)
    behavioral_questions: list[InterviewQuestion] = Field(min_length=1, max_length=8)


class InterviewStartRequest(InterviewGuideRequest):
    pass


class InterviewSessionQuestion(BaseModel):
    question: str = Field(min_length=10, max_length=1000)
    objective: str = Field(min_length=5, max_length=500)
    category: str = Field(pattern=r"^(Técnica|Comportamental)$")


class InterviewStartResponse(BaseModel):
    candidate_name: str
    vacancy_title: str
    questions: list[InterviewSessionQuestion] = Field(min_length=1, max_length=4)
    opening_text: str


class InterviewRespondRequest(InterviewGuideRequest):
    question: str = Field(min_length=10, max_length=1000)
    objective: str = Field(min_length=5, max_length=500)
    answer: str = Field(min_length=1, max_length=5000)


class InterviewEvaluationResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(min_length=1, max_length=5)
    improvement: str = Field(min_length=5, max_length=500)
    feedback: str = Field(min_length=5, max_length=1000)


class InterviewTTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
