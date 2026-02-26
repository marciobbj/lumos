"""Project data model and manager for Lumos OCR sessions.

Each project is stored as a folder under output/<project_name>/ with:
  - project.json   — metadata and state
  - ocr.txt        — OCR result (if available)
  - translation.txt — translation result (if available)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


class ProjectStatus(str, Enum):
    PENDING = "pending"          # created, no processing started
    OCR_IN_PROGRESS = "ocr_in_progress"
    OCR_PAUSED = "ocr_paused"
    OCR_DONE = "ocr_done"
    TRANSLATING = "translating"
    TRANSLATION_PAUSED = "translation_paused"
    DONE = "done"
    ERROR = "error"

    @property
    def label(self) -> str:
        labels = {
            "pending": "Pending",
            "ocr_in_progress": "OCR in progress",
            "ocr_paused": "OCR paused",
            "ocr_done": "OCR done",
            "translating": "Translating",
            "translation_paused": "Translation paused",
            "done": "Done",
            "error": "Error",
        }
        return labels.get(self.value, self.value)

    @property
    def color(self) -> str:
        colors = {
            "pending": "#9E9E9E",
            "ocr_in_progress": "#1976D2",
            "ocr_paused": "#F57C00",
            "ocr_done": "#0288D1",
            "translating": "#7B1FA2",
            "translation_paused": "#F57C00",
            "done": "#388E3C",
            "error": "#D32F2F",
        }
        return colors.get(self.value, "#9E9E9E")

    def can_pause(self) -> bool:
        return self in (
            ProjectStatus.OCR_IN_PROGRESS,
            ProjectStatus.TRANSLATING,
        )

    def can_resume(self) -> bool:
        return self in (
            ProjectStatus.OCR_PAUSED,
            ProjectStatus.TRANSLATION_PAUSED,
        )

    def can_start(self) -> bool:
        return self in (
            ProjectStatus.PENDING,
            ProjectStatus.OCR_DONE,
        )


@dataclass
class Project:
    """A single Lumos project (one PDF scan session)."""

    name: str
    source_pdf: str                    # absolute path to the PDF
    status: ProjectStatus = ProjectStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # OCR progress
    ocr_total_pages: int = 0
    ocr_completed_pages: int = 0
    ocr_language: str = "por+eng"

    # Translation progress
    translation_total_pages: int = 0
    translation_completed_pages: int = 0
    translation_target_language: str = "Portuguese"
    translation_backend: str = "lmstudio"
    translation_lmstudio_url: str = "http://localhost:1234/v1"
    translation_lmstudio_model: str = "local-model"
    translation_opencode_model: str = "github-copilot/gpt-5-mini"


    # Error
    error_message: str = ""

    # Not serialised — set by ProjectManager after load/create
    _output_dir: Path = field(default=OUTPUT_DIR, init=False, repr=False, compare=False)

    # ── Derived ────────────────────────────────────────────────────────────

    @property
    def folder(self) -> Path:
        return self._output_dir / self.name

    @property
    def meta_path(self) -> Path:
        return self.folder / "project.json"

    @property
    def ocr_path(self) -> Path:
        return self.folder / "ocr.txt"

    @property
    def translation_path(self) -> Path:
        return self.folder / "translation.txt"

    @property
    def ocr_pages_dir(self) -> Path:
        """Directory where individual page OCR results are cached."""
        return self.folder / "pages"

    @property
    def ocr_progress_pct(self) -> float:
        if self.ocr_total_pages == 0:
            return 0.0
        return self.ocr_completed_pages / self.ocr_total_pages

    @property
    def translation_progress_pct(self) -> float:
        if self.translation_total_pages == 0:
            return 0.0
        return self.translation_completed_pages / self.translation_total_pages

    @property
    def updated_at_dt(self) -> datetime:
        try:
            return datetime.fromisoformat(self.updated_at)
        except ValueError:
            return datetime.min

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat()


    def save(self) -> None:
        """Persist project metadata to project.json."""
        self.folder.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        data["status"] = self.status.value
        # Remove non-serialisable internal fields
        data.pop("_output_dir", None)
        self.meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Saved project metadata: %s", self.meta_path)

    def save_ocr_page(self, page_index: int, text: str) -> None:
        """Save a single OCR page result to disk."""
        self.ocr_pages_dir.mkdir(parents=True, exist_ok=True)
        page_path = self.ocr_pages_dir / f"page_{page_index:04d}.txt"
        page_path.write_text(text, encoding="utf-8")

    def load_ocr_pages(self) -> list[str]:
        """Load all cached OCR page results, sorted by page index."""
        if not self.ocr_pages_dir.exists():
            return []
        pages = sorted(self.ocr_pages_dir.glob("page_*.txt"))
        return [p.read_text(encoding="utf-8") for p in pages]

    @property
    def translation_pages_dir(self) -> Path:
        """Directory where individual page translation results are cached."""
        return self.folder / "translation_pages"

    def save_translation_page(self, page_index: int, text: str) -> None:
        """Save a single translated page result to disk."""
        self.translation_pages_dir.mkdir(parents=True, exist_ok=True)
        page_path = self.translation_pages_dir / f"page_{page_index:04d}.txt"
        page_path.write_text(text, encoding="utf-8")

    def load_translation_pages(self) -> list[str]:
        """Load all cached translation page results, sorted by page index."""
        if not self.translation_pages_dir.exists():
            return []
        pages = sorted(self.translation_pages_dir.glob("page_*.txt"))
        return [p.read_text(encoding="utf-8") for p in pages]

    def save_ocr_result(self, text: str) -> None:
        """Save full OCR result text."""
        self.ocr_path.write_text(text, encoding="utf-8")

    def load_ocr_result(self) -> Optional[str]:
        """Load OCR result text if it exists."""
        if self.ocr_path.exists():
            return self.ocr_path.read_text(encoding="utf-8")
        return None

    def save_translation_result(self, text: str) -> None:
        """Save full translation result text."""
        self.translation_path.write_text(text, encoding="utf-8")

    def load_translation_result(self) -> Optional[str]:
        """Load translation result text if it exists."""
        if self.translation_path.exists():
            return self.translation_path.read_text(encoding="utf-8")
        return None

    @classmethod
    def load(cls, folder: Path) -> "Project":
        """Load a project from its folder."""
        meta_path = folder / "project.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"No project.json found in {folder}")
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        data["status"] = ProjectStatus(data["status"])
        project = cls(**data)
        project._output_dir = folder.parent  # inject correct output dir
        return project


class ProjectManager:
    """Manages all Lumos projects stored in the output directory."""

    def __init__(self, output_dir: Path = OUTPUT_DIR) -> None:
        self.output_dir = output_dir

    def list_projects(self) -> list[Project]:
        """Return all projects sorted by most recently updated."""
        projects: list[Project] = []
        if not self.output_dir.exists():
            return projects
        for folder in self.output_dir.iterdir():
            if folder.is_dir() and (folder / "project.json").exists():
                try:
                    p = Project.load(folder)
                    p._output_dir = self.output_dir
                    projects.append(p)
                except Exception as exc:
                    logger.warning("Could not load project from %s: %s", folder, exc)
        projects.sort(key=lambda p: p.updated_at_dt, reverse=True)
        return projects

    def create_project(self, name: str, source_pdf: str) -> Project:
        """Create and persist a new project."""
        # Sanitise the name for use as a directory name
        safe_name = self._sanitise_name(name)
        project = Project(name=safe_name, source_pdf=source_pdf)
        project._output_dir = self.output_dir
        project.save()
        return project

    def delete_project(self, project: Project) -> None:
        """Delete a project and all its files."""
        import shutil
        if project.folder.exists():
            shutil.rmtree(project.folder)

    def project_name_exists(self, name: str) -> bool:
        safe = self._sanitise_name(name)
        return (self.output_dir / safe).exists()

    @staticmethod
    def _sanitise_name(name: str) -> str:
        """Convert a display name to a safe directory name."""
        import re
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name.strip())
        safe = re.sub(r"\s+", "_", safe)
        safe = safe.strip("._")
        return safe or "project"
