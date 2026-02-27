"""OpenCode CLI translation backend using subprocess invocation.

Note: newer opencode versions may block access to external directories (e.g. /tmp)
and no longer support the previous `@/path/to/file` prompt indirection reliably.
We therefore attach the page text as a file via `opencode run -f ... -- <prompt>`.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import tempfile
import os

from src.translation.base import TranslationBackend, TranslationResult
from src.translation.config import OpenCodeConfig

import time
import logging

logger = logging.getLogger(__name__)

INSTRUCTION_TEMPLATE = (
    "Translate the provided text to {target_language}. "
    "Return ONLY the translated text, with no additional commentary, explanations, or notes. "
    "Preserve the original formatting and paragraph structure. "
    "Pay close attention to cohesion and coherence: the translation must read "
    "as natural, fluent {target_language} — sentences must connect logically, "
    "ideas must flow clearly, and the meaning of the original must be fully preserved. "
    "Do not translate word-for-word if it produces unnatural or confusing results; "
    "prefer idiomatic phrasing that conveys the same meaning. "
    "If the text is shown with line numbers like '1:' or editor prefixes, ignore them and do NOT reproduce them.\n\n"
    "The text to translate is in the attached file."
)


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

        logger.info("[INFO] Sending translation prompt to OpenCode CLI (model: %s)", self._config.model)
        start_time = time.perf_counter()

        # Write only the page text to a temp file and attach it.
        # Prefer a file within the current working directory to avoid
        # opencode "external_directory" permission blocks for /tmp.
        tmp_dir = os.getcwd()
        if not os.access(tmp_dir, os.W_OK):
            tmp_dir = None  # fallback to system temp dir

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            prefix="lumos_translate_",
            delete=False,
            encoding="utf-8",
            dir=tmp_dir,
        ) as tmp:
            tmp.write(text)
            tmp_path = tmp.name

        prompt = INSTRUCTION_TEMPLATE.format(target_language=target_language)

        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                "opencode",
                "run",
                "--format",
                "json",
                "-m",
                self._config.model,
                "-f",
                tmp_path,
                "--",
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._config.timeout,
            )
        except asyncio.TimeoutError:
            if proc is not None:
                proc.kill()
                await proc.wait()
            raise RuntimeError(
                f"opencode CLI timed out after {self._config.timeout}s"
            ) from None
        finally:
            os.unlink(tmp_path)

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

    text = _strip_preamble("".join(parts))
    text = _strip_line_ids(text)
    text = _strip_line_number_prefixes(text)
    return text



# Matches LINE#ID prefixes like "1#JB|" or "106#WX|" that the model may echo back
_LINE_ID_RE = re.compile(r"^\d+#[A-Z]{2}\|", re.MULTILINE)


def _strip_line_ids(text: str) -> str:
    """Remove any LINE#ID editor prefixes the model echoed in the translation."""
    return _LINE_ID_RE.sub("", text)


_LINE_NUMBER_RE = re.compile(r"^\s*(\d{1,6}):\s+", re.MULTILINE)


def _strip_line_number_prefixes(text: str) -> str:
    """Strip leading `N:` prefixes if the output looks line-numbered.

    Some opencode file attachment renderers show file contents with line numbers
    (e.g. `1: ...`). Models may translate and echo those prefixes.

    To avoid corrupting legitimate numbered lists, we only strip when the
    majority of non-empty lines start with a small `N:` prefix.
    """
    lines = text.splitlines()
    non_empty = [ln for ln in lines if ln.strip()]
    if not non_empty:
        return text

    matches = 0
    for ln in non_empty:
        if re.match(r"^\s*\d{1,6}:\s+", ln):
            matches += 1

    if matches / max(1, len(non_empty)) < 0.70:
        return text

    return _LINE_NUMBER_RE.sub("", text)


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
