from pydantic import BaseModel, Field


class QuizStartPayload(BaseModel):
    class_code: str
    question_id: str
    options: list[str] = Field(..., min_length=2)


class QuizAnswerPayload(BaseModel):
    class_code: str
    question_id: str
    answer: str


class QuizStopPayload(BaseModel):
    class_code: str
    question_id: str


class QuizClosePayload(BaseModel):
    class_code: str
    question_id: str
    correct_answer: str
