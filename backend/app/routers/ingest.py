from typing import List
from fastapi import APIRouter, Depends, UploadFile

from ..core.logging_config import get_logger
from ..core.settings import Settings, get_settings
from ..models.ingest import RefreshRequest, RefreshResponse, UploadResponse

router = APIRouter(tags=['ingest'])
logger = get_logger(__name__)


@router.post('/refresh', response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest | None = None,
    settings: Settings = Depends(get_settings),
) -> RefreshResponse:
    logger.info('🔁 refresh_request starting...')
    effective_payload = payload or RefreshRequest()
    logger.debug('🧾 %s', effective_payload.json())
    response = RefreshResponse(scanned_files=0, ingested_chunks=0, skipped_files=0)
    logger.info('✅ 🔁 refresh_request done.')
    return response


@router.post('/upload', response_model=UploadResponse)
async def upload(files: List[UploadFile]) -> UploadResponse:
    logger.info('📤 upload_request starting...')
    accepted_files = len(files)
    response = UploadResponse(
        accepted_files=accepted_files,
        rejected_files=0,
        detail='Upload pipeline not implemented yet.',
    )
    logger.info('✅ 📤 upload_request done.')
    return response
