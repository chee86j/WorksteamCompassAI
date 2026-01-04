"""Deterministic chunking utilities."""

from __future__ import annotations

from typing import Any, Dict, List

from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from ..core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_SEPARATORS = ['\n\n', '\n', '. ', ' ']
HEADER_FIELDS = ('h1', 'h2', 'h3', 'h4')


def chunk_text(
    document_id: str,
    filename: str,
    raw_text: str,
    chunk_size: int,
    chunk_overlap: int,
    source_extension: str | None = None,
    chunk_strategy: str = 'recursive',
) -> List[Dict[str, Any]]:
    logger.info('🧩 chunk_text starting...')
    normalized_strategy = (chunk_strategy or 'recursive').lower()
    normalized_extension = (source_extension or '').lower()
    structured: List[Dict[str, Any]] = []

    if normalized_strategy in {'markdown', 'auto'} and normalized_extension == '.md':
        structured = _chunk_markdown(
            document_id=document_id,
            filename=filename,
            raw_text=raw_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            source_extension=normalized_extension,
            chunk_strategy=normalized_strategy,
        )
    else:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=DEFAULT_SEPARATORS,
        )
        chunks = splitter.split_text(raw_text)
        structured = _format_chunks(
            document_id=document_id,
            filename=filename,
            chunks=chunks,
            source_extension=normalized_extension,
            chunk_strategy=normalized_strategy,
        )

    logger.info('✅ 🧩 chunk_text done.')
    return structured


def _chunk_markdown(
    document_id: str,
    filename: str,
    raw_text: str,
    chunk_size: int,
    chunk_overlap: int,
    source_extension: str,
    chunk_strategy: str,
) -> List[Dict[str, Any]]:
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[('#', 'h1'), ('##', 'h2'), ('###', 'h3'), ('####', 'h4')],
    )
    header_docs = header_splitter.split_text(raw_text)
    if not header_docs:
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=DEFAULT_SEPARATORS,
    )
    docs = splitter.split_documents(header_docs)
    chunks = [doc.page_content for doc in docs]
    metadata_list = [doc.metadata or {} for doc in docs]
    return _format_chunks(
        document_id=document_id,
        filename=filename,
        chunks=chunks,
        source_extension=source_extension,
        chunk_strategy=chunk_strategy,
        metadata_list=metadata_list,
    )


def _format_chunks(
    document_id: str,
    filename: str,
    chunks: List[str],
    source_extension: str,
    chunk_strategy: str,
    metadata_list: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    structured: List[Dict[str, Any]] = []
    total_chunks = len(chunks)
    for idx, chunk in enumerate(chunks):
        chunk_id = f'{document_id}-chunk-{idx}'
        extra_metadata = metadata_list[idx] if metadata_list else {}
        section_title = _section_title(extra_metadata)
        metadata = {
            'chunk_id': chunk_id,
            'document_id': document_id,
            'filename': filename,
            'chunk_index': idx,
            'chunk_total': total_chunks,
            'content_length': len(chunk),
            'chunk_strategy': chunk_strategy,
        }
        if source_extension:
            metadata['source_extension'] = source_extension
        if section_title:
            metadata['section_title'] = section_title
        metadata.update(extra_metadata)
        structured.append(
            {
                'chunk_id': chunk_id,
                'content': chunk,
                'metadata': metadata,
            }
        )
    return structured


def _section_title(metadata: Dict[str, Any]) -> str | None:
    parts: List[str] = []
    for key in HEADER_FIELDS:
        value = metadata.get(key)
        if value:
            parts.append(str(value).strip())
    if not parts:
        return None
    return ' > '.join(parts)
