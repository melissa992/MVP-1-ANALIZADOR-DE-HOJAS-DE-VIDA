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
