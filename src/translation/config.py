"""Configuration dataclasses and factory function for translation backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.translation.base import TranslationBackend


class BackendType(Enum):
    LMSTUDIO = "lmstudio"
    OPENCODE = "opencode"


@dataclass
class LMStudioConfig:
    base_url: str = "http://localhost:1234/v1"
    api_key: str = "lm-studio"
    model: str = "local-model"
    timeout: float = 60.0


@dataclass
class OpenCodeConfig:
    timeout: float = 300.0  # 5 minutes per page — translation can be slow
    model: str = "github-copilot/gpt-5-mini"


@dataclass
class TranslationConfig:
    backend: BackendType = BackendType.LMSTUDIO
    lmstudio: LMStudioConfig = field(default_factory=LMStudioConfig)
    opencode: OpenCodeConfig = field(default_factory=OpenCodeConfig)


def get_backend(config: TranslationConfig | None = None) -> TranslationBackend:
    """Factory function — returns a configured backend instance.

    Args:
        config: Translation configuration. Uses defaults if None.

    Returns:
        A concrete TranslationBackend instance.

    Raises:
        ValueError: If the backend type is unknown.
    """
    from src.translation.lmstudio import LMStudioBackend
    from src.translation.opencode import OpenCodeBackend

    if config is None:
        config = TranslationConfig()

    if config.backend == BackendType.LMSTUDIO:
        return LMStudioBackend(config.lmstudio)
    elif config.backend == BackendType.OPENCODE:
        return OpenCodeBackend(config.opencode)

    raise ValueError(f"Unknown backend: {config.backend}")
