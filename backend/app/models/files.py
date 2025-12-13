from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    filename: str
    hash: Optional[str] = None
    size_bytes: Optional[int] = None
    last_ingested_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


class FileListResponse(BaseModel):
    files: List[FileMetadata] = Field(default_factory=list)
