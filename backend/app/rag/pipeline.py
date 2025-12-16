"""LangChain-powered ingestion and answering pipeline for WS-104."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from langchain_community.vectorstores import Qdrant as QdrantVectorStore
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from ..core.logging_config import get_logger
from ..core.settings import Settings
from ..ingest.chunking import chunk_text
from ..ingest.indexing import load_manifest, save_manifest, update_manifest_entry
from ..ingest.loaders import load_document
from ..rag.cache import RagCache
from ..rag.compressor import compress_chunks
from ..rag.prompts import SYSTEM_PROMPT
from ..utils.hashing import hash_file, hash_text
from ..utils.normalize import normalize_text

logger = get_logger(__name__)


class RagPipeline:
    """Coordinates ingestion into Qdrant and RAG answering."""

    def __init__(self, settings: Settings, cache: RagCache) -> None:
        logger.info('🧠 rag_pipeline_init starting...')
        self.settings = settings
        self.cache = cache
        self.allowed_exts = {ext.strip().lower() for ext in settings.allowed_exts.split(',') if ext.strip()}
        self.qdrant_client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embed_model,
            api_key=settings.openai_api_key,
            dimensions=settings.openai_embed_dimension,
        )
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=settings.qdrant_collection,
            embeddings=self.embeddings,
        )
        self.chat_model = ChatOpenAI(
            model=settings.openai_chat_model,
            temperature=settings.openai_chat_temperature,
            max_tokens=settings.openai_chat_max_tokens,
            timeout=settings.openai_timeout_sec,
            openai_api_key=settings.openai_api_key,
        )
        self._ensure_collection()
        logger.info('✅ 🧠 rag_pipeline_init done.')

    def _ensure_collection(self) -> None:
        logger.info('🏗️ ensure_qdrant_collection starting...')
        collections = self.qdrant_client.get_collections()
        names = [collection.name for collection in collections.collections]
        if self.settings.qdrant_collection not in names:
            self.qdrant_client.recreate_collection(
                collection_name=self.settings.qdrant_collection,
                vectors_config=qmodels.VectorParams(
                    size=self.settings.openai_embed_dimension,
                    distance=qmodels.Distance.COSINE,
                ),
            )
        logger.info('✅ 🏗️ ensure_qdrant_collection done.')

    async def refresh_notes(self, force: bool = False) -> Dict[str, int]:
        logger.info('🔁 refresh_notes starting...')
        notes_dir = Path(self.settings.notes_dir).resolve()
        notes_dir.mkdir(parents=True, exist_ok=True)
        manifest = load_manifest(notes_dir)
        ingest_plan = self._build_ingest_plan(notes_dir, manifest, force=force)
        summary = await self._ingest_plan(manifest, ingest_plan)
        save_manifest(notes_dir, manifest)
        logger.info('✅ 🔁 refresh_notes done.')
        return summary

    async def ingest_files(self, file_paths: Sequence[Path]) -> Dict[str, int]:
        logger.info('📥 ingest_files starting...')
        notes_dir = Path(self.settings.notes_dir).resolve()
        notes_dir.mkdir(parents=True, exist_ok=True)
        manifest = load_manifest(notes_dir)
        ingest_plan: List[Tuple[Path, str]] = []
        for file_path in file_paths:
            if not file_path.exists():
                continue
            file_hash = hash_file(file_path)
            ingest_plan.append((file_path, file_hash))
        summary = await self._ingest_plan(manifest, ingest_plan, force=True)
        save_manifest(notes_dir, manifest)
        logger.info('✅ 📥 ingest_files done.')
        return summary

    def _build_ingest_plan(
        self,
        notes_dir: Path,
        manifest: Dict[str, Dict[str, Any]],
        force: bool,
    ) -> List[Tuple[Path, str]]:
        logger.info('🗺️ build_ingest_plan starting...')
        ingest_plan: List[Tuple[Path, str]] = []
        for file_path in notes_dir.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in self.allowed_exts:
                continue
            file_hash = hash_file(file_path)
            existing = manifest.get(file_path.name)
            if not force and existing and existing.get('hash') == file_hash:
                continue
            ingest_plan.append((file_path, file_hash))
        logger.info('✅ 🗺️ build_ingest_plan done.')
        return ingest_plan

    async def _ingest_plan(
        self,
        manifest: Dict[str, Dict[str, Any]],
        ingest_plan: List[Tuple[Path, str]],
        force: bool = False,
    ) -> Dict[str, int]:
        logger.info('🧾 ingest_plan starting...')
        scanned_files = len(ingest_plan)
        ingested_chunks = 0
        skipped_files = 0
        for file_path, file_hash in ingest_plan:
            logger.info('📄 ingest_file starting filename=%s', file_path.name)
            document_id = self._document_id(file_path)
            if file_path.suffix.lower() not in self.allowed_exts:
                skipped_files += 1
                logger.info('⚠️ ingest_file skipped filename=%s reason=extension', file_path.name)
                continue
            if not force:
                existing = manifest.get(file_path.name)
                if existing and existing.get('hash') == file_hash:
                    logger.info('ℹ️ ingest_file skipped filename=%s reason=hash', file_path.name)
                    continue
            raw_text = load_document(str(file_path))
            if not raw_text:
                skipped_files += 1
                logger.info('⚠️ ingest_file skipped filename=%s reason=load', file_path.name)
                continue
            await self._delete_existing_chunks(document_id)
            chunk_records = chunk_text(
                document_id=document_id,
                filename=file_path.name,
                raw_text=raw_text,
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
            )
            if not chunk_records:
                skipped_files += 1
                logger.info('⚠️ ingest_file skipped filename=%s reason=no_chunks', file_path.name)
                continue
            await self._upsert_chunks(chunk_records)
            update_manifest_entry(
                manifest,
                filename=file_path.name,
                document_id=document_id,
                file_hash=file_hash,
                total_chunks=len(chunk_records),
                size_bytes=file_path.stat().st_size,
            )
            ingested_chunks += len(chunk_records)
            logger.info('✅ 📄 ingest_file done filename=%s', file_path.name)
        summary = {
            'scanned_files': scanned_files,
            'ingested_chunks': ingested_chunks,
            'skipped_files': skipped_files,
        }
        logger.info('✅ 🧾 ingest_plan done.')
        return summary

    async def generate_answer(self, query: str, mode: str = 'answer', filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
        logger.info('💡 generate_answer starting...')
        normalized_query = normalize_text(query or '')
        if not normalized_query:
            logger.info('⚠️ generate_answer short_circuit empty query')
            return self._empty_answer('Query is empty. Please provide a question.', mode)
        rewritten_query = await self._rewrite_query(normalized_query)
        retrieved_chunks = await self._retrieve_chunks(rewritten_query, filters)
        if not retrieved_chunks:
            return self._empty_answer('No relevant context found. Try refreshing documents.', mode)
        compressed_chunks = await self._compress_chunks(rewritten_query, retrieved_chunks)
        if not compressed_chunks:
            return self._empty_answer('Context limit reached without usable chunks.', mode)
        answer_payload = await self._answer_from_context(
            rewritten_query,
            query,
            mode,
            compressed_chunks,
        )
        logger.info('✅ 💡 generate_answer done.')
        return answer_payload

    async def _rewrite_query(self, normalized_query: str) -> str:
        logger.info('✍️ rewrite_query starting...')
        cached = await self.cache.get_rewrite(normalized_query)
        if cached:
            logger.info('✅ ✍️ rewrite_query done (cache hit).')
            return cached
        rewrite = normalized_query
        await self.cache.set_rewrite(normalized_query, rewrite)
        logger.info('✅ ✍️ rewrite_query done.')
        return rewrite

    async def _retrieve_chunks(self, query: str, filters: Dict[str, Any] | None) -> List[Dict[str, Any]]:
        logger.info('🔎 retrieve_chunks starting...')
        cached = await self.cache.get_retrieval(query)
        if cached:
            logger.info('✅ 🔎 retrieve_chunks done (cache hit).')
            return cached
        if filters:
            logger.debug('🎚️ retrieve_chunks filters_unhandled=%s', filters)

        def _search() -> List[Any]:
            return self.vector_store.similarity_search_with_score(query, k=self.settings.rag_top_k)

        docs = await asyncio.to_thread(_search)
        formatted: List[Dict[str, Any]] = []
        for doc, score in docs:
            formatted.append(
                {
                    'chunk_id': doc.metadata.get('chunk_id'),
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': score,
                }
            )
        await self.cache.set_retrieval(query, formatted)
        logger.info('✅ 🔎 retrieve_chunks done.')
        return formatted

    async def _compress_chunks(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info('🪫 compress_chunks starting...')
        chunk_ids: List[str] = []
        for chunk in chunks:
            chunk_id = chunk.get('chunk_id') or chunk.get('metadata', {}).get('chunk_id') or 'chunk'
            chunk_ids.append(chunk_id)
        cached = await self.cache.get_compress(query, chunk_ids)
        if cached:
            logger.info('✅ 🪫 compress_chunks done (cache hit).')
            return cached
        trimmed = compress_chunks(chunks, max_tokens=self.settings.max_context_tokens)
        await self.cache.set_compress(query, chunk_ids, trimmed)
        logger.info('✅ 🪫 compress_chunks done.')
        return trimmed

    async def _answer_from_context(
        self,
        cache_key_query: str,
        original_query: str,
        mode: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        logger.info('🧪 answer_from_context starting...')
        cached = await self.cache.get_answer(cache_key_query, mode)
        if cached:
            logger.info('✅ 🧪 answer_from_context done (cache hit).')
            return cached
        context_lines: List[str] = []
        sources: List[Dict[str, Any]] = []
        quotes: List[str] = []
        seen_chunks: set[str] = set()
        for chunk in context_chunks:
            chunk_id = chunk.get('chunk_id') or chunk.get('metadata', {}).get('chunk_id') or 'chunk'
            cleaned_content = (chunk.get('content') or '').strip()
            context_lines.append(f'[{chunk_id}] {cleaned_content}')
            if chunk_id not in seen_chunks:
                seen_chunks.add(chunk_id)
                metadata = chunk.get('metadata', {})
                sources.append(
                    {
                        'document_id': metadata.get('document_id'),
                        'filename': metadata.get('filename'),
                        'chunk_id': chunk_id,
                        'page': metadata.get('page'),
                    }
                )
                quotes.append(cleaned_content[:400])
        context_text = '\n\n'.join(context_lines)
        if not context_text:
            return self._empty_answer('Context chunk text unavailable.', mode)
        mode_hint = 'Answer succinctly with citations referencing [chunk-id].'
        if mode == 'verbatim':
            mode_hint = 'Return verbatim snippets with citations referencing [chunk-id].'
        human_prompt = (
            f'{mode_hint}\n'
            f'Question: {original_query}\n'
            f'Context:\n{context_text}\n'
        )
        response = await self.chat_model.ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=human_prompt)]
        )
        payload = {
            'answer': response.content,
            'sources': sources,
            'quotes': quotes,
            'metadata': {
                'mode': mode,
                'model': self.settings.openai_chat_model,
                'retrieved_chunks': len(context_chunks),
            },
        }
        await self.cache.set_answer(cache_key_query, mode, payload)
        logger.info('✅ 🧪 answer_from_context done.')
        return payload

    async def _delete_existing_chunks(self, document_id: str) -> None:
        logger.info('🧽 delete_existing_chunks starting doc_id=%s', document_id)
        filter_condition = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key='document_id',
                    match=qmodels.MatchValue(value=document_id),
                )
            ]
        )
        selector = qmodels.FilterSelector(filter=filter_condition)
        await asyncio.to_thread(
            self.qdrant_client.delete,
            collection_name=self.settings.qdrant_collection,
            points_selector=selector,
        )
        logger.info('✅ 🧽 delete_existing_chunks done doc_id=%s', document_id)

    async def _upsert_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        logger.info('⬆️ upsert_chunks starting...')
        texts = [chunk['content'] for chunk in chunks]
        vectors = await self.embeddings.aembed_documents(texts)
        payloads = [chunk['metadata'] | {'content': chunk['content']} for chunk in chunks]
        points = [
            qmodels.PointStruct(id=chunk['chunk_id'], vector=vectors[idx], payload=payloads[idx])
            for idx, chunk in enumerate(chunks)
        ]
        await asyncio.to_thread(
            self.qdrant_client.upsert,
            collection_name=self.settings.qdrant_collection,
            points=points,
        )
        logger.info('✅ ⬆️ upsert_chunks done.')

    def _document_id(self, file_path: Path) -> str:
        return hash_text(str(file_path.resolve()).lower())

    def _empty_answer(self, message: str, mode: str) -> Dict[str, Any]:
        return {
            'answer': message,
            'sources': [],
            'quotes': [],
            'metadata': {'mode': mode, 'model': self.settings.openai_chat_model},
        }
