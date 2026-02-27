import os
from pathlib import Path


def _configure_tessdata_prefix() -> None:
    """Best-effort Tesseract language data setup.

    This app supports OCR languages that require `*.traineddata` files.
    If `TESSDATA_PREFIX` is missing or points to a non-existent directory,
    we try a few common locations.
    """

    current = os.environ.get("TESSDATA_PREFIX")
    if current and Path(current).is_dir():
        return

    def _looks_like_tessdata_dir(p: Path) -> bool:
        if not p.is_dir():
            return False
        # Only consider it valid if it actually contains language data.
        return any(p.glob("*.traineddata"))

    repo_tessdata = Path(__file__).resolve().parent / "tessdata"
    candidates = [
        repo_tessdata,
        Path("/home/io/tessdata_temp"),
        Path("/usr/share/tessdata"),
    ]
    for p in candidates:
        if _looks_like_tessdata_dir(p):
            os.environ["TESSDATA_PREFIX"] = str(p)
            return


_configure_tessdata_prefix()

"""Lumos — Desktop OCR + Translation App."""

import logging
import flet as ft

from src.projects.manager import Project
from src.ui.project_list import ProjectListScreen
from src.ui.app import OCRApp


class LumosApp:
    """Top-level navigator that switches between the project list and scan screens."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        OCRApp.configure_page(page)
        self._show_project_list()

    def _show_project_list(self) -> None:
        ProjectListScreen(
            page=self.page,
            on_open_project=self._open_project,
            on_new_project=self._open_project,
        )

    def _open_project(self, project: Project) -> None:
        OCRApp(
            page=self.page,
            project=project,
            on_back=self._show_project_list,
        )


def main(page: ft.Page) -> None:
    """Flet app entry point — called by ft.app() with the page."""
    LumosApp(page)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    ft.app(main)
