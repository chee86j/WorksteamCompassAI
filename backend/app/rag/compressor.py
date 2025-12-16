"""Context compressor for retrieved chunks."""

from __future__ import annotations

from typing import Any, Dict, List

from ..core.logging_config import get_logger

logger = get_logger(__name__)


def compress_chunks(chunks: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
    logger.info('🔧 compress_chunks starting...')
    trimmed: List[Dict[str, Any]] = []
    running_tokens = 0
    for chunk in chunks:
        content = chunk.get('content', '')
        token_estimate = len(content.split())
        if running_tokens + token_estimate > max_tokens:
            break
        trimmed.append(chunk)
        running_tokens += token_estimate
    logger.debug('✂️ trimmed_chunks=%s tokens=%s', len(trimmed), running_tokens)
    logger.info('✅ 🔧 compress_chunks done.')
    return trimmed
