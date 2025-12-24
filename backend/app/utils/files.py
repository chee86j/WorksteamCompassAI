"""Filesystem helpers for Compass backend."""

from __future__ import annotations

from pathlib import Path

from ..core.logging_config import get_logger
from ..core.settings import Settings

logger = get_logger(__name__)


def allowed_extensions(settings: Settings) -> set[str]:
    logger.info('🧾 allowed_extensions starting...')
    extensions = {ext.strip().lower() for ext in settings.allowed_exts.split(',') if ext.strip()}
    logger.debug(f'📎 {extensions = }')
    logger.info('✅ 🧾 allowed_extensions done.')
    return extensions


def resolve_notes_directory(settings: Settings, create_if_missing: bool = False) -> Path:
    logger.info('📁 resolve_notes_directory starting...')
    notes_path = Path(settings.notes_dir).resolve()
    if create_if_missing:
        notes_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f'🧭 {notes_path = }')
    logger.info('✅ 📁 resolve_notes_directory done.')
    return notes_path
