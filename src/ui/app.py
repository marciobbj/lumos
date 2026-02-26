"""Main Flet application class for OCR + Translation."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import flet as ft

from src.ocr import OCREngine, OCRResult
from src.translation import get_backend, TranslationConfig, BackendType
from src.translation.config import LMStudioConfig, OpenCodeConfig
from src.ui.components import section_header, result_text_area, char_count_label

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


class OCRApp:
    """Complete Flet desktop UI for OCR extraction and translation."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self._selected_file: str | None = None
        self._ocr_result: OCRResult | None = None
        self._translated_text: str | None = None
        self._setup_page()
        self._build_ui()

    # ------------------------------------------------------------------
    # Page setup
    # ------------------------------------------------------------------

    def _setup_page(self) -> None:
        self.page.title = "Lumos"
        self.page.window.width = 900
        self.page.window.height = 700
        self.page.window.min_width = 800
        self.page.window.min_height = 600
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = "#F5F5F5"

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # File picker — Service controls in Flet 0.81 self-register via context.page
        # when instantiated inside the page handler. No need to add to overlay or services.
        self._file_picker = ft.FilePicker()

        # --- File selection row ---
        self._file_label = ft.Text(
            "No file selected", size=13, color="#757575", expand=True
        )
        file_row = ft.Row(
            [
                ft.ElevatedButton(
                    "Select PDF",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=self._on_pick_file,
                ),
                self._file_label,
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        # --- Settings card ---
        self._ocr_language = ft.Dropdown(
            label="OCR Language",
            value="por+eng",
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
            value="lmstudio",
            on_change=self._on_backend_change,
        )

        self._target_language = ft.TextField(
            label="Target Language",
            value="Portuguese",
            width=200,
        )

        self._lmstudio_url = ft.TextField(
            label="LM Studio URL",
            value="http://localhost:1234/v1",
            width=300,
        )
        self._lmstudio_model = ft.TextField(
            label="LM Studio Model",
            value="local-model",
            width=200,
        )
        self._lmstudio_settings = ft.Column(
            [
                ft.Row(
                    [self._lmstudio_url, self._lmstudio_model],
                    spacing=10,
                ),
            ],
            visible=True,  # visible by default since lmstudio is default
        )

        settings_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        section_header("Settings"),
                        ft.Row(
                            [self._ocr_language, self._target_language],
                            spacing=15,
                        ),
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

        # --- Action buttons ---
        self._btn_ocr = ft.ElevatedButton(
            "Extract Text (OCR)",
            icon=ft.Icons.DOCUMENT_SCANNER,
            on_click=self._on_run_ocr,
            bgcolor="#1976D2",
            color="white",
        )
        self._btn_ocr_translate = ft.ElevatedButton(
            "Extract + Translate",
            icon=ft.Icons.TRANSLATE,
            on_click=self._on_run_ocr_translate,
            bgcolor="#388E3C",
            color="white",
        )
        action_row = ft.Row(
            [self._btn_ocr, self._btn_ocr_translate],
            spacing=10,
        )

        # --- Progress section ---
        self._progress_bar = ft.ProgressBar(visible=False, expand=True)
        self._status_text = ft.Text("", size=12, color="#757575")
        progress_section = ft.Column(
            [
                self._progress_bar,
                self._status_text,
            ],
            spacing=5,
        )

        # --- Results: Tabs ---
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

        # --- Save buttons ---
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

        # --- Assemble page ---
        self.page.add(
            ft.Column(
                [
                    # Header
                    ft.Text(
                        "Lumos",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Divider(height=1),
                    file_row,
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

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_pick_file(self, e) -> None:
        """Open file picker and handle selection."""
        result = await self._file_picker.pick_files(
            dialog_title="Select a PDF file",
            allowed_extensions=["pdf"],
            allow_multiple=False,
        )
        if result and len(result) > 0:
            self._selected_file = result[0].path
            self._file_label.value = Path(self._selected_file).name
            self._file_label.color = "#212121"
            self.page.update()

    async def _on_run_ocr(self, e) -> None:
        await self._run_ocr(translate=False)

    async def _on_run_ocr_translate(self, e) -> None:
        await self._run_ocr(translate=True)

    def _on_backend_change(self, e) -> None:
        """Show/hide LM Studio settings based on selected backend."""
        self._lmstudio_settings.visible = (
            self._backend_radio.value == "lmstudio"
        )
        self.page.update()

    async def _on_save_ocr(self, e) -> None:
        """Save OCR text to file."""
        if self._ocr_result:
            path = self._save_text(self._ocr_result.text, "ocr")
            self._show_snackbar(f"OCR text saved to {path.name}")

    async def _on_save_translation(self, e) -> None:
        """Save translation text to file."""
        if self._translated_text:
            path = self._save_text(self._translated_text, "translation")
            self._show_snackbar(f"Translation saved to {path.name}")

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------

    async def _run_ocr(self, translate: bool) -> None:
        """Run OCR (and optionally translation) on the selected PDF."""
        if not self._selected_file:
            self._show_error("Please select a PDF file first.")
            return

        self._set_processing(True)
        self._set_status("Starting OCR...")

        try:
            engine = OCREngine(language=self._ocr_language.value or "por+eng")

            def on_progress(current: int, total: int) -> None:
                self._progress_bar.value = current / total
                self._status_text.value = (
                    f"Processing page {current}/{total}..."
                )
                self.page.update()

            self._ocr_result = await engine.process_pdf(
                self._selected_file,
                progress_callback=on_progress,
            )

            self._ocr_text_field.value = self._ocr_result.text
            self._ocr_char_count.value = (
                f"{self._ocr_result.char_count:,} characters"
            )
            self._btn_save_ocr.disabled = False

            if translate:
                self._set_status("Translating...")
                self._progress_bar.value = None  # indeterminate
                self.page.update()

                backend = self._create_translation_backend()
                target_lang = self._target_language.value or "Portuguese"

                pages = self._ocr_result.pages
                translated_parts: list[str] = []

                for i, page_text in enumerate(pages, 1):
                    self._set_status(f"Translating page {i}/{len(pages)}...")
                    self._progress_bar.value = (i - 1) / len(pages)
                    self.page.update()

                    page_result = await backend.translate(
                        page_text,
                        target_language=target_lang,
                    )
                    translated_parts.append(page_result.translated_text)

                    # Show partial results as they arrive
                    self._translated_text = "\n\n".join(translated_parts)
                    self._translation_text_field.value = self._translated_text
                    self._translation_char_count.value = (
                        f"{len(self._translated_text):,} characters"
                    )
                    self._btn_save_translation.disabled = False
                    self.page.update()

            self._set_status("Done!")
            self._progress_bar.value = 1.0
            self._auto_save_results(translate)
            self._show_snackbar("Processing complete!")

        except Exception as exc:
            logger.exception("Processing failed")
            self._show_error(str(exc))
        finally:
            self._set_processing(False)
            self.page.update()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_translation_backend(self):
        """Build a translation backend from current UI settings."""
        backend_value = self._backend_radio.value or "lmstudio"
        backend_type = BackendType(backend_value)

        config = TranslationConfig(
            backend=backend_type,
            lmstudio=LMStudioConfig(
                base_url=self._lmstudio_url.value or "http://localhost:1234/v1",
                model=self._lmstudio_model.value or "local-model",
            ),
            opencode=OpenCodeConfig(),
        )
        return get_backend(config)

    def _set_processing(self, active: bool) -> None:
        """Toggle processing state: disable buttons, show/hide progress."""
        self._btn_ocr.disabled = active
        self._btn_ocr_translate.disabled = active
        self._progress_bar.visible = active
        if active:
            self._progress_bar.value = 0
        self.page.update()

    def _set_status(self, msg: str) -> None:
        """Update the status text."""
        self._status_text.value = msg
        self.page.update()

    def _show_error(self, msg: str) -> None:
        """Display an error dialog."""
        dialog = ft.AlertDialog(
            title=ft.Text("Error"),
            content=ft.Text(msg),
            actions=[
                ft.ElevatedButton(
                    "OK",
                    on_click=lambda _: self.page.pop_dialog(),
                ),
            ],
            modal=True,
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _show_snackbar(self, msg: str) -> None:
        """Display a brief snackbar notification."""
        self.page.show_dialog(
            ft.SnackBar(content=ft.Text(msg))
        )
        self.page.update()

    def _auto_save_results(self, translated: bool) -> None:
        """Automatically save results to the output directory."""
        if self._ocr_result:
            self._save_text(self._ocr_result.text, "ocr")
        if translated and self._translated_text:
            self._save_text(self._translated_text, "translation")

    def _save_text(self, text: str, suffix: str) -> Path:
        """Save text to output/<pdf_stem>_<suffix>_<timestamp>.txt."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = Path(self._selected_file).stem if self._selected_file else "unknown"
        path = OUTPUT_DIR / f"{pdf_name}_{suffix}_{timestamp}.txt"
        path.write_text(text, encoding="utf-8")
        logger.info("Saved %s to %s", suffix, path)
        return path
