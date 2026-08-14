from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from config import AI_QUALITY_THRESHOLD, CATEGORIES, execute, get_connection, rows_as_dicts
from db import utc_now_iso


def list_rules(enabled_only: bool = False) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        sql = "SELECT * FROM rules"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY is_system DESC, created_at ASC"
        return rows_as_dicts(execute(conn, sql))
    finally:
        conn.close()


def create_rule(
    *,
    title: str,
    description: str,
    severity: str,
    pattern: str | None,
    min_description_length: int | None,
    created_by: str,
    code: str | None = None,
) -> dict[str, Any]:
    if severity not in {"warn", "block"}:
        raise ValueError("severity must be warn or block")
    rule_id = str(uuid4())
    code_value = (code or f"CUSTOM_{rule_id[:8]}").upper().replace(" ", "_")
    now = utc_now_iso()
    conn = get_connection()
    try:
        execute(
            conn,
            """
            INSERT INTO rules (
                id, code, title, description, severity, pattern,
                min_description_length, enabled, is_system, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?)
            """,
            (
                rule_id,
                code_value,
                title.strip(),
                description.strip(),
                severity,
                pattern,
                min_description_length,
                created_by,
                now,
            ),
        )
        conn.commit()
        rows = rows_as_dicts(execute(conn, "SELECT * FROM rules WHERE id = ?", (rule_id,)))
        return rows[0]
    finally:
        conn.close()


def set_rule_enabled(rule_id: str, enabled: bool) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        execute(conn, "UPDATE rules SET enabled = ? WHERE id = ?", (1 if enabled else 0, rule_id))
        conn.commit()
        rows = rows_as_dicts(execute(conn, "SELECT * FROM rules WHERE id = ?", (rule_id,)))
        return rows[0] if rows else None
    finally:
        conn.close()


def evaluate_app_against_rules(app: dict[str, Any], checked_by: str = "system_ai") -> dict[str, Any]:
    """System AI rule engine: score quality and blacklist apps that fail standards."""
    rules = list_rules(enabled_only=True)
    checks: list[dict[str, Any]] = []
    score = 100.0
    block_failures: list[str] = []
    warn_failures: list[str] = []

    name = (app.get("name") or "").strip()
    description = (app.get("description") or "").strip()
    category = (app.get("category") or "").strip()
    haystack = f"{name}\n{description}".lower()

    for rule in rules:
        passed = True
        detail = "Passed"

        if rule["code"] == "AI_SAFE_CATEGORY":
            allowed = {c for c in CATEGORIES if c != "All Categories"}
            passed = category in allowed
            detail = "Valid category" if passed else f"Invalid category: {category}"
        elif rule.get("min_description_length"):
            minimum = int(rule["min_description_length"])
            passed = len(description) >= minimum
            detail = f"Description length {len(description)} (min {minimum})"
        elif rule.get("pattern"):
            pattern = rule["pattern"]
            match = re.search(pattern, haystack if rule["code"] != "AI_NO_PLACEHOLDER_NAME" else name.lower(), re.I)
            if rule["code"] == "AI_NEURIY_RELEVANCE":
                # Positive pattern: must match
                passed = match is not None
                detail = "Mentions Neuriy/AI concepts" if passed else "Missing Neuriy/AI relevance signals"
            elif rule["code"] == "AI_NO_PLACEHOLDER_NAME":
                passed = match is None
                detail = "Name looks real" if passed else "Placeholder/generic name rejected"
            else:
                # Negative pattern: must NOT match
                passed = match is None
                detail = "No forbidden language" if passed else f"Matched forbidden pattern: {pattern}"

        if not passed:
            if rule["severity"] == "block":
                score -= 35
                block_failures.append(rule["title"])
            else:
                score -= 12
                warn_failures.append(rule["title"])

        check = {
            "id": str(uuid4()),
            "app_id": app["id"],
            "rule_id": rule["id"],
            "passed": 1 if passed else 0,
            "detail": detail,
            "checked_at": utc_now_iso(),
            "checked_by": checked_by,
            "rule_code": rule["code"],
            "rule_title": rule["title"],
            "severity": rule["severity"],
        }
        checks.append(check)

    # Extra system AI heuristics for overall quality.
    if len(name) < 3:
        score -= 20
        block_failures.append("Name too short")
    if len(set(description.lower().split())) < 6:
        score -= 15
        warn_failures.append("Description too thin")

    score = max(0.0, min(100.0, score))
    blacklisted = bool(block_failures) or score < AI_QUALITY_THRESHOLD
    status = "blacklisted" if blacklisted else "approved"
    notes_parts = [
        f"system_ai score={score:.1f} (threshold={AI_QUALITY_THRESHOLD})",
    ]
    if block_failures:
        notes_parts.append("blocked: " + "; ".join(block_failures))
    if warn_failures:
        notes_parts.append("warnings: " + "; ".join(warn_failures))
    if not blacklisted:
        notes_parts.append("meets Neuriy marketplace standards")

    # Persist checks
    conn = get_connection()
    try:
        execute(conn, "DELETE FROM rule_checks WHERE app_id = ?", (app["id"],))
        for check in checks:
            execute(
                conn,
                """
                INSERT INTO rule_checks (id, app_id, rule_id, passed, detail, checked_at, checked_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    check["id"],
                    check["app_id"],
                    check["rule_id"],
                    check["passed"],
                    check["detail"],
                    check["checked_at"],
                    check["checked_by"],
                ),
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "status": status,
        "moderation_score": score,
        "moderation_notes": " | ".join(notes_parts),
        "checks": checks,
        "blacklisted": blacklisted,
    }
