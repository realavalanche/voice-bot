from typing import Literal, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    language: Literal["hi-IN", "en-IN", "auto"] = "auto"
    history: list[dict] = Field(default_factory=list, max_length=10)
