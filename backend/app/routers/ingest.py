from typing import List

from fastapi import APIRouter, Depends, UploadFile

from ..core.logging_config import get_logger
from ..core.settings import Settings, get_settings
from ..dependencies import get_rag_pipeline
from ..models.ingest import RefreshRequest, RefreshResponse, UploadResponse
from ..rag.pipeline import RagPipeline
from ..utils.files import allowed_extensions, resolve_notes_directory

router = APIRouter(tags=['ingest'])
logger = get_logger(__name__)


@router.post('/refresh', response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest | None = None,
    pipeline: RagPipeline = Depends(get_rag_pipeline),
) -> RefreshResponse:
    logger.info('🔁 refresh_request starting...')
    effective_payload = payload or RefreshRequest()
    summary = await pipeline.refresh_notes(force=effective_payload.force)
    response = RefreshResponse(**summary)
    logger.info('✅ 🔁 refresh_request done.')
    return response


@router.post('/upload', response_model=UploadResponse)
async def upload(
    files: List[UploadFile],
    settings: Settings = Depends(get_settings),
    pipeline: RagPipeline = Depends(get_rag_pipeline),
) -> UploadResponse:
    logger.info('📤 upload_request starting...')
    if not files:
        logger.info('⚠️ upload_request empty_files')
        return UploadResponse(accepted_files=0, rejected_files=0, detail='No files were uploaded.')

    notes_path = resolve_notes_directory(settings, create_if_missing=True)
    allowed_exts = allowed_extensions(settings)
    saved_paths: List[Path] = []
    rejected_files = 0

    for upload_file in files:
        suffix = Path(upload_file.filename).suffix.lower()
        if suffix not in allowed_exts:
            rejected_files += 1
            logger.info('⚠️ upload_request rejected filename=%s reason=extension', upload_file.filename)
            continue
        safe_name = Path(upload_file.filename).name
        destination = notes_path / safe_name
        with destination.open('wb') as dest_file:
            while True:
                chunk = await upload_file.read(1024 * 1024)
                if not chunk:
                    break
                dest_file.write(chunk)
        await upload_file.close()
        saved_paths.append(destination)

    if not saved_paths:
        logger.info('⚠️ upload_request no_accepted_files')
        return UploadResponse(
            accepted_files=0,
            rejected_files=rejected_files or len(files),
            detail='No files matched allowed extensions.',
        )

    summary = await pipeline.ingest_files(saved_paths)
    detail = (
        f"Ingested {summary['ingested_chunks']} chunks from {len(saved_paths)} files."
        if summary['ingested_chunks']
        else 'Files saved but produced no chunks.'
    )
    response = UploadResponse(
        accepted_files=len(saved_paths),
        rejected_files=rejected_files,
        detail=detail,
    )
    logger.info('✅ 📤 upload_request done.')
    return response
