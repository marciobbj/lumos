"""Download Tesseract language data into ./tessdata.

This repository does not ship `*.traineddata` files.
Run this script to fetch the languages used by the app.

Usage:
  python scripts/download_tessdata.py
  python scripts/download_tessdata.py eng por fra deu spa
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path


TESSDATA_FAST_BASE = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main"
DEFAULT_LANGS = ["eng", "por", "fra", "deu", "spa"]


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read()


def main(argv: list[str]) -> int:
    langs = argv[1:] if len(argv) > 1 else DEFAULT_LANGS
    tessdata_dir = Path(__file__).resolve().parent.parent / "tessdata"
    tessdata_dir.mkdir(parents=True, exist_ok=True)

    for lang in langs:
        dest = tessdata_dir / f"{lang}.traineddata"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"skip {lang}: already exists ({dest.stat().st_size} bytes)")
            continue

        url = f"{TESSDATA_FAST_BASE}/{lang}.traineddata"
        print(f"download {lang}: {url}")
        data = _download(url)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
        print(f"ok {lang}: {dest} ({dest.stat().st_size} bytes)")

    print("\nDone.")
    print("If needed, point Tesseract to this directory:")
    print(f"  export TESSDATA_PREFIX=\"{tessdata_dir}\"")
    print("  tesseract --list-langs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
