from typing import Any

from pydantic import BaseModel, Field


class WSMessage(BaseModel):
    event: str = Field(...)
    data: dict[str, Any] = Field(default_factory=dict)
