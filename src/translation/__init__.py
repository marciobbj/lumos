"""Translation backends — Strategy pattern for swappable translation providers."""

from src.translation.base import TranslationBackend, TranslationResult
from src.translation.config import (
    BackendType,
    LMStudioConfig,
    OpenCodeConfig,
    TranslationConfig,
    get_backend,
)
from src.translation.lmstudio import LMStudioBackend
from src.translation.opencode import OpenCodeBackend

__all__ = [
    "BackendType",
    "LMStudioBackend",
    "LMStudioConfig",
    "OpenCodeBackend",
    "OpenCodeConfig",
    "TranslationBackend",
    "TranslationConfig",
    "TranslationResult",
    "get_backend",
]
