import os
from pathlib import Path


def _configure_tessdata_prefix() -> None:
    """Best-effort Tesseract language data setup.

    This app supports OCR languages that require `*.traineddata` files.
    If `TESSDATA_PREFIX` is missing or points to a non-existent directory,
    we try a few common locations.
    """

    def _looks_like_tessdata_dir(p: Path) -> bool:
        if not p.is_dir():
            return False
        # Only consider it valid if it actually contains language data.
        return any(p.glob("*.traineddata"))

    current = os.environ.get("TESSDATA_PREFIX")
    if current:
        p = Path(current)
        if _looks_like_tessdata_dir(p):
            return
        # If it's set but invalid, remove it so Tesseract can fall back to its
        # built-in default data locations.
        os.environ.pop("TESSDATA_PREFIX", None)

    repo_tessdata = Path(__file__).resolve().parent / "tessdata"
    if _looks_like_tessdata_dir(repo_tessdata):
        os.environ["TESSDATA_PREFIX"] = str(repo_tessdata)
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
