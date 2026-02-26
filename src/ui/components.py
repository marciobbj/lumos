from __future__ import annotations

"""Reusable UI components for the OCR + Translation app."""

import flet as ft


def section_header(title: str) -> ft.Text:
    """Create a styled section header."""
    return ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color="#1976D2")


def result_text_area(
    read_only: bool = True,
    min_lines: int = 10,
    max_lines: int = 20,
) -> ft.TextField:
    """Create a multiline text area for displaying results."""
    return ft.TextField(
        multiline=True,
        read_only=read_only,
        min_lines=min_lines,
        max_lines=max_lines,
        expand=True,
        text_size=12,
    )


def action_button(
    text: str,
    icon: ft.Icons | None = None,
    on_click=None,
    primary: bool = True,
) -> ft.ElevatedButton:
    """Create a styled action button."""
    if primary:
        return ft.ElevatedButton(
            content=text,
            icon=icon,
            on_click=on_click,
            bgcolor="#1976D2",
            color="white",
        )
    return ft.OutlinedButton(
        content=text,
        icon=icon,
        on_click=on_click,
    )


def char_count_label(count: int = 0) -> ft.Text:
    """Create a character count label."""
    return ft.Text(
        f"{count:,} characters" if count else "No content",
        size=12,
        color="#757575",
    )
