from pathlib import Path
from fastapi import APIRouter, Depends

from ..core.logging_config import get_logger
from ..core.settings import Settings, get_settings
from ..models.files import FileListResponse, FileMetadata

router = APIRouter(tags=['files'])
logger = get_logger(__name__)


@router.get('/files', response_model=FileListResponse)
async def list_files(settings: Settings = Depends(get_settings)) -> FileListResponse:
    logger.info('🗂️ file_listing starting...')
    notes_path = Path(settings.notes_dir)
    files: list[FileMetadata] = []
    if notes_path.exists():
        for file_path in notes_path.iterdir():
            if file_path.is_file():
                files.append(
                    FileMetadata(
                        filename=file_path.name,
                        size_bytes=file_path.stat().st_size,
                    )
                )
    response = FileListResponse(files=files)
    logger.info('✅ 🗂️ file_listing done.')
    return response
