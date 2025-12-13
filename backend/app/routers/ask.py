from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..core.logging_config import get_logger
from ..core.settings import Settings, get_settings
from ..models.ask import AnswerSource, AskRequest, AskResponse

router = APIRouter(tags=['ask'])
logger = get_logger(__name__)


@router.post('/ask', response_model=AskResponse)
async def ask(request: AskRequest, settings: Settings = Depends(get_settings)) -> AskResponse:
    logger.info('💬 ask_request starting...')
    placeholder_source = AnswerSource(
        document_id='not-implemented',
        filename='placeholder.txt',
        chunk_id=None,
        page=None,
    )
    response = AskResponse(
        answer='RAG pipeline not wired yet. Please check back once ingestion is ready.',
        sources=[placeholder_source],
        quotes=[],
        metadata={
            'mode': request.mode,
            'model': settings.openai_chat_model,
        },
    )
    logger.info('✅ 💬 ask_request done.')
    return response


@router.post('/ask_stream')
async def ask_stream(request: AskRequest) -> StreamingResponse:
    logger.info('🌊 ask_stream starting...')

    async def streamer() -> AsyncGenerator[bytes, None]:
        yield b'{"event":"message","data":"Streaming not implemented yet"}\n'

    logger.info('✅ 🌊 ask_stream done.')
    return StreamingResponse(streamer(), media_type='application/x-ndjson')
