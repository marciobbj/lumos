import os
os.environ.setdefault("TESSDATA_PREFIX", "/home/io/tessdata_temp")

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
