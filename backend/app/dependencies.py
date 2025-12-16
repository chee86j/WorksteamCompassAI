"""Shared FastAPI dependencies for services."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from .core.settings import Settings, get_settings
from .rag import RagPipeline


def get_rag_pipeline(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: ARG001 - ensures settings loaded
) -> RagPipeline:
    pipeline: RagPipeline | None = getattr(request.app.state, 'rag_pipeline', None)
    if not pipeline:
        raise HTTPException(status_code=503, detail='RAG pipeline not initialized.')
    return pipeline
