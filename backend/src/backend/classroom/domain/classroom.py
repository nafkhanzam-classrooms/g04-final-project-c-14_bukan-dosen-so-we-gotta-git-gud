from pydantic import BaseModel, Field


class StudentState(BaseModel):
    name: str


class Classroom(BaseModel):
    class_code: str
    host_session_id: str
    current_slide: int = 1
    total_slides: int = 0
    active_students: dict[str, StudentState] = Field(default_factory=dict)
