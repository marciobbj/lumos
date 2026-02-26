"""Project list screen — shown at app startup to browse/create/open projects."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import flet as ft

from src.projects.manager import Project, ProjectManager, ProjectStatus

logger = logging.getLogger(__name__)


class ProjectListScreen:
    """Displays all existing projects and lets the user create a new one.

    Calls `on_open_project(project)` when the user opens an existing project.
    Calls `on_new_project(project)` when a new project is created.
    """

    def __init__(
        self,
        page: ft.Page,
        on_open_project: Callable[[Project], None],
        on_new_project: Callable[[Project], None],
    ) -> None:
        self.page = page
        self._on_open_project = on_open_project
        self._on_new_project = on_new_project
        self._manager = ProjectManager()
        self._pending_project_name: str | None = None

        # Register FilePicker as a page service (Flet 0.81+).
        # Clear any lingering services from a previous screen first.
        self._file_picker = ft.FilePicker()
        page.services.clear()
        page.services.append(self._file_picker)
        page.update()

        self._build()


    def _build(self) -> None:
        self.page.controls.clear()

        projects = self._manager.list_projects()

        header = ft.Row(
            [
                ft.Text("Lumos", size=26, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.FilledButton(
                    "New Project",
                    icon=ft.Icons.ADD,
                    style=ft.ButtonStyle(bgcolor="#1976D2", color="white"),
                    on_click=self._on_new_project_click,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        divider = ft.Divider(height=1)

        if projects:
            list_view = ft.Column(
                controls=[self._project_card(p) for p in projects],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
        else:
            list_view = ft.Column(
                [
                    ft.Container(height=60),
                    ft.Icon(ft.Icons.FOLDER_OPEN_OUTLINED, size=64, color="#BDBDBD"),
                    ft.Text(
                        "No projects yet",
                        size=18,
                        color="#9E9E9E",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Click \"New Project\" to start your first scan.",
                        size=13,
                        color="#BDBDBD",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )

        self.page.add(
            ft.Column(
                [header, divider, list_view],
                spacing=12,
                expand=True,
            )
        )
        self.page.update()

    def _project_card(self, project: Project) -> ft.Container:
        """Build a card for a single project entry."""
        status_chip = ft.Container(
            content=ft.Text(
                project.status.label,
                size=11,
                color="white",
                weight=ft.FontWeight.W_500,
            ),
            bgcolor=project.status.color,
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
        )

        # Progress indicator
        progress_widgets: list[ft.Control] = []
        if project.status in (
            ProjectStatus.OCR_PAUSED,
            ProjectStatus.OCR_IN_PROGRESS,
            ProjectStatus.OCR_DONE,
            ProjectStatus.TRANSLATING,
            ProjectStatus.TRANSLATION_PAUSED,
            ProjectStatus.DONE,
        ):
            if project.ocr_total_pages > 0:
                progress_widgets.append(
                    ft.Text(
                        f"OCR: {project.ocr_completed_pages}/{project.ocr_total_pages} pages",
                        size=11,
                        color="#757575",
                    )
                )
            if project.translation_total_pages > 0:
                progress_widgets.append(
                    ft.Text(
                        f"Translation: {project.translation_completed_pages}/"
                        f"{project.translation_total_pages} pages",
                        size=11,
                        color="#757575",
                    )
                )

        pdf_name = Path(project.source_pdf).name if project.source_pdf else "—"
        updated = project.updated_at_dt.strftime("%d/%m/%Y %H:%M")

        card_content = ft.Row(
            [
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    project.name.replace("_", " "),
                                    size=15,
                                    weight=ft.FontWeight.W_600,
                                    expand=True,
                                ),
                                status_chip,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            pdf_name,
                            size=12,
                            color="#757575",
                        ),
                        ft.Row(progress_widgets, spacing=12) if progress_widgets else ft.Container(height=0),
                        ft.Text(
                            f"Last updated: {updated}",
                            size=11,
                            color="#BDBDBD",
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.OPEN_IN_NEW,
                            tooltip="Open project",
                            icon_color="#1976D2",
                            on_click=lambda e, p=project: self._open_project(p),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            tooltip="Delete project",
                            icon_color="#D32F2F",
                            on_click=lambda e, p=project: self._confirm_delete(p),
                        ),
                    ],
                    spacing=0,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=card_content,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border=ft.border.all(1, "#E0E0E0"),
            border_radius=8,
            bgcolor="white",
            on_click=lambda e, p=project: self._open_project(p),
            ink=True,
        )


    def _open_project(self, project: Project) -> None:
        self._on_open_project(project)

    def _on_new_project_click(self, e) -> None:
        """Show dialog to enter project name."""
        name_field = ft.TextField(
            label="Project name",
            hint_text="e.g. Book 01 - Origin",
            autofocus=True,
            on_submit=lambda ev: self._on_name_confirmed(ev, name_field, dialog),
        )
        error_text = ft.Text("", color="#D32F2F", size=12, visible=False)

        dialog = ft.AlertDialog(
            title=ft.Text("New Project"),
            content=ft.Column(
                [
                    ft.Text("Enter a name for the project:", size=13),
                    name_field,
                    error_text,
                ],
                spacing=8,
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton(
                    "Next: Select PDF",
                    style=ft.ButtonStyle(bgcolor="#1976D2", color="white"),
                    on_click=lambda ev: self._on_name_confirmed(ev, name_field, dialog, error_text),
                ),
            ],
            modal=True,
        )
        self.page.show_dialog(dialog)

    def _on_name_confirmed(
        self,
        e,
        name_field: ft.TextField,
        dialog: ft.AlertDialog,
        error_text: ft.Text | None = None,
    ) -> None:
        name = (name_field.value or "").strip()
        if not name:
            if error_text:
                error_text.value = "Please enter a project name."
                error_text.visible = True
                self.page.update()
            return
        if self._manager.project_name_exists(name):
            if error_text:
                error_text.value = "A project with this name already exists."
                error_text.visible = True
                self.page.update()
            return
        self._pending_project_name = name
        self.page.pop_dialog()
        # Now pick the PDF
        import asyncio
        asyncio.ensure_future(self._pick_pdf_for_new_project())

    async def _pick_pdf_for_new_project(self) -> None:
        result = await self._file_picker.pick_files(
            dialog_title="Select the PDF for this project",
            allowed_extensions=["pdf"],
            allow_multiple=False,
        )
        if not result or not result[0].path:
            self._pending_project_name = None
            return

        pdf_path = result[0].path
        name = self._pending_project_name or Path(pdf_path).stem
        self._pending_project_name = None

        project = self._manager.create_project(name, pdf_path)
        self._on_new_project(project)

    def _confirm_delete(self, project: Project) -> None:
        def do_delete(_):
            self.page.pop_dialog()
            self._manager.delete_project(project)
            self._build()  # refresh list

        dialog = ft.AlertDialog(
            title=ft.Text("Delete Project"),
            content=ft.Text(
                f'Delete "{project.name.replace("_", " ")}" and all its files?'
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton(
                    "Delete",
                    style=ft.ButtonStyle(bgcolor="#D32F2F", color="white"),
                    on_click=do_delete,
                ),
            ],
            modal=True,
        )
        self.page.show_dialog(dialog)

    def refresh(self) -> None:
        """Re-render the screen (e.g. after returning from a project)."""
        self._build()
