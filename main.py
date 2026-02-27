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


import logging
import flet as ft

from src.diagnostics.requirements import DOCS_URL, check_startup_requirements
from src.projects.manager import Project
from src.ui.project_list import ProjectListScreen
from src.ui.app import OCRApp


class LumosApp:
    """Top-level navigator that switches between the project list and scan screens."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        OCRApp.configure_page(page)
        self._requirements_dialog: ft.AlertDialog | None = None
        self._requirements_items: ft.Column | None = None

        issues = check_startup_requirements()
        if issues:
            self._show_requirements_gate(issues)
            return

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

    def _show_requirements_gate(self, issues) -> None:
        """Block the app until requirements are satisfied."""
        self.page.controls.clear()
        self.page.add(
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    [
                        ft.Text("Lumos", size=28, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Checking startup requirements...",
                            size=13,
                            color="#757575",
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                    tight=True,
                ),
            )
        )
        self.page.update()

        self._requirements_items = ft.Column(
            controls=self._build_requirement_controls(issues),
            spacing=6,
        )

        intro = ft.Text(
            "Lumos cannot continue until the missing requirements are installed/configured.",
            size=13,
        )

        content = ft.Container(
            width=560,
            content=ft.Column(
                [intro, ft.Divider(height=1), self._requirements_items],
                spacing=10,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

        self._requirements_dialog = ft.AlertDialog(
            title=ft.Text("Missing requirements", size=18, weight=ft.FontWeight.BOLD),
            content=content,
            actions=[
                ft.TextButton(
                    "Open documentation",
                    on_click=lambda _: self.page.launch_url(DOCS_URL),
                ),
                ft.FilledButton(
                    "Re-check",
                    on_click=self._on_recheck_requirements,
                    style=ft.ButtonStyle(bgcolor="#1976D2", color="white"),
                ),
            ],
            modal=True,
        )
        self.page.show_dialog(self._requirements_dialog)

    def _build_requirement_controls(self, issues) -> list[ft.Control]:
        items: list[ft.Control] = []
        for issue in issues:
            prefix = "[WARNING]" if issue.severity == "warning" else "[ERROR]"
            items.append(ft.Text(f"{prefix} {issue.title}", size=13, weight=ft.FontWeight.W_600))
            items.append(ft.Text(issue.details, size=12, color="#616161"))
        return items

    def _on_recheck_requirements(self, e) -> None:
        issues = check_startup_requirements()
        if issues:
            if self._requirements_items is not None:
                self._requirements_items.controls = self._build_requirement_controls(issues)
                self.page.update()
            return

        if self._requirements_dialog is not None:
            self.page.pop_dialog()
        self._show_project_list()


def main(page: ft.Page) -> None:
    """Flet app entry point — called by ft.app() with the page."""
    LumosApp(page)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    ft.app(main)
