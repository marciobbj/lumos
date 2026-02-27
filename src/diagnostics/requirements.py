"""Startup requirement checks.

This module performs best-effort checks for external/system dependencies that
Python packaging cannot guarantee (e.g. Tesseract, Poppler, opencode CLI).

The UI can use these checks to block startup until requirements are met.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
import sys
from typing import Iterable


DOCS_URL = "https://github.com/marciobbj/lumos#prerequisites"

SUPPORTED_TESS_LANGS = ["por", "eng", "fra", "deu", "spa"]


@dataclass(frozen=True)
class RequirementIssue:
    id: str
    title: str
    details: str
    severity: str = "error"  # "error" | "warning"


def check_startup_requirements() -> list[RequirementIssue]:
    issues: list[RequirementIssue] = []

    if sys.version_info < (3, 12):
        issues.append(
            RequirementIssue(
                id="python_version",
                title="Python >= 3.12",
                details=f"Current version: {sys.version.split()[0]}",
                severity="error",
            )
        )

    tesseract = shutil.which("tesseract")
    if not tesseract:
        issues.append(
            RequirementIssue(
                id="tesseract",
                title="Tesseract OCR (tesseract executable)",
                details=(
                    "Not found in PATH. Install it via your package manager "
                    "(e.g. 'sudo apt-get install tesseract-ocr')."
                ),
                severity="error",
            )
        )
    else:
        missing_langs = _missing_tesseract_langs(SUPPORTED_TESS_LANGS)
        if missing_langs:
            issues.append(
                RequirementIssue(
                    id="tesseract_langs",
                    title="Tesseract language data (por/eng/fra/deu/spa)",
                    details=(
                        "Missing: "
                        + ", ".join(missing_langs)
                        + ". Install the language packs (e.g. 'tesseract-ocr-por') or set TESSDATA_PREFIX."
                    ),
                    severity="error",
                )
            )

    missing_poppler = [cmd for cmd in ("pdftoppm", "pdfinfo") if shutil.which(cmd) is None]
    if missing_poppler:
        issues.append(
            RequirementIssue(
                id="poppler",
                title="Poppler (pdftoppm/pdfinfo)",
                details=(
                    "Not found in PATH: "
                    + ", ".join(missing_poppler)
                    + ". Install 'poppler-utils' (Ubuntu/Debian) or 'poppler' (macOS)."
                ),
                severity="error",
            )
        )

    if shutil.which("opencode") is None:
        issues.append(
            RequirementIssue(
                id="opencode",
                title="opencode CLI (OpenCode translation)",
                details="Not found in PATH. Install and configure opencode to enable translation.",
                severity="error",
            )
        )

    return issues


def _missing_tesseract_langs(required: Iterable[str]) -> list[str]:
    """Return languages from `required` missing in `tesseract --list-langs`.

    Best-effort: if we cannot query languages, we return an empty list to avoid
    blocking the UI (the OCR path will raise a clear error later).
    """
    try:
        proc = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            timeout=4.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    langs = _parse_tesseract_list_langs(out)
    if not langs:
        return []

    missing: list[str] = []
    for lang in required:
        if lang not in langs:
            missing.append(lang)
    return missing


def _parse_tesseract_list_langs(output: str) -> set[str]:
    langs: set[str] = set()
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("list of available languages"):
            continue
        if line.lower().startswith("tesseract") and "languages" in line.lower():
            # Some builds print additional headers.
            continue
        if " " in line or "\t" in line:
            # Be conservative; language codes are typically single tokens.
            continue
        langs.add(line)
    return langs
