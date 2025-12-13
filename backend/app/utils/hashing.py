import hashlib

from ..core.logging_config import get_logger

logger = get_logger(__name__)


def hash_text(value: str) -> str:
    logger.info('🔐 hash_text starting...')
    hasher = hashlib.blake2b(digest_size=16)
    hasher.update(value.encode('utf-8'))
    digest = hasher.hexdigest()
    logger.debug('📄 hash_text digest=%s', digest)
    logger.info('✅ 🔐 hash_text done.')
    return digest
