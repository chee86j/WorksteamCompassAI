from pydantic import BaseModel, Field


class RefreshRequest(BaseModel):
    force: bool = Field(default=False, description='Force re-index even if hashes match.')


class RefreshResponse(BaseModel):
    scanned_files: int
    ingested_chunks: int
    skipped_files: int


class UploadResponse(BaseModel):
    accepted_files: int
    rejected_files: int
    detail: str | None = None
