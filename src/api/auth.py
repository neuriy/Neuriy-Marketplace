from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import JWT_ALGORITHM, JWT_EXPIRE_HOURS, JWT_SECRET, ROLES, execute, get_connection, rows_as_dicts
from db import utc_now_iso

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def user_count() -> int:
    conn = get_connection()
    try:
        rows = rows_as_dicts(execute(conn, "SELECT COUNT(*) AS c FROM users"))
        return int(rows[0]["c"] if rows else 0)
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> Optional[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = rows_as_dicts(execute(conn, "SELECT * FROM users WHERE id = ?", (user_id,)))
        return rows[0] if rows else None
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = rows_as_dicts(
            execute(conn, "SELECT * FROM users WHERE lower(email) = lower(?)", (email.strip(),))
        )
        return rows[0] if rows else None
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = rows_as_dicts(
            execute(conn, "SELECT * FROM users WHERE lower(username) = lower(?)", (username.strip(),))
        )
        return rows[0] if rows else None
    finally:
        conn.close()


def register_user(email: str, username: str, password: str) -> dict[str, Any]:
    email = email.strip().lower()
    username = username.strip()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if get_user_by_username(username):
        raise HTTPException(status_code=400, detail="Username already taken")

    # First account becomes admin; later accounts are regular users.
    role = "admin" if user_count() == 0 else "user"
    user = {
        "id": str(uuid4()),
        "email": email,
        "username": username,
        "password_hash": hash_password(password),
        "role": role,
        "created_at": utc_now_iso(),
    }
    conn = get_connection()
    try:
        execute(
            conn,
            """
            INSERT INTO users (id, email, username, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user["id"], user["email"], user["username"], user["password_hash"], user["role"], user["created_at"]),
        )
        conn.commit()
    finally:
        conn.close()
    return public_user(user)


def authenticate_user(email_or_username: str, password: str) -> dict[str, Any]:
    needle = email_or_username.strip()
    user = get_user_by_email(needle) or get_user_by_username(needle)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return public_user(user)


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


def set_user_role(actor: dict[str, Any], target_user_id: str, role: str) -> dict[str, Any]:
    if role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of {', '.join(ROLES)}")
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can assign roles")
    target = get_user_by_id(target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    conn = get_connection()
    try:
        execute(conn, "UPDATE users SET role = ? WHERE id = ?", (role, target_user_id))
        conn.commit()
    finally:
        conn.close()
    target["role"] = role
    return public_user(target)


def list_users() -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = rows_as_dicts(execute(conn, "SELECT * FROM users ORDER BY created_at ASC"))
        return [public_user(row) for row in rows]
    finally:
        conn.close()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> Optional[dict[str, Any]]:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = get_user_by_id(user_id)
        return public_user(user) if user else None
    except JWTError:
        return None


async def require_user(user: Optional[dict[str, Any]] = Depends(get_current_user)) -> dict[str, Any]:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


async def require_admin(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


async def require_moderator(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    # Admin or administrator may check / enforce rules.
    if user["role"] not in {"admin", "administrator"}:
        raise HTTPException(status_code=403, detail="Administrator or admin role required")
    return user
