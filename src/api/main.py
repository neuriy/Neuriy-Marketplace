from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from auth import (
    authenticate_user,
    create_access_token,
    list_users,
    register_user,
    require_admin,
    require_moderator,
    require_user,
    set_user_role,
)
from config import CATEGORIES, using_turso
from db import init_db
from moderation import create_rule, evaluate_app_against_rules, list_rules, set_rule_enabled
from repository import repo

app = FastAPI(
    title="Neuriy Marketplace API",
    description="Turso/libSQL-backed Neuriy AI marketplace with roles and system AI moderation.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=200)
    username: str = Field(..., min_length=3, max_length=40)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    login: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)


class RoleUpdateRequest(BaseModel):
    role: str


class RuleCreateRequest(BaseModel):
    title: str
    description: str
    severity: str = "block"
    pattern: Optional[str] = None
    min_description_length: Optional[int] = None
    code: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str
    notes: Optional[str] = None


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "neuriy-marketplace-api",
        "database": "turso" if using_turso() else "local-sqlite-fallback",
    }


@app.get("/api/categories")
def categories() -> dict:
    return {"categories": CATEGORIES}


@app.post("/api/auth/register")
def auth_register(payload: RegisterRequest) -> dict[str, Any]:
    user = register_user(payload.email, payload.username, payload.password)
    token = create_access_token(user["id"], user["role"])
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.post("/api/auth/login")
def auth_login(payload: LoginRequest) -> dict[str, Any]:
    user = authenticate_user(payload.login, payload.password)
    token = create_access_token(user["id"], user["role"])
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.get("/api/auth/me")
def auth_me(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return user


@app.get("/api/users")
def users_list(user: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    return list_users()


@app.post("/api/users/{user_id}/role")
def users_set_role(
    user_id: str,
    payload: RoleUpdateRequest,
    actor: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return set_user_role(actor, user_id, payload.role)


@app.get("/api/apps")
def list_apps(
    q: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    featured: Optional[bool] = Query(default=None),
    sort: str = Query(default="popular"),
    status: Optional[str] = Query(default="approved"),
) -> list[dict[str, Any]]:
    if sort not in {"popular", "new"}:
        raise HTTPException(status_code=400, detail="sort must be 'popular' or 'new'")
    return repo.list_apps(
        query=q,
        category=category,
        featured=featured,
        sort=sort,
        status=status or "approved",
        include_all_statuses=False,
    )


@app.get("/api/apps/moderation/queue")
def moderation_queue(user: dict[str, Any] = Depends(require_moderator)) -> list[dict[str, Any]]:
    return repo.list_apps(include_all_statuses=True, status=None, sort="new")


@app.get("/api/apps/{app_id}")
def get_app(app_id: str) -> dict[str, Any]:
    found = repo.get(app_id)
    if not found:
        raise HTTPException(status_code=404, detail="App not found")
    if found["status"] != "approved":
        # Still return details so owners/moderators can inspect; MVC can gate download.
        pass
    return found


@app.get("/api/apps/{app_id}/checks")
def get_app_checks(app_id: str, user: dict[str, Any] = Depends(require_moderator)) -> list[dict[str, Any]]:
    if not repo.get(app_id):
        raise HTTPException(status_code=404, detail="App not found")
    return repo.get_checks(app_id)


@app.post("/api/apps", status_code=201)
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
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    package_bytes = await package.read()
    if not package_bytes:
        raise HTTPException(status_code=400, detail="Uploaded package is empty")
    package_ext = Path(package.filename or "app.neuriy").suffix.lower() or ".neuriy"
    if len(package_ext) > 20:
        package_ext = ".neuriy"

    icon_bytes = None
    icon_ext = None
    if icon is not None and icon.filename:
        icon_ext = Path(icon.filename).suffix.lower() or ".png"
        if icon_ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
            raise HTTPException(status_code=400, detail="Unsupported icon type")
        icon_bytes = await icon.read()

    # Only admin can mark featured at upload time.
    featured_flag = featured if user["role"] == "admin" else False

    created = repo.create(
        name=name,
        description=description,
        category=category,
        developer=developer or user["username"],
        price=price,
        version=version,
        featured=featured_flag,
        owner_id=user["id"],
        package_bytes=package_bytes,
        package_ext=package_ext,
        icon_bytes=icon_bytes,
        icon_ext=icon_ext,
        run_moderation=True,
    )
    return created


@app.post("/api/apps/{app_id}/remoderate")
def remoderate_app(app_id: str, user: dict[str, Any] = Depends(require_moderator)) -> dict[str, Any]:
    found = repo.get(app_id)
    if not found:
        raise HTTPException(status_code=404, detail="App not found")
    result = evaluate_app_against_rules(found, checked_by=f"system_ai:{user['id']}")
    updated = repo.apply_moderation(app_id, result["status"], result["moderation_score"], result["moderation_notes"])
    assert updated is not None
    updated["moderation"] = result
    return updated


@app.post("/api/apps/{app_id}/status")
def update_app_status(
    app_id: str,
    payload: StatusUpdateRequest,
    user: dict[str, Any] = Depends(require_moderator),
) -> dict[str, Any]:
    if payload.status not in {"pending", "approved", "blacklisted"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    notes = payload.notes or f"Status set to {payload.status} by {user['role']} {user['username']}"
    updated = repo.set_status(app_id, payload.status, notes)
    if not updated:
        raise HTTPException(status_code=404, detail="App not found")
    return updated


@app.get("/api/apps/{app_id}/download")
def download_app(app_id: str):
    found = repo.get(app_id)
    if not found:
        raise HTTPException(status_code=404, detail="App not found")
    if found["status"] == "blacklisted":
        raise HTTPException(status_code=403, detail="This app is blacklisted by system AI rules")
    if found["status"] != "approved":
        raise HTTPException(status_code=403, detail="App is not approved for download yet")

    path = repo.package_path(found)
    if path is None:
        raise HTTPException(status_code=404, detail="Package file missing")
    repo.record_download(app_id)
    safe_name = "".join(ch if ch.isalnum() or ch in "-._" else "-" for ch in found["name"]).strip("-") or "neuriy-app"
    return FileResponse(
        path=path,
        filename=f"{safe_name}-{found['version']}{path.suffix}",
        media_type="application/octet-stream",
    )


@app.get("/api/rules")
def rules_list(user: dict[str, Any] = Depends(require_moderator)) -> list[dict[str, Any]]:
    return list_rules(enabled_only=False)


@app.post("/api/rules", status_code=201)
def rules_create(payload: RuleCreateRequest, user: dict[str, Any] = Depends(require_moderator)) -> dict[str, Any]:
    try:
        return create_rule(
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
            pattern=payload.pattern,
            min_description_length=payload.min_description_length,
            created_by=user["id"],
            code=payload.code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/rules/{rule_id}/enabled")
def rules_toggle(rule_id: str, enabled: bool = Form(...), user: dict[str, Any] = Depends(require_moderator)) -> dict[str, Any]:
    updated = set_rule_enabled(rule_id, enabled)
    if not updated:
        raise HTTPException(status_code=404, detail="Rule not found")
    return updated
