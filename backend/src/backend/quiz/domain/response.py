from pydantic import BaseModel


class QuizStartedResponse(BaseModel):
    class_code: str
    question_id: str
    options: list[str]


class QuizAnswerReceivedResponse(BaseModel):
    class_code: str
    question_id: str
    total_answered: int


class QuizStoppedResponse(BaseModel):
    class_code: str
    question_id: str


class QuizClosedResponse(BaseModel):
    class_code: str
    question_id: str
    correct_answer: str
    stats: dict[str, int]


class QuizErrorResponse(BaseModel):
    message: str
