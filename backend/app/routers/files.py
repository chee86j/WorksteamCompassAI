from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends

from ..core.logging_config import get_logger
from ..core.settings import Settings, get_settings
from ..ingest.indexing import load_manifest
from ..models.files import FileListResponse, FileMetadata

router = APIRouter(tags=['files'])
logger = get_logger(__name__)


@router.get('/files', response_model=FileListResponse)
async def list_files(settings: Settings = Depends(get_settings)) -> FileListResponse:
    logger.info('🗂️ file_listing starting...')
    notes_path = Path(settings.notes_dir).resolve()
    files: list[FileMetadata] = []
    manifest = load_manifest(notes_path) if notes_path.exists() else {}
    if notes_path.exists():
        for file_path in sorted(notes_path.iterdir()):
            if not file_path.is_file():
                continue
            entry = manifest.get(file_path.name, {})
            last_ingested_at = entry.get('last_ingested_at')
            parsed_ingested = datetime.fromisoformat(last_ingested_at) if last_ingested_at else None
            size_bytes = entry.get('size_bytes') or file_path.stat().st_size
            files.append(
                FileMetadata(
                    filename=file_path.name,
                    hash=entry.get('hash'),
                    size_bytes=size_bytes,
                    last_ingested_at=parsed_ingested,
                )
            )
    response = FileListResponse(files=files)
    logger.info('✅ 🗂️ file_listing done.')
    return response
