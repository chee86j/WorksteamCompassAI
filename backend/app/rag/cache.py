"""Redis-backed cache helpers for rewrite, retrieval, compression, and answers."""

from __future__ import annotations

import json
from typing import Any, Iterable

from redis.asyncio import Redis

from ..core.logging_config import get_logger
from ..core.settings import Settings

logger = get_logger(__name__)


def _hash_inputs(values: Iterable[str]) -> str:
    from ..utils.hashing import hash_text

    joined = '::'.join(values)
    return hash_text(joined)


def _rewrite_key(query: str) -> str:
    return f'rewrite:{_hash_inputs([query])}'


def _retrieve_key(query: str, top_k: int) -> str:
    return f'retrieve:{_hash_inputs([query, str(top_k)])}'


def _compress_key(query: str, chunk_ids: Iterable[str]) -> str:
    return f'compress:{_hash_inputs([query, *chunk_ids])}'


def _answer_key(query: str, model: str, mode: str) -> str:
    return f'answer:{_hash_inputs([query, model, mode])}'


async def cache_get(redis_client: Redis, key: str) -> Any | None:
    logger.debug('🧊 cache_get key=%s', key)
    value = await redis_client.get(key)
    if value:
        return json.loads(value)
    return None


async def cache_set(redis_client: Redis, key: str, value: Any, ttl_seconds: int) -> None:
    logger.debug('🔥 cache_set key=%s ttl=%s', key, ttl_seconds)
    await redis_client.set(key, json.dumps(value), ex=ttl_seconds)


class RagCache:
    def __init__(self, redis_client: Redis, settings: Settings) -> None:
        self.redis = redis_client
        self.settings = settings

    async def get_rewrite(self, query: str) -> Any | None:
        return await cache_get(self.redis, _rewrite_key(query))

    async def set_rewrite(self, query: str, value: Any) -> None:
        await cache_set(self.redis, _rewrite_key(query), value, self.settings.cache_rewrite_ttl_sec)

    async def get_retrieval(self, query: str, top_k: int) -> Any | None:
        return await cache_get(self.redis, _retrieve_key(query, top_k))

    async def set_retrieval(self, query: str, top_k: int, value: Any) -> None:
        await cache_set(
            self.redis,
            _retrieve_key(query, top_k),
            value,
            self.settings.cache_retrieval_ttl_sec,
        )

    async def get_compress(self, query: str, chunk_ids: Iterable[str]) -> Any | None:
        return await cache_get(self.redis, _compress_key(query, chunk_ids))

    async def set_compress(self, query: str, chunk_ids: Iterable[str], value: Any) -> None:
        await cache_set(
            self.redis,
            _compress_key(query, chunk_ids),
            value,
            self.settings.cache_compress_ttl_sec,
        )

    async def get_answer(self, query: str, mode: str) -> Any | None:
        return await cache_get(self.redis, _answer_key(query, self.settings.openai_chat_model, mode))

    async def set_answer(self, query: str, mode: str, value: Any) -> None:
        await cache_set(
            self.redis,
            _answer_key(query, self.settings.openai_chat_model, mode),
            value,
            self.settings.cache_answer_ttl_sec,
        )
