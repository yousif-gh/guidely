from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

Question = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]


class SearchRequest(BaseModel):
    question: Question
    k: int = Field(default=3, ge=1, le=20)
