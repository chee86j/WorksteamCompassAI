from pydantic import BaseModel, Field
from typing import List, Optional


class AskRequest(BaseModel):
    query: str = Field(..., description='Natural language question to answer.')
    mode: str = Field(default='answer', description='answer or verbatim highlighting.')
    filters: Optional[dict] = Field(default=None, description='Optional metadata filters.')


class AnswerSource(BaseModel):
    document_id: str
    filename: str
    chunk_id: Optional[str] = None
    page: Optional[int] = None


class AskResponse(BaseModel):
    answer: str
    sources: List[AnswerSource] = Field(default_factory=list)
    quotes: List[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
