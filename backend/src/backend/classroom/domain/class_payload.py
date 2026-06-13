from pydantic import BaseModel


class CreateClassPayload(BaseModel):
    class_code: str


class JoinClassroomPayload(BaseModel):
    class_code: str
    student_name: str


class EndClassroomPayload(BaseModel):
    class_code: str


class SyncClassroomPayload(BaseModel):
    class_code: str
