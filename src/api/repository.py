from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from config import CATEGORIES, ICON_DIR, UPLOAD_DIR, execute, get_connection, rows_as_dicts
from db import utc_now_iso
from moderation import evaluate_app_against_rules


def _boolish(value: Any) -> bool:
    return bool(int(value or 0)) if not isinstance(value, bool) else value


def serialize_app(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "category": row["category"],
        "developer": row["developer"],
        "price": row["price"],
        "version": row["version"],
        "rating": float(row.get("rating") or 0),
        "downloads": int(row.get("downloads") or 0),
        "featured": _boolish(row.get("featured")),
        "icon_url": row.get("icon_url"),
        "package_filename": row.get("package_filename"),
        "owner_id": row.get("owner_id"),
        "status": row.get("status") or "pending",
        "moderation_score": float(row["moderation_score"]) if row.get("moderation_score") is not None else None,
        "moderation_notes": row.get("moderation_notes"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


class AppRepository:
    def list_apps(
        self,
        *,
        query: Optional[str] = None,
        category: Optional[str] = None,
        featured: Optional[bool] = None,
        sort: str = "popular",
        status: Optional[str] = "approved",
        include_all_statuses: bool = False,
    ) -> list[dict[str, Any]]:
        conn = get_connection()
        try:
            sql = "SELECT * FROM apps WHERE 1=1"
            params: list[Any] = []
            if not include_all_statuses:
                sql += " AND status = ?"
                params.append(status or "approved")
            if query:
                sql += " AND (lower(name) LIKE ? OR lower(description) LIKE ? OR lower(developer) LIKE ? OR lower(category) LIKE ?)"
                needle = f"%{query.lower().strip()}%"
                params.extend([needle, needle, needle, needle])
            if category and category.lower() not in {"", "all", "all categories"}:
                sql += " AND lower(category) = lower(?)"
                params.append(category)
            if featured is not None:
                sql += " AND featured = ?"
                params.append(1 if featured else 0)
            if sort == "new":
                sql += " ORDER BY created_at DESC"
            else:
                sql += " ORDER BY downloads DESC, rating DESC"
            rows = rows_as_dicts(execute(conn, sql, params))
            return [serialize_app(row) for row in rows]
        finally:
            conn.close()

    def get(self, app_id: str) -> Optional[dict[str, Any]]:
        conn = get_connection()
        try:
            rows = rows_as_dicts(execute(conn, "SELECT * FROM apps WHERE id = ?", (app_id,)))
            return serialize_app(rows[0]) if rows else None
        finally:
            conn.close()

    def create(
        self,
        *,
        name: str,
        description: str,
        category: str,
        developer: str,
        price: str,
        version: str,
        featured: bool,
        owner_id: Optional[str],
        package_bytes: bytes,
        package_ext: str,
        icon_bytes: Optional[bytes] = None,
        icon_ext: Optional[str] = None,
        run_moderation: bool = True,
    ) -> dict[str, Any]:
        app_id = str(uuid4())
        now = utc_now_iso()
        package_name = f"{app_id}{package_ext}"
        (UPLOAD_DIR / package_name).write_bytes(package_bytes)

        if icon_bytes and icon_ext:
            icon_name = f"{app_id}{icon_ext}"
            (ICON_DIR / icon_name).write_bytes(icon_bytes)
            icon_url = f"/static/icons/{icon_name}"
        else:
            initials = "".join(part[0] for part in name.split()[:2]).upper() or "NA"
            icon_name = f"{app_id}.svg"
            (ICON_DIR / icon_name).write_text(
                f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <rect width="128" height="128" rx="24" fill="#2B6CB0"/>
  <text x="64" y="78" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif"
        font-size="44" font-weight="700" fill="#ffffff">{initials}</text>
</svg>
""",
                encoding="utf-8",
            )
            icon_url = f"/static/icons/{icon_name}"

        conn = get_connection()
        try:
            execute(
                conn,
                """
                INSERT INTO apps (
                    id, name, description, category, developer, price, version,
                    rating, downloads, featured, icon_url, package_filename,
                    owner_id, status, moderation_score, moderation_notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, 'pending', NULL, NULL, ?, ?)
                """,
                (
                    app_id,
                    name.strip(),
                    description.strip(),
                    category.strip(),
                    developer.strip() or "Community",
                    price.strip() or "Free",
                    version.strip() or "1.0.0",
                    1 if featured else 0,
                    icon_url,
                    package_name,
                    owner_id,
                    now,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        app = self.get(app_id)
        assert app is not None
        if run_moderation:
            result = evaluate_app_against_rules(app, checked_by="system_ai")
            self.apply_moderation(app_id, result["status"], result["moderation_score"], result["moderation_notes"])
            app = self.get(app_id)
            assert app is not None
            app["moderation"] = result
        return app

    def apply_moderation(self, app_id: str, status: str, score: float, notes: str) -> Optional[dict[str, Any]]:
        conn = get_connection()
        try:
            execute(
                conn,
                """
                UPDATE apps
                SET status = ?, moderation_score = ?, moderation_notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, score, notes, utc_now_iso(), app_id),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get(app_id)

    def set_status(self, app_id: str, status: str, notes: str | None = None) -> Optional[dict[str, Any]]:
        conn = get_connection()
        try:
            if notes is None:
                execute(
                    conn,
                    "UPDATE apps SET status = ?, updated_at = ? WHERE id = ?",
                    (status, utc_now_iso(), app_id),
                )
            else:
                execute(
                    conn,
                    "UPDATE apps SET status = ?, moderation_notes = ?, updated_at = ? WHERE id = ?",
                    (status, notes, utc_now_iso(), app_id),
                )
            conn.commit()
        finally:
            conn.close()
        return self.get(app_id)

    def record_download(self, app_id: str) -> Optional[dict[str, Any]]:
        conn = get_connection()
        try:
            execute(
                conn,
                "UPDATE apps SET downloads = downloads + 1, updated_at = ? WHERE id = ?",
                (utc_now_iso(), app_id),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get(app_id)

    def package_path(self, app: dict[str, Any]) -> Optional[Path]:
        filename = app.get("package_filename")
        if not filename:
            return None
        path = UPLOAD_DIR / filename
        return path if path.exists() else None

    def get_checks(self, app_id: str) -> list[dict[str, Any]]:
        conn = get_connection()
        try:
            return rows_as_dicts(
                execute(
                    conn,
                    """
                    SELECT rc.*, r.code AS rule_code, r.title AS rule_title, r.severity
                    FROM rule_checks rc
                    JOIN rules r ON r.id = rc.rule_id
                    WHERE rc.app_id = ?
                    ORDER BY rc.checked_at DESC
                    """,
                    (app_id,),
                )
            )
        finally:
            conn.close()


repo = AppRepository()
