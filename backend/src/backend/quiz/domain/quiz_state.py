from pydantic import BaseModel


class QuizState(BaseModel):
    question_id: str
    options: list[str]
    is_active: bool
    answers: dict[str, str] = {}
    correct_answer: str | None = None
