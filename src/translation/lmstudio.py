"""LM Studio translation backend using the OpenAI-compatible API."""

from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from src.translation.base import TranslationBackend, TranslationResult
from src.translation.config import LMStudioConfig

TRANSLATION_PROMPT = """\
Translate the following text to {target_language}. \
Return ONLY the translated text, with no additional commentary, explanations, or notes.
Preserve the original formatting and paragraph structure.

Text to translate:
{text}"""


class LMStudioBackend(TranslationBackend):
    """Translation backend that uses LM Studio's OpenAI-compatible API."""

    def __init__(self, config: LMStudioConfig | None = None) -> None:
        self._config = config or LMStudioConfig()
        self._client = AsyncOpenAI(
            base_url=self._config.base_url,
            api_key=self._config.api_key,
            timeout=self._config.timeout,
        )

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> TranslationResult:
        """Translate text using the LM Studio API.

        Args:
            text: The text to translate.
            target_language: Language to translate into.
            source_language: Source language hint (unused by prompt, kept for interface).

        Returns:
            TranslationResult with translated text.

        Raises:
            openai.APIError: If the LM Studio API returns an error.
        """
        prompt = TRANSLATION_PROMPT.format(
            target_language=target_language,
            text=text,
        )

        response = await self._client.chat.completions.create(
            model=self._config.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional translator. "
                        "Return ONLY the translation, nothing else."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        translated = response.choices[0].message.content
        if translated is None:
            raise RuntimeError(
                "LM Studio returned empty response — "
                "check that the model is loaded and responding."
            )

        return TranslationResult(
            translated_text=translated.strip(),
            source_language=source_language,
            target_language=target_language,
            backend_used=self.name,
        )

    def is_available(self) -> bool:
        """Check connectivity by hitting the /v1/models endpoint.

        Returns:
            True if LM Studio is reachable and responds, False otherwise.
        """
        try:
            resp = httpx.get(
                f"{self._config.base_url}/models",
                timeout=5.0,
            )
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, OSError):
            return False

    @property
    def name(self) -> str:
        return "lmstudio"
