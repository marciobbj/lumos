import os
os.environ.setdefault("TESSDATA_PREFIX", "/home/io/tessdata_temp")

"""Lumos — Desktop OCR + Translation App."""

import logging
import flet as ft
from src.ui.app import OCRApp


def main(page: ft.Page) -> None:
    """Flet app entry point — called by ft.app() with the page."""
    OCRApp(page)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    ft.app(main)
