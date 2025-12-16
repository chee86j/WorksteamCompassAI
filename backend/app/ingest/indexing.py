"""Index manifest helpers for keeping metadata per file."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..core.logging_config import get_logger

logger = get_logger(__name__)

MANIFEST_FILENAME = '.compass_index.json'
Manifest = Dict[str, Dict[str, Any]]


def load_manifest(notes_dir: Path) -> Manifest:
    logger.info('📗 load_manifest starting...')
    manifest_path = notes_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        logger.info('✅ 📗 load_manifest done.')
        return {}
    logger.debug('📄 load_manifest path=%s', manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    logger.info('✅ 📗 load_manifest done.')
    return manifest


def save_manifest(notes_dir: Path, manifest: Manifest) -> None:
    logger.info('📘 save_manifest starting...')
    manifest_path = notes_dir / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    logger.info('✅ 📘 save_manifest done.')


def update_manifest_entry(
    manifest: Manifest,
    filename: str,
    document_id: str,
    file_hash: str,
    total_chunks: int,
    size_bytes: int,
) -> None:
    logger.info('📝 update_manifest_entry starting...')
    manifest[filename] = {
        'document_id': document_id,
        'hash': file_hash,
        'size_bytes': size_bytes,
        'total_chunks': total_chunks,
        'last_ingested_at': datetime.utcnow().isoformat(),
    }
    logger.info('✅ 📝 update_manifest_entry done.')


def manifest_to_list(manifest: Manifest) -> List[Dict[str, Any]]:
    logger.info('📚 manifest_to_list starting...')
    entries: List[Dict[str, Any]] = []
    for filename, info in manifest.items():
        entries.append(
            {
                'filename': filename,
                'hash': info.get('hash'),
                'size_bytes': info.get('size_bytes'),
                'last_ingested_at': info.get('last_ingested_at'),
                'total_chunks': info.get('total_chunks'),
            }
        )
    logger.info('✅ 📚 manifest_to_list done.')
    return entries
