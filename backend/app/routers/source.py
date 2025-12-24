from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

from ..core.logging_config import get_logger
from ..core.settings import Settings, get_settings
from ..ingest.loaders import load_document
from ..utils.files import allowed_extensions, resolve_notes_directory

router = APIRouter(tags=['source'])
logger = get_logger(__name__)


def _resolve_source_file(filename: str, settings: Settings) -> Path:
    logger.info('🧭 resolve_source_file starting filename=%s', filename)
    notes_path = resolve_notes_directory(settings, create_if_missing=False)
    if not notes_path.exists():
        logger.info('⚠️ resolve_source_file notes_dir_missing filename=%s', filename)
        raise HTTPException(status_code=404, detail='Notes directory is not initialized.')
    target_path = (notes_path / filename).resolve()
    try:
        target_path.relative_to(notes_path)
    except ValueError as exc:  # pragma: no cover - safety
        logger.info('⚠️ resolve_source_file traversal_blocked filename=%s', filename)
        raise HTTPException(status_code=400, detail='Invalid filename path.') from exc
    if not target_path.is_file():
        logger.info('⚠️ resolve_source_file missing_file filename=%s', filename)
        raise HTTPException(status_code=404, detail='Requested file does not exist.')
    if target_path.suffix.lower() not in allowed_extensions(settings):
        logger.info('⚠️ resolve_source_file disallowed_ext filename=%s', filename)
        raise HTTPException(status_code=400, detail='File type is not supported.')
    logger.debug(f'📄 {target_path = }')
    logger.info('✅ 🧭 resolve_source_file done filename=%s', filename)
    return target_path


@router.get('/source')
async def download_source(
    filename: str = Query(..., description='Filename relative to NOTES_DIR.'),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    logger.info('📦 source_download starting filename=%s', filename)
    file_path = _resolve_source_file(filename, settings)
    logger.info('✅ 📦 source_download done filename=%s', filename)
    return FileResponse(path=file_path, filename=file_path.name)


@router.get('/source_text')
async def download_source_text(
    filename: str = Query(..., description='Filename relative to NOTES_DIR.'),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    logger.info('📝 source_text starting filename=%s', filename)
    file_path = _resolve_source_file(filename, settings)
    extracted_text = load_document(str(file_path))
    if not extracted_text:
        logger.info('⚠️ source_text extraction_failed filename=%s', filename)
        raise HTTPException(status_code=400, detail='Unable to extract text from file.')
    logger.info('✅ 📝 source_text done filename=%s', filename)
    return PlainTextResponse(content=extracted_text)
