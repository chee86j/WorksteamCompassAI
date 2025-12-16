import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..core.logging_config import get_logger
from ..dependencies import get_rag_pipeline
from ..models.ask import AnswerSource, AskRequest, AskResponse
from ..rag.pipeline import RagPipeline

router = APIRouter(tags=['ask'])
logger = get_logger(__name__)


def _to_response(payload: dict) -> AskResponse:
    sources = [AnswerSource(**source) for source in payload.get('sources', [])]
    return AskResponse(
        answer=payload.get('answer', ''),
        sources=sources,
        quotes=payload.get('quotes', []),
        metadata=payload.get('metadata', {}),
    )


@router.post('/ask', response_model=AskResponse)
async def ask(request: AskRequest, pipeline: RagPipeline = Depends(get_rag_pipeline)) -> AskResponse:
    logger.info('💬 ask_request starting...')
    rag_payload = await pipeline.generate_answer(request.query, request.mode, request.filters)
    response = _to_response(rag_payload)
    logger.info('✅ 💬 ask_request done.')
    return response


@router.post('/ask_stream')
async def ask_stream(request: AskRequest, pipeline: RagPipeline = Depends(get_rag_pipeline)) -> StreamingResponse:
    logger.info('🌊 ask_stream starting...')
    rag_payload = await pipeline.generate_answer(request.query, request.mode, request.filters)
    response = _to_response(rag_payload)

    async def streamer() -> AsyncGenerator[bytes, None]:
        for line in filter(None, response.answer.split('\n')):
            event = json.dumps({'event': 'message', 'data': line})
            yield event.encode('utf-8') + b'\n'
        meta_event = json.dumps({'event': 'metadata', 'data': response.metadata})
        yield meta_event.encode('utf-8') + b'\n'

    logger.info('✅ 🌊 ask_stream done.')
    return StreamingResponse(streamer(), media_type='application/x-ndjson')
