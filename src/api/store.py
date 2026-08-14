from __future__ import annotations

import json
import shutil
from pathlib import Path
from threading import Lock
from typing import Iterable, Optional

from models import App, AppCreate, AppUpdate, utc_now

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "apps.json"
UPLOAD_DIR = BASE_DIR / "uploads"
ICON_DIR = BASE_DIR / "static" / "icons"

CATEGORIES = [
    "All Categories",
    "Assistants",
    "Productivity",
    "Creative",
    "Developer Tools",
    "Research",
    "Education",
    "Utilities",
]


class AppStore:
    def __init__(self) -> None:
        self._lock = Lock()
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        ICON_DIR.mkdir(parents=True, exist_ok=True)
        if not DATA_FILE.exists():
            self._seed()

    def _read(self) -> list[App]:
        with DATA_FILE.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return [App.model_validate(item) for item in raw]

    def _write(self, apps: Iterable[App]) -> None:
        payload = [app.model_dump(mode="json") for app in apps]
        tmp = DATA_FILE.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        tmp.replace(DATA_FILE)

    def list_apps(
        self,
        *,
        query: Optional[str] = None,
        category: Optional[str] = None,
        featured: Optional[bool] = None,
        sort: str = "popular",
    ) -> list[App]:
        with self._lock:
            apps = self._read()

        if query:
            needle = query.lower().strip()
            apps = [
                app
                for app in apps
                if needle in app.name.lower()
                or needle in app.description.lower()
                or needle in app.developer.lower()
                or needle in app.category.lower()
            ]

        if category and category.lower() not in {"", "all", "all categories"}:
            apps = [app for app in apps if app.category.lower() == category.lower()]

        if featured is not None:
            apps = [app for app in apps if app.featured is featured]

        if sort == "new":
            apps.sort(key=lambda app: app.created_at, reverse=True)
        else:
            apps.sort(key=lambda app: (app.downloads, app.rating), reverse=True)

        return apps

    def get(self, app_id: str) -> Optional[App]:
        with self._lock:
            for app in self._read():
                if app.id == app_id:
                    return app
        return None

    def create(self, payload: AppCreate, icon_url: Optional[str] = None) -> App:
        app = App.new(payload, icon_url=icon_url)
        with self._lock:
            apps = self._read()
            apps.append(app)
            self._write(apps)
        return app

    def update(self, app_id: str, payload: AppUpdate) -> Optional[App]:
        with self._lock:
            apps = self._read()
            for index, app in enumerate(apps):
                if app.id != app_id:
                    continue
                data = app.model_dump()
                updates = payload.model_dump(exclude_unset=True)
                data.update(updates)
                data["updated_at"] = utc_now()
                updated = App.model_validate(data)
                apps[index] = updated
                self._write(apps)
                return updated
        return None

    def attach_package(self, app_id: str, filename: str) -> Optional[App]:
        with self._lock:
            apps = self._read()
            for index, app in enumerate(apps):
                if app.id != app_id:
                    continue
                data = app.model_dump()
                data["package_filename"] = filename
                data["updated_at"] = utc_now()
                updated = App.model_validate(data)
                apps[index] = updated
                self._write(apps)
                return updated
        return None

    def attach_icon(self, app_id: str, icon_url: str) -> Optional[App]:
        with self._lock:
            apps = self._read()
            for index, app in enumerate(apps):
                if app.id != app_id:
                    continue
                data = app.model_dump()
                data["icon_url"] = icon_url
                data["updated_at"] = utc_now()
                updated = App.model_validate(data)
                apps[index] = updated
                self._write(apps)
                return updated
        return None

    def record_download(self, app_id: str) -> Optional[App]:
        with self._lock:
            apps = self._read()
            for index, app in enumerate(apps):
                if app.id != app_id:
                    continue
                data = app.model_dump()
                data["downloads"] = int(data.get("downloads", 0)) + 1
                data["updated_at"] = utc_now()
                updated = App.model_validate(data)
                apps[index] = updated
                self._write(apps)
                return updated
        return None

    def package_path(self, app: App) -> Optional[Path]:
        if not app.package_filename:
            return None
        path = UPLOAD_DIR / app.package_filename
        return path if path.exists() else None

    def _seed(self) -> None:
        samples = [
            AppCreate(
                name="Neuriy Chat",
                description="Conversational assistant tuned for Neuriy AI workflows.",
                category="Assistants",
                developer="Neuriy",
                featured=True,
                version="2.1.0",
            ),
            AppCreate(
                name="Prompt Studio",
                description="Craft, version, and share reusable prompt packs.",
                category="Productivity",
                developer="Neuriy Labs",
                featured=True,
                version="1.4.2",
            ),
            AppCreate(
                name="Vision Desk",
                description="Image understanding toolkit for multimodal Neuriy agents.",
                category="Creative",
                developer="Pixel Forge",
                featured=True,
                version="1.0.8",
            ),
            AppCreate(
                name="Code Copilot",
                description="Inline coding helper for Neuriy developer environments.",
                category="Developer Tools",
                developer="Neuriy",
                featured=True,
                version="3.0.1",
            ),
            AppCreate(
                name="Research Radar",
                description="Scan papers and summarize findings for AI research teams.",
                category="Research",
                developer="Atlas AI",
                featured=False,
                version="1.2.0",
            ),
            AppCreate(
                name="Lesson Builder",
                description="Generate structured learning modules with Neuriy models.",
                category="Education",
                developer="Campus Soft",
                featured=False,
                version="0.9.5",
            ),
            AppCreate(
                name="Workflow Glue",
                description="Connect Neuriy tools into automated pipelines.",
                category="Utilities",
                developer="Pipewright",
                featured=False,
                version="1.1.3",
            ),
            AppCreate(
                name="Voice Notes",
                description="Transcribe and organize spoken ideas with Neuriy speech.",
                category="Productivity",
                developer="Echo Works",
                featured=False,
                version="1.0.0",
            ),
            AppCreate(
                name="Style Transfer",
                description="Apply artistic styles to images using Neuriy creative models.",
                category="Creative",
                developer="Canvas AI",
                featured=False,
                version="2.0.0",
            ),
            AppCreate(
                name="Dataset Scout",
                description="Discover and prepare datasets for Neuriy fine-tuning jobs.",
                category="Developer Tools",
                developer="DataNest",
                featured=False,
                version="1.3.4",
            ),
            AppCreate(
                name="Meeting Scribe",
                description="Capture action items from meetings with Neuriy summarization.",
                category="Productivity",
                developer="Neuriy",
                featured=True,
                version="1.6.0",
            ),
            AppCreate(
                name="Safe Guard",
                description="Content moderation utilities for Neuriy applications.",
                category="Utilities",
                developer="Shield Soft",
                featured=False,
                version="1.0.2",
            ),
        ]

        ratings = [4.8, 4.6, 4.5, 4.9, 4.2, 4.0, 4.3, 4.1, 4.4, 4.7, 4.5, 4.2]
        downloads = [18240, 15410, 12100, 21050, 8300, 5120, 9740, 6400, 11020, 14600, 9900, 7200]
        colors = [
            "#2B6CB0",
            "#C05621",
            "#6B46C1",
            "#2F855A",
            "#B83280",
            "#2C7A7B",
            "#744210",
            "#1A365D",
            "#9B2C2C",
            "#285E61",
            "#553C9A",
            "#276749",
        ]

        apps: list[App] = []
        for index, payload in enumerate(samples):
            app = App.new(payload)
            icon_name = f"{app.id}.svg"
            icon_path = ICON_DIR / icon_name
            self._write_icon(icon_path, payload.name, colors[index % len(colors)])
            data = app.model_dump()
            data["icon_url"] = f"/static/icons/{icon_name}"
            data["rating"] = ratings[index]
            data["downloads"] = downloads[index]
            package_name = f"{app.id}.neuriy"
            package_path = UPLOAD_DIR / package_name
            package_path.write_text(
                f"Neuriy AI package\nname={payload.name}\nversion={payload.version}\n",
                encoding="utf-8",
            )
            data["package_filename"] = package_name
            apps.append(App.model_validate(data))

        self._write(apps)

    @staticmethod
    def _write_icon(path: Path, name: str, color: str) -> None:
        initials = "".join(part[0] for part in name.split()[:2]).upper()
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <rect width="128" height="128" rx="24" fill="{color}"/>
  <text x="64" y="78" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif"
        font-size="44" font-weight="700" fill="#ffffff">{initials}</text>
</svg>
"""
        path.write_text(svg, encoding="utf-8")


def clear_upload_artifact(path: Path) -> None:
    if path.exists() and path.is_file():
        path.unlink()


def copy_upload(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
