#!/usr/bin/env python3
"""Lightweight retrieval evaluation for the RAG pipeline."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from redis.asyncio import Redis

from backend.app.core.settings import Settings
from backend.app.rag import RagCache, RagPipeline


def _load_cases(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, list):
        raise ValueError('Evaluation data must be a JSON list.')
    return payload


def _expected_set(values: List[str]) -> set[str]:
    return {value.strip().lower() for value in values if value}


def _score_case(
    retrieved: List[Dict[str, Any]],
    expected_sources: List[str],
) -> Tuple[int | None, str | None]:
    expected = _expected_set(expected_sources)
    for idx, chunk in enumerate(retrieved, start=1):
        filename = (chunk.get('metadata') or {}).get('filename', '')
        if filename and filename.lower() in expected:
            return idx, filename
    return None, None


async def _evaluate(
    pipeline: RagPipeline,
    cases: List[Dict[str, Any]],
    top_k: int | None,
    use_cache: bool,
) -> Dict[str, Any]:
    total = len(cases)
    hits = 0
    reciprocal_sum = 0.0
    rows: List[Dict[str, Any]] = []
    for case in cases:
        query = case.get('query', '')
        expected_sources = case.get('expected_sources', [])
        filters = case.get('filters')
        retrieved = await pipeline.retrieve_chunks(
            query,
            filters=filters,
            top_k=top_k,
            use_cache=use_cache,
        )
        rank, matched = _score_case(retrieved, expected_sources)
        hit = 1 if rank else 0
        hits += hit
        reciprocal_sum += 1 / rank if rank else 0.0
        rows.append(
            {
                'query': query,
                'hit': bool(hit),
                'rank': rank,
                'matched_source': matched,
            }
        )
    recall_at_k = hits / total if total else 0.0
    mrr = reciprocal_sum / total if total else 0.0
    return {
        'total': total,
        'recall_at_k': recall_at_k,
        'mrr': mrr,
        'cases': rows,
    }


async def _run() -> int:
    parser = argparse.ArgumentParser(description='Evaluate RAG retrieval quality.')
    parser.add_argument('--data', required=True, help='Path to JSON eval set.')
    parser.add_argument('--k', type=int, default=None, help='Override top-k for retrieval.')
    parser.add_argument('--no-cache', action='store_true', help='Bypass retrieval cache.')
    args = parser.parse_args()

    data_path = Path(args.data)
    cases = _load_cases(data_path)

    settings = Settings()
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    cache = RagCache(redis_client, settings)
    pipeline = RagPipeline(settings, cache)
    try:
        results = await _evaluate(pipeline, cases, args.k, use_cache=not args.no_cache)
    finally:
        await redis_client.close()

    print(json.dumps(results, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(_run()))
