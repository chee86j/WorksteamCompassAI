"""Deterministic chunking utilities."""

from __future__ import annotations

from typing import Any, Dict, List

from langchain.text_splitter import RecursiveCharacterTextSplitter

from ..core.logging_config import get_logger

logger = get_logger(__name__)


def chunk_text(
    document_id: str,
    filename: str,
    raw_text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Dict[str, Any]]:
    logger.info('🧩 chunk_text starting...')
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=['\n\n', '\n', '. ', ' '],
    )
    chunks = splitter.split_text(raw_text)
    structured: List[Dict[str, Any]] = []
    total_chunks = len(chunks)
    for idx, chunk in enumerate(chunks):
        chunk_id = f'{document_id}-chunk-{idx}'
        structured.append(
            {
                'chunk_id': chunk_id,
                'content': chunk,
                'metadata': {
                    'chunk_id': chunk_id,
                    'document_id': document_id,
                    'filename': filename,
                    'chunk_index': idx,
                    'chunk_total': total_chunks,
                    'content_length': len(chunk),
                },
            }
        )
    logger.info('✅ 🧩 chunk_text done.')
    return structured
