"""Project scan screen — OCR + Translation for a single Lumos project.

Supports:
- Resuming a partially-completed OCR (pages already done are loaded from disk)
- Pausing/resuming both OCR and translation phases
- Persisting all progress to the project folder
"""

from __future__ import annotations

import asyncio
import logging
import time

from pathlib import Path
from typing import Callable

import flet as ft

from src.ocr import OCREngine, OCRResult
from src.translation import get_backend, TranslationConfig, BackendType
from src.translation.config import LMStudioConfig, OpenCodeConfig
from src.ui.components import section_header, result_text_area, char_count_label
from src.projects.manager import Project, ProjectStatus

logger = logging.getLogger(__name__)


class OCRApp:
    """Scan screen for a single project — OCR extraction + translation.

    Args:
        page:            Flet Page.
        project:         The project being worked on.
        on_back:         Callback to return to the project list screen.
    """

    def __init__(
        self,
        page: ft.Page,
        project: Project,
        on_back: Callable[[], None],
    ) -> None:
        self.page = page
        self._project = project
        self._on_back = on_back

        # Runtime state
        self._ocr_result: OCRResult | None = None
        self._translated_text: str | None = None

        # Pause / cancel signals
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # not paused by default (set = running)
        self._cancel_requested = False

        self._build_ui()
        self._restore_state()

    # ------------------------------------------------------------------
    # Page setup (called once per app launch, not per screen)
    # ------------------------------------------------------------------

    @staticmethod
    def configure_page(page: ft.Page) -> None:
        page.title = "Lumos"
        page.window.width = 900
        page.window.height = 700
        page.window.min_width = 800
        page.window.min_height = 600
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = "#F5F5F5"

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.page.controls.clear()

        # ── Header with back button ───────────────────────────────────
        project_title = self._project.name.replace("_", " ")
        header = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Back to projects",
                    on_click=self._on_back_click,
                    icon_color="#1976D2",
                ),
                ft.Text(project_title, size=20, weight=ft.FontWeight.BOLD, expand=True),
                self._build_status_chip(),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # ── PDF info row ───────────────────────────────────────────────
        pdf_name = Path(self._project.source_pdf).name
        pdf_info = ft.Text(
            f"PDF: {pdf_name}",
            size=12,
            color="#757575",
        )

        # ── Settings card ──────────────────────────────────────────────
        self._ocr_language = ft.Dropdown(
            label="OCR Language",
            value=self._project.ocr_language,
            options=[
                ft.DropdownOption(key="por+eng", text="Portuguese + English"),
                ft.DropdownOption(key="eng", text="English"),
                ft.DropdownOption(key="por", text="Portuguese"),
                ft.DropdownOption(key="fra", text="French"),
                ft.DropdownOption(key="deu", text="German"),
                ft.DropdownOption(key="spa", text="Spanish"),
            ],
            width=250,
        )

        self._backend_radio = ft.RadioGroup(
            content=ft.Row(
                [
                    ft.Radio(value="lmstudio", label="LM Studio"),
                    ft.Radio(value="opencode", label="OpenCode"),
                ],
            ),
            value=self._project.translation_backend,
            on_change=self._on_backend_change,
        )

        self._target_language = ft.TextField(
            label="Target Language",
            value=self._project.translation_target_language,
            width=200,
        )

        self._lmstudio_url = ft.TextField(
            label="LM Studio URL",
            value=self._project.translation_lmstudio_url,
            width=300,
        )
        self._lmstudio_model = ft.TextField(
            label="LM Studio Model",
            value=self._project.translation_lmstudio_model,
            width=200,
        )
        self._lmstudio_settings = ft.Column(
            [
                ft.Row([self._lmstudio_url, self._lmstudio_model], spacing=10),
            ],
            visible=(self._project.translation_backend == "lmstudio"),
        )

        settings_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        section_header("Settings"),
                        ft.Row([self._ocr_language, self._target_language], spacing=15),
                        ft.Row(
                            [
                                ft.Text("Translation Backend:", size=13),
                                self._backend_radio,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        self._lmstudio_settings,
                    ],
                    spacing=10,
                ),
                padding=15,
            ),
        )

        # ── Action buttons ────────────────────────────────────────────
        self._btn_ocr = ft.FilledButton(
            "Extract Text (OCR)",
            icon=ft.Icons.DOCUMENT_SCANNER,
            on_click=self._on_run_ocr,
            style=ft.ButtonStyle(bgcolor="#1976D2", color="white"),
        )
        self._btn_ocr_translate = ft.FilledButton(
            "Extract + Translate",
            icon=ft.Icons.TRANSLATE,
            on_click=self._on_run_ocr_translate,
            style=ft.ButtonStyle(bgcolor="#388E3C", color="white"),
        )
        self._btn_pause_resume = ft.OutlinedButton(
            "Pause",
            icon=ft.Icons.PAUSE,
            on_click=self._on_pause_resume,
            visible=False,
        )
        action_row = ft.Row(
            [self._btn_ocr, self._btn_ocr_translate, self._btn_pause_resume],
            spacing=10,
        )

        # ── Progress section ──────────────────────────────────────────
        self._progress_bar = ft.ProgressBar(visible=False, expand=True)
        self._status_text = ft.Text("", size=12, color="#757575")
        progress_section = ft.Column(
            [self._progress_bar, self._status_text],
            spacing=5,
        )

        # ── Results tabs ──────────────────────────────────────────────
        self._ocr_text_field = result_text_area()
        self._ocr_char_count = char_count_label()
        self._translation_text_field = result_text_area()
        self._translation_char_count = char_count_label()

        ocr_tab_content = ft.Column(
            [self._ocr_text_field, self._ocr_char_count],
            spacing=5,
            expand=True,
        )
        translation_tab_content = ft.Column(
            [self._translation_text_field, self._translation_char_count],
            spacing=5,
            expand=True,
        )

        results_tabs = ft.Tabs(
            content=ft.Column(
                [
                    ft.TabBar(
                        tabs=[
                            ft.Tab(label="OCR Result"),
                            ft.Tab(label="Translation"),
                        ],
                    ),
                    ft.TabBarView(
                        controls=[ocr_tab_content, translation_tab_content],
                        expand=True,
                    ),
                ],
                expand=True,
            ),
            length=2,
            selected_index=0,
            expand=True,
        )

        # ── Save buttons ──────────────────────────────────────────────
        self._btn_save_ocr = ft.OutlinedButton(
            "Save OCR Text",
            icon=ft.Icons.SAVE_ALT,
            on_click=self._on_save_ocr,
            disabled=True,
        )
        self._btn_save_translation = ft.OutlinedButton(
            "Save Translation",
            icon=ft.Icons.SAVE_ALT,
            on_click=self._on_save_translation,
            disabled=True,
        )
        save_row = ft.Row(
            [self._btn_save_ocr, self._btn_save_translation],
            spacing=10,
        )

        # ── Assemble ──────────────────────────────────────────────────
        self.page.add(
            ft.Column(
                [
                    header,
                    pdf_info,
                    ft.Divider(height=1),
                    settings_card,
                    action_row,
                    progress_section,
                    results_tabs,
                    save_row,
                ],
                spacing=12,
                expand=True,
            )
        )
        self.page.update()

    def _build_status_chip(self) -> ft.Container:
        return ft.Container(
            content=ft.Text(
                self._project.status.label,
                size=11,
                color="white",
                weight=ft.FontWeight.W_500,
            ),
            bgcolor=self._project.status.color,
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
        )

    # ------------------------------------------------------------------
    # Restore persisted state
    # ------------------------------------------------------------------

    def _restore_state(self) -> None:
        """Load previously saved OCR / translation results into the UI."""
        ocr_text = self._project.load_ocr_result()
        if ocr_text:
            self._ocr_text_field.value = ocr_text
            self._ocr_char_count.value = f"{len(ocr_text):,} characters"
            self._btn_save_ocr.disabled = False

            # Reconstruct OCRResult so translation can use it
            pages = self._project.load_ocr_pages()
            if not pages:
                # Fall back: split by page markers
                import re
                parts = re.split(r"--- Page \d+ ---\n\n", ocr_text)
                pages = [p for p in parts if p.strip()]
            self._ocr_result = OCRResult(
                text=ocr_text,
                pages=pages,
                total_pages=self._project.ocr_total_pages or len(pages),
                language=self._project.ocr_language,
                source_file=self._project.source_pdf,
            )

        trans_text = self._project.load_translation_result()
        if trans_text:
            self._translated_text = trans_text
            self._translation_text_field.value = trans_text
            self._translation_char_count.value = f"{len(trans_text):,} characters"
            self._btn_save_translation.disabled = False

        # Update action button labels based on current status
        self._refresh_action_buttons()
        self.page.update()

    def _refresh_action_buttons(self) -> None:
        """Adjust action button labels/states based on project status."""
        status = self._project.status
        can_ocr = status in (ProjectStatus.PENDING, ProjectStatus.OCR_PAUSED)
        can_translate = status in (
            ProjectStatus.OCR_DONE,
            ProjectStatus.TRANSLATION_PAUSED,
        )

        if status == ProjectStatus.OCR_PAUSED:
            self._btn_ocr.content = "Resume OCR"
            self._btn_ocr.icon = ft.Icons.PLAY_ARROW
        else:
            self._btn_ocr.content = "Extract Text (OCR)"
            self._btn_ocr.icon = ft.Icons.DOCUMENT_SCANNER

        if status == ProjectStatus.TRANSLATION_PAUSED:
            self._btn_ocr_translate.content = "Resume Translation"
            self._btn_ocr_translate.icon = ft.Icons.PLAY_ARROW
            self._btn_ocr_translate.style = ft.ButtonStyle(bgcolor="#7B1FA2", color="white")
        elif status == ProjectStatus.OCR_DONE:
            self._btn_ocr_translate.content = "Translate OCR Result"
            self._btn_ocr_translate.icon = ft.Icons.TRANSLATE
            self._btn_ocr_translate.style = ft.ButtonStyle(bgcolor="#388E3C", color="white")
        else:
            self._btn_ocr_translate.content = "Extract + Translate"
            self._btn_ocr_translate.icon = ft.Icons.TRANSLATE
            self._btn_ocr_translate.style = ft.ButtonStyle(bgcolor="#388E3C", color="white")

        if status == ProjectStatus.DONE:
            self._btn_ocr.disabled = True
            self._btn_ocr_translate.disabled = True
        else:
            self._btn_ocr.disabled = not (can_ocr or status == ProjectStatus.PENDING)
            self._btn_ocr_translate.disabled = not (
                can_translate
                or status in (ProjectStatus.PENDING, ProjectStatus.OCR_DONE)
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_back_click(self, e) -> None:
        # If processing, just pause first
        if self._project.status in (
            ProjectStatus.OCR_IN_PROGRESS,
            ProjectStatus.TRANSLATING,
        ):
            await self._pause()
        self._on_back()

    async def _on_run_ocr(self, e) -> None:
        if self._project.status == ProjectStatus.OCR_PAUSED:
            await self._run_ocr(translate=False, resume=True)
        else:
            await self._run_ocr(translate=False, resume=False)

    async def _on_run_ocr_translate(self, e) -> None:
        if self._project.status == ProjectStatus.TRANSLATION_PAUSED:
            await self._run_translation(resume=True)
        elif self._project.status == ProjectStatus.OCR_DONE:
            await self._run_translation(resume=False)
        else:
            await self._run_ocr(translate=True, resume=False)

    def _on_backend_change(self, e) -> None:
        self._lmstudio_settings.visible = (
            self._backend_radio.value == "lmstudio"
        )
        self.page.update()

    async def _on_pause_resume(self, e) -> None:
        if self._project.status.can_pause():
            await self._pause()
        elif self._project.status.can_resume():
            # Resume is handled by re-clicking the main action button
            pass

    async def _on_save_ocr(self, e) -> None:
        if self._ocr_result:
            path = self._project.ocr_path
            path.write_text(self._ocr_result.text, encoding="utf-8")
            self._show_snackbar(f"OCR text saved to {path.name}")

    async def _on_save_translation(self, e) -> None:
        if self._translated_text:
            path = self._project.translation_path
            path.write_text(self._translated_text, encoding="utf-8")
            self._show_snackbar(f"Translation saved to {path.name}")

    # ------------------------------------------------------------------
    # Core processing — OCR
    # ------------------------------------------------------------------

    async def _run_ocr(self, translate: bool, resume: bool) -> None:
        """Run OCR on the project PDF, optionally resuming from a checkpoint."""
        self._cancel_requested = False
        self._pause_event.set()  # ensure we start un-paused

        # Determine starting page
        start_page = 0
        existing_pages: list[str] = []
        if resume:
            existing_pages = self._project.load_ocr_pages()
            start_page = len(existing_pages)

        self._set_project_status(ProjectStatus.OCR_IN_PROGRESS)
        self._set_processing(True, show_pause=True)
        self._set_status("Starting OCR...")

        # Persist current settings
        self._project.ocr_language = self._ocr_language.value or "por+eng"
        self._project.save()

        try:
            engine = OCREngine(language=self._project.ocr_language)
            loop = asyncio.get_event_loop()

        # Convert PDF to images (all pages)
        conv_start = time.perf_counter()
        self._set_status("Converting PDF to images...")
        images = await loop.run_in_executor(
            None,
            engine._convert_pdf_to_images,
            self._project.source_pdf,
        )
        conv_duration = time.perf_counter() - conv_start
        logger.info("[INFO] PDF conversion took %.2fs", conv_duration)
        total = len(images)
        self._project.ocr_total_pages = total
        self._project.save()


            pages_text: list[str] = list(existing_pages)

            for i, image in enumerate(images):
                # Skip already-processed pages
                if i < start_page:
                    image.close()
                    continue

                # ── Pause point ──────────────────────────────────────
                await self._pause_event.wait()
                if self._cancel_requested:
                    image.close()
                    break

                self._progress_bar.value = i / total
                self._status_text.value = f"OCR page {i + 1}/{total}..."
                self.page.update()
                self.page.update()

                page_ocr_start = time.perf_counter()
                try:
                    text = await loop.run_in_executor(
                        None, engine._extract_text_from_image, image
                    )
                except Exception as exc:
                    logger.warning("OCR failed on page %d: %s", i + 1, exc)
                    text = f"[PAGE {i + 1} OCR FAILED]\n"
                finally:
                    image.close()
                page_ocr_duration = time.perf_counter() - page_ocr_start
                logger.info("[INFO] OCR page %d/%d took %.2fs", i + 1, total, page_ocr_duration)

                pages_text.append(text)
                self._project.save_ocr_page(i, text)
                self._project.ocr_completed_pages = len(pages_text)
                self._project.touch()
                self._project.save()

                # Live preview
                full_text = engine._join_pages(pages_text)
                self._ocr_text_field.value = full_text
                self._ocr_char_count.value = f"{len(full_text):,} characters"
                self._btn_save_ocr.disabled = False
                self.page.update()

            if self._cancel_requested:
                # Paused mid-OCR
                return

            # OCR complete
            full_text = engine._join_pages(pages_text)
            self._ocr_result = OCRResult(
                text=full_text,
                pages=pages_text,
                total_pages=total,
                language=self._project.ocr_language,
                source_file=self._project.source_pdf,
            )
            self._project.save_ocr_result(full_text)
            self._project.ocr_completed_pages = total
            self._set_project_status(ProjectStatus.OCR_DONE)

            self._ocr_text_field.value = full_text
            self._ocr_char_count.value = f"{len(full_text):,} characters"
            self._btn_save_ocr.disabled = False
            self._set_status("OCR complete!")
            self._progress_bar.value = 1.0

            if translate:
                self.page.update()
                await asyncio.sleep(0.3)
                await self._run_translation(resume=False)
            else:
                self._show_snackbar("OCR complete!")

        except Exception as exc:
            logger.exception("OCR failed")
            self._project.status = ProjectStatus.ERROR
            self._project.error_message = str(exc)
            self._project.save()
            self._show_error(str(exc))
        finally:
            self._set_processing(False, show_pause=False)
            self._refresh_action_buttons()
            self.page.update()

    # ------------------------------------------------------------------
    # Core processing — Translation
    # ------------------------------------------------------------------

    async def _run_translation(self, resume: bool) -> None:
        """Translate the OCR pages, optionally resuming from a checkpoint."""
        if not self._ocr_result:
            self._show_error("No OCR result available. Run OCR first.")
            return

        self._cancel_requested = False
        self._pause_event.set()

        start_page = 0
        translated_parts: list[str] = []
        if resume:
            existing = self._project.load_translation_result()
            if existing:
                # Count already-translated pages by splitting on double newline
                import re
                parts = re.split(r"\n\n(?=--- Page \d+ ---)", existing)
                translated_parts = list(parts)
                start_page = len(translated_parts)

        self._set_project_status(ProjectStatus.TRANSLATING)
        self._set_processing(True, show_pause=True)

        # Persist settings
        self._project.translation_backend = self._backend_radio.value or "lmstudio"
        self._project.translation_target_language = self._target_language.value or "Portuguese"
        self._project.translation_lmstudio_url = self._lmstudio_url.value or "http://localhost:1234/v1"
        self._project.translation_lmstudio_model = self._lmstudio_model.value or "local-model"
        self._project.save()

        try:
            backend = self._create_translation_backend()
            target_lang = self._project.translation_target_language
            pages = self._ocr_result.pages
            total = len(pages)
            self._project.translation_total_pages = total
            self._project.save()

            for i, page_text in enumerate(pages, 1):
                if i - 1 < start_page:
                    continue  # skip already-translated pages

                # ── Pause point ──────────────────────────────────────
                await self._pause_event.wait()
                if self._cancel_requested:
                    break

                self._set_status(f"Translating page {i}/{total}...")
                self._progress_bar.value = (i - 1) / total
                self.page.update()
                self.page.update()

                page_trans_start = time.perf_counter()
                page_translation: str | None = None
                for attempt in range(3):
                    try:
                        result = await backend.translate(page_text, target_language=target_lang)
                        page_translation = result.translated_text
                        break
                    except Exception as exc:
                        if attempt < 2:
                            wait_time = 2 ** attempt
                            self._set_status(
                                f"Page {i} failed, retrying in {wait_time}s... ({attempt + 1}/3)"
                            )
                            self.page.update()
                            await asyncio.sleep(wait_time)
                        else:
                            logger.warning("Page %d failed: %s", i, exc)
                
                page_trans_duration = time.perf_counter() - page_trans_start
                logger.info("[INFO] Translation page %d/%d took %.2fs", i, total, page_trans_duration)

                if page_translation:
                    translated_parts.append(page_translation)
                else:
                    translated_parts.append(
                        f"[PAGE {i} TRANSLATION FAILED — original text below]\n\n{page_text}"
                    )

                self._translated_text = "\n\n".join(translated_parts)
                self._project.save_translation_result(self._translated_text)
                self._project.translation_completed_pages = len(translated_parts)
                self._project.touch()
                self._project.save()

                self._translation_text_field.value = self._translated_text
                self._translation_char_count.value = f"{len(self._translated_text):,} characters"
                self._btn_save_translation.disabled = False
                self.page.update()

                if i < total:
                    await asyncio.sleep(1)

            if self._cancel_requested:
                return

            self._project.translation_completed_pages = total
            self._set_project_status(ProjectStatus.DONE)
            self._set_status("Done!")
            self._progress_bar.value = 1.0
            self._show_snackbar("Translation complete!")

        except Exception as exc:
            logger.exception("Translation failed")
            self._project.status = ProjectStatus.ERROR
            self._project.error_message = str(exc)
            self._project.save()
            self._show_error(str(exc))
        finally:
            self._set_processing(False, show_pause=False)
            self._refresh_action_buttons()
            self.page.update()

    # ------------------------------------------------------------------
    # Pause / resume
    # ------------------------------------------------------------------

    async def _pause(self) -> None:
        """Signal the running coroutine to pause at the next checkpoint."""
        self._pause_event.clear()  # block the next await _pause_event.wait()
        self._cancel_requested = True  # exit the loop cleanly

        if self._project.status == ProjectStatus.OCR_IN_PROGRESS:
            self._set_project_status(ProjectStatus.OCR_PAUSED)
        elif self._project.status == ProjectStatus.TRANSLATING:
            self._set_project_status(ProjectStatus.TRANSLATION_PAUSED)

        self._set_processing(False, show_pause=False)
        self._refresh_action_buttons()
        self._set_status("Paused. You can resume any time.")
        self.page.update()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_translation_backend(self):
        backend_value = self._project.translation_backend
        backend_type = BackendType(backend_value)
        config = TranslationConfig(
            backend=backend_type,
            lmstudio=LMStudioConfig(
                base_url=self._project.translation_lmstudio_url,
                model=self._project.translation_lmstudio_model,
            ),
            opencode=OpenCodeConfig(),
        )
        return get_backend(config)

    def _set_project_status(self, status: ProjectStatus) -> None:
        self._project.status = status
        self._project.touch()
        self._project.save()

    def _set_processing(self, active: bool, show_pause: bool = False) -> None:
        self._btn_ocr.disabled = active
        self._btn_ocr_translate.disabled = active
        self._progress_bar.visible = active
        self._btn_pause_resume.visible = active and show_pause
        if active:
            self._progress_bar.value = 0
        self.page.update()

    def _set_status(self, msg: str) -> None:
        self._status_text.value = msg
        self.page.update()

    def _show_error(self, msg: str) -> None:
        dialog = ft.AlertDialog(
            title=ft.Text("Error"),
            content=ft.Text(msg),
            actions=[
                ft.FilledButton("OK", on_click=lambda _: self.page.pop_dialog()),
            ],
            modal=True,
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _show_snackbar(self, msg: str) -> None:
        self.page.show_dialog(ft.SnackBar(content=ft.Text(msg)))
        self.page.update()
