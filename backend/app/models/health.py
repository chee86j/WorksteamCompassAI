from datetime import datetime
from typing import List
from pydantic import BaseModel


class ComponentStatus(BaseModel):
    name: str
    status: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime
    details: List[ComponentStatus]
