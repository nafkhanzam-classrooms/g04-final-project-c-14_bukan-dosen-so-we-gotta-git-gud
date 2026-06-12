from pydantic import BaseModel


class ClassroomCreatedResponse(BaseModel):
    class_code: str


class ClassroomJoinedResponse(BaseModel):
    class_code: str
    student_name: str


class ClassroomErrorResponse(BaseModel):
    class_code: str | None = None
    message: str


class ClassroomStateSyncResponse(BaseModel):
    class_code: str
    host_session_id: str
    current_slide: str
    total_slides: str
    active_students: list[str]


class TopStudentResponse(BaseModel):
    name: str
    score: int
    is_streak: bool


class ClassroomEndedResponse(BaseModel):
    class_code: str
    top_students: list[TopStudentResponse]
