from pydantic import BaseModel


class SlidesChangedResponse(BaseModel):
    slide_number: int


class SlidesReadyResponse(BaseModel):
    total_slides: int


class SlidesErrorResponse(BaseModel):
    class_code: str | None = None
    message: str
