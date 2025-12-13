import re

from ..core.logging_config import get_logger

logger = get_logger(__name__)
WHITESPACE_RE = re.compile(r'\s+')


def normalize_text(value: str) -> str:
    logger.info('🧹 normalize_text starting...')
    normalized = ''
    if value:
        normalized = WHITESPACE_RE.sub(' ', value.strip().lower())
    logger.debug('🧼 normalize_text result=%s', normalized)
    logger.info('✅ 🧹 normalize_text done.')
    return normalized
