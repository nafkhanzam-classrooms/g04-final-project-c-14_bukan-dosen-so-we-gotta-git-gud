from pydantic import BaseModel, Field


class ChangeSlidePayload(BaseModel):
    class_code: str
    slide_number: int = Field(..., gt=0)
