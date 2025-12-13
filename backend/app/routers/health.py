from datetime import datetime
from fastapi import APIRouter, Depends

from ..core.logging_config import get_logger
from ..core.settings import Settings, get_settings
from ..models.health import ComponentStatus, HealthResponse

router = APIRouter(tags=['health'])
logger = get_logger(__name__)


@router.get('/health', response_model=HealthResponse)
async def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    logger.info('🚦 health_check starting...')
    components = [
        ComponentStatus(name='api', status='ok', detail='FastAPI responding'),
        ComponentStatus(name='qdrant', status='unknown', detail='Not probed yet'),
        ComponentStatus(name='redis', status='unknown', detail='Not probed yet'),
    ]
    response = HealthResponse(
        status='ok',
        version=settings.api_version,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
        details=components,
    )
    logger.info('✅ 🚦 health_check done.')
    return response
