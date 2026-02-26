"""OpenCode CLI translation backend using subprocess invocation."""

from __future__ import annotations

import asyncio
import json
import shutil

from src.translation.base import TranslationBackend, TranslationResult
from src.translation.config import OpenCodeConfig

TRANSLATION_PROMPT = """\
Translate the following text to {target_language}. \
Return ONLY the translated text, with no additional commentary, explanations, or notes.
Preserve the original formatting and paragraph structure.

Text to translate:
{text}"""


class OpenCodeBackend(TranslationBackend):
    """Translation backend that shells out to the ``opencode`` CLI."""

    def __init__(self, config: OpenCodeConfig | None = None) -> None:
        self._config = config or OpenCodeConfig()

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> TranslationResult:
        """Translate text by invoking ``opencode run``.

        The CLI is called with ``--format json`` which emits newline-delimited
        JSON events.  We collect all ``"text"`` events and concatenate
        their ``part.text`` fields to reconstruct the full response.

        Args:
            text: The text to translate.
            target_language: Language to translate into.
            source_language: Source language hint (kept for interface).

        Returns:
            TranslationResult with translated text.

        Raises:
            RuntimeError: If opencode is not installed or the subprocess fails.
        """
        if not self.is_available():
            raise RuntimeError(
                "opencode CLI is not installed or not found in PATH."
            )

        prompt = TRANSLATION_PROMPT.format(
            target_language=target_language,
            text=text,
        )

        proc = await asyncio.create_subprocess_exec(
            "opencode",
            "run",
            "--format",
            "json",
            "-m",
            self._config.model,
            prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._config.timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(
                f"opencode CLI timed out after {self._config.timeout}s"
            ) from None

        if proc.returncode != 0:
            stderr_text = stderr_bytes.decode(errors="replace").strip()
            raise RuntimeError(
                f"opencode CLI exited with code {proc.returncode}: {stderr_text}"
            )

        translated_text = _parse_opencode_json(stdout_bytes.decode(errors="replace"))

        if not translated_text.strip():
            raise RuntimeError(
                "opencode CLI returned empty translation — "
                "check model availability and prompt."
            )

        return TranslationResult(
            translated_text=translated_text.strip(),
            source_language=source_language,
            target_language=target_language,
            backend_used=self.name,
        )

    def is_available(self) -> bool:
        """Check if the ``opencode`` binary is on PATH.

        Returns:
            True if ``opencode`` is found, False otherwise.
        """
        return shutil.which("opencode") is not None

    @property
    def name(self) -> str:
        return "opencode"


def _parse_opencode_json(raw_output: str) -> str:
    """Parse newline-delimited JSON events from ``opencode run --format json``.

    The output consists of one JSON object per line.  Events with
    ``"type": "text"`` carry the actual response content in
    ``part.text``.  We concatenate all such fragments.

    Some models (e.g. github-copilot/gpt-5-mini) prepend a reasoning
    preamble to the response (e.g. "I detect trivial intent — ...") before
    the actual translated text, separated by a blank line (``\n\n``).
    ``_strip_preamble`` removes that prefix so callers receive clean output.

    Args:
        raw_output: Raw stdout from the opencode process.

    Returns:
        The concatenated translated text, with any reasoning preamble removed.
    """
    parts: list[str] = []
    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Non-JSON output (e.g. progress messages) — skip
            continue

        if event.get("type") == "text":
            text_fragment = event.get("part", {}).get("text", "")
            if text_fragment:
                parts.append(text_fragment)

    return _strip_preamble("".join(parts))


def _strip_preamble(text: str) -> str:
    """Remove model reasoning preambles that precede the actual translation.

    Models like github-copilot/gpt-5-mini emit a line such as::

        I detect trivial intent — ... My approach: ...

    followed by a blank line before the real content.  This function
    detects that pattern and returns only the content after the last
    such preamble block.

    Args:
        text: Raw model output, potentially containing a reasoning prefix.

    Returns:
        The text with any leading reasoning preamble stripped.
    """
    # Preamble blocks are separated from the real content by \n\n.
    # If the model emitted reasoning, everything up to the first \n\n
    # that is followed by non-empty content is considered preamble.
    # We detect preamble by looking for known marker phrases.
    _PREAMBLE_MARKERS = (
        "I detect ",
        "My approach:",
        "I'll ",
        "I will ",
    )

    blocks = text.split("\n\n")
    # Find the first block that does NOT look like a preamble
    for i, block in enumerate(blocks):
        stripped = block.strip()
        if not stripped:
            continue
        is_preamble = any(stripped.startswith(m) for m in _PREAMBLE_MARKERS)
        if not is_preamble:
            return "\n\n".join(blocks[i:]).strip()

    return text.strip()
