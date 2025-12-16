import hashlib
from pathlib import Path

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


def hash_file(path: Path) -> str:
    logger.info('🗃️ hash_file starting...')
    hasher = hashlib.blake2b(digest_size=16)
    with path.open('rb') as file_handle:
        for chunk in iter(lambda: file_handle.read(8192), b''):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    logger.debug('🧾 hash_file digest=%s path=%s', digest, path)
    logger.info('✅ 🗃️ hash_file done.')
    return digest
