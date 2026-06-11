from pydantic import BaseModel


class SlideState(BaseModel):
    class_code: str
    current_slide: int
    total_slides: int
