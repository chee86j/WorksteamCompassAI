from fastapi import FastAPI

from .core.logging_config import configure_logging, get_logger
from .core.settings import get_settings
from .routers import ask, files, health, ingest

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
    application.include_router(health.router)
    application.include_router(ask.router)
    application.include_router(files.router)
    application.include_router(ingest.router)
    logger.info('✅ 🧱 app_factory done.')
    return application


app = create_app()


@app.on_event('startup')
async def on_startup() -> None:
    logger.info('🚀 startup starting...')
    logger.info('✅ 🚀 startup done.')


@app.on_event('shutdown')
async def on_shutdown() -> None:
    logger.info('🛬 shutdown starting...')
    logger.info('✅ 🛬 shutdown done.')
