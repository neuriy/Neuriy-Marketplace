from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from models import App, AppCreate, AppUpdate
from store import CATEGORIES, ICON_DIR, UPLOAD_DIR, AppStore

store = AppStore()

app = FastAPI(
    title="Neuriy Marketplace API",
    description="Python backend for the Neuriy AI app marketplace.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._")
    return cleaned or "package"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "neuriy-marketplace-api"}


@app.get("/api/categories")
def categories() -> dict:
    return {"categories": CATEGORIES}


@app.get("/api/apps", response_model=list[App])
def list_apps(
    q: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    featured: Optional[bool] = Query(default=None),
    sort: str = Query(default="popular"),
) -> list[App]:
    if sort not in {"popular", "new"}:
        raise HTTPException(status_code=400, detail="sort must be 'popular' or 'new'")
    return store.list_apps(query=q, category=category, featured=featured, sort=sort)


@app.get("/api/apps/{app_id}", response_model=App)
def get_app(app_id: str) -> App:
    found = store.get(app_id)
    if not found:
        raise HTTPException(status_code=404, detail="App not found")
    return found


@app.post("/api/apps", response_model=App, status_code=201)
async def create_app(
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    developer: str = Form("Community"),
    price: str = Form("Free"),
    version: str = Form("1.0.0"),
    featured: bool = Form(False),
    package: UploadFile = File(...),
    icon: Optional[UploadFile] = File(default=None),
) -> App:
    payload = AppCreate(
        name=name,
        description=description,
        category=category,
        developer=developer,
        price=price,
        version=version,
        featured=featured,
    )

    created = store.create(payload)

    package_ext = Path(package.filename or "app.neuriy").suffix.lower() or ".neuriy"
    if len(package_ext) > 20:
        package_ext = ".neuriy"
    package_name = f"{created.id}{package_ext}"
    package_path = UPLOAD_DIR / package_name
    content = await package.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded package is empty")
    package_path.write_bytes(content)
    store.attach_package(created.id, package_name)

    icon_url = None
    if icon is not None and icon.filename:
        icon_ext = Path(icon.filename).suffix.lower() or ".png"
        if icon_ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
            raise HTTPException(status_code=400, detail="Unsupported icon type")
        icon_name = f"{created.id}{icon_ext}"
        icon_path = ICON_DIR / icon_name
        icon_path.write_bytes(await icon.read())
        icon_url = f"/static/icons/{icon_name}"
        store.attach_icon(created.id, icon_url)
    else:
        # Generate a simple fallback icon
        initials = "".join(part[0] for part in created.name.split()[:2]).upper() or "NA"
        icon_name = f"{created.id}.svg"
        icon_path = ICON_DIR / icon_name
        icon_path.write_text(
            f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <rect width="128" height="128" rx="24" fill="#2B6CB0"/>
  <text x="64" y="78" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif"
        font-size="44" font-weight="700" fill="#ffffff">{initials}</text>
</svg>
""",
            encoding="utf-8",
        )
        icon_url = f"/static/icons/{icon_name}"
        store.attach_icon(created.id, icon_url)

    found = store.get(created.id)
    assert found is not None
    return found


@app.patch("/api/apps/{app_id}", response_model=App)
def update_app(app_id: str, payload: AppUpdate) -> App:
    updated = store.update(app_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="App not found")
    return updated


@app.get("/api/apps/{app_id}/download")
def download_app(app_id: str):
    found = store.get(app_id)
    if not found:
        raise HTTPException(status_code=404, detail="App not found")

    path = store.package_path(found)
    if path is None:
        # Provide a temporary placeholder package if none exists
        with tempfile.NamedTemporaryFile(delete=False, suffix=".neuriy") as handle:
            handle.write(
                f"Neuriy AI package\nname={found.name}\nversion={found.version}\nid={found.id}\n".encode(
                    "utf-8"
                )
            )
            temp_path = Path(handle.name)
        store.record_download(app_id)
        return FileResponse(
            path=temp_path,
            filename=f"{_safe_segment(found.name)}-{found.version}.neuriy",
            media_type="application/octet-stream",
        )

    store.record_download(app_id)
    return FileResponse(
        path=path,
        filename=f"{_safe_segment(found.name)}-{found.version}{path.suffix}",
        media_type="application/octet-stream",
    )


@app.post("/api/apps/{app_id}/rate", response_model=App)
def rate_app(app_id: str, rating: float = Form(..., ge=0, le=5)) -> App:
    updated = store.update(app_id, AppUpdate(rating=rating))
    if not updated:
        raise HTTPException(status_code=404, detail="App not found")
    return updated
