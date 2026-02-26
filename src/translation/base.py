"""Abstract base class for translation backends (Strategy pattern)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranslationResult:
    """Result of a translation operation."""

    translated_text: str
    source_language: str
    target_language: str
    backend_used: str


class TranslationBackend(ABC):
    """Abstract interface that all translation backends must implement."""

    @abstractmethod
    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> TranslationResult:
        """Translate text to the target language.

        Args:
            text: The text to translate.
            target_language: Language to translate into (e.g. "Portuguese").
            source_language: Source language hint, or "auto" for auto-detect.

        Returns:
            TranslationResult with the translated text and metadata.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is reachable and properly configured."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this backend."""
        ...
