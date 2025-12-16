"""File loading helpers per extension."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import docx2txt
import pandas as pd
from pypdf import PdfReader

from ..core.logging_config import get_logger

logger = get_logger(__name__)


def load_document(file_path: str) -> Optional[str]:
    logger.info('📚 load_document starting...')
    path = Path(file_path)
    if not path.exists():
        logger.warning('⚠️ file missing path=%s', path)
        return None
    suffix = path.suffix.lower()
    try:
        if suffix == '.pdf':
            return _load_pdf(path)
        if suffix == '.docx':
            return docx2txt.process(str(path))
        if suffix in {'.csv', '.xlsx'}:
            return _load_tabular(path)
        if suffix in {'.md', '.txt', '.log'}:
            return path.read_text(encoding='utf-8', errors='ignore')
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception('💥 load_document error path=%s exc=%s', path, exc)
        return None
    logger.warning('⚠️ unsupported_extension path=%s', path)
    return None


def _load_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    output = io.StringIO()
    for page in reader.pages:
        text = page.extract_text() or ''
        output.write(text)
        output.write('\n')
    return output.getvalue()


def _load_tabular(path: Path) -> str:
    if path.suffix.lower() == '.csv':
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, engine='openpyxl')
    return df.to_csv(index=False)
