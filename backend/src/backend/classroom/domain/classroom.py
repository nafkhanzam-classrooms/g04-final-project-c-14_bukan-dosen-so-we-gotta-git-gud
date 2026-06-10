from pydantic import BaseModel, Field


class StudentState(BaseModel):
    name: str
    is_online: bool = True
    stars: int = 0


class Classroom(BaseModel):
    class_code: str
    host_session_id: str
    current_slide: int = 1
    active_students: dict[str, StudentState] = Field(default_factory=dict)
