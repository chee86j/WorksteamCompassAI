from redis.asyncio import Redis
from fastapi import FastAPI

from .core.logging_config import configure_logging, get_logger
from .core.settings import get_settings
from .rag import RagCache, RagPipeline
from .routers import ask, files, health, ingest, source

configure_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    logger.info('🧱 app_factory starting...')
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        docs_url='/docs',
        redoc_url='/redoc',
    )
    application.state.redis: Redis | None = None
    application.state.rag_cache: RagCache | None = None
    application.state.rag_pipeline: RagPipeline | None = None
    application.include_router(health.router)
    application.include_router(ask.router)
    application.include_router(files.router)
    application.include_router(ingest.router)
    application.include_router(source.router)
    logger.info('✅ 🧱 app_factory done.')
    return application


app = create_app()


@app.on_event('startup')
async def on_startup() -> None:
    logger.info('🚀 startup starting...')
    settings = get_settings()
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.rag_cache = RagCache(app.state.redis, settings)
    app.state.rag_pipeline = RagPipeline(settings, app.state.rag_cache)
    logger.info('✅ 🚀 startup done.')


@app.on_event('shutdown')
async def on_shutdown() -> None:
    logger.info('🛬 shutdown starting...')
    redis_client: Redis | None = getattr(app.state, 'redis', None)
    if redis_client:
        await redis_client.close()
    logger.info('✅ 🛬 shutdown done.')
