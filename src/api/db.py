from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config import execute, get_connection, rows_as_dicts, using_turso

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS apps (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        developer TEXT NOT NULL,
        price TEXT NOT NULL DEFAULT 'Free',
        version TEXT NOT NULL DEFAULT '1.0.0',
        rating REAL NOT NULL DEFAULT 0,
        downloads INTEGER NOT NULL DEFAULT 0,
        featured INTEGER NOT NULL DEFAULT 0,
        icon_url TEXT,
        package_filename TEXT,
        owner_id TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        moderation_score REAL,
        moderation_notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rules (
        id TEXT PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        severity TEXT NOT NULL,
        pattern TEXT,
        min_description_length INTEGER,
        enabled INTEGER NOT NULL DEFAULT 1,
        is_system INTEGER NOT NULL DEFAULT 0,
        created_by TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rule_checks (
        id TEXT PRIMARY KEY,
        app_id TEXT NOT NULL,
        rule_id TEXT NOT NULL,
        passed INTEGER NOT NULL,
        detail TEXT,
        checked_at TEXT NOT NULL,
        checked_by TEXT NOT NULL
    )
    """,
]


SYSTEM_RULES = [
    {
        "code": "AI_MIN_DESCRIPTION",
        "title": "Meaningful description",
        "description": "Apps must include a clear description of at least 40 characters explaining Neuriy AI value.",
        "severity": "block",
        "pattern": None,
        "min_description_length": 40,
    },
    {
        "code": "AI_NO_SPAM_KEYWORDS",
        "title": "No spam or scam language",
        "description": "Block apps using spam, scam, malware, crack, warez, or phishing language.",
        "severity": "block",
        "pattern": r"\b(spam|scam|malware|crack|warez|phishing|steal\s*data|hack\s*account)\b",
        "min_description_length": None,
    },
    {
        "code": "AI_NO_PLACEHOLDER_NAME",
        "title": "No placeholder app names",
        "description": "Reject generic placeholder names such as test, asdf, untitled, or demo123.",
        "severity": "block",
        "pattern": r"^(test|asdf|foo|bar|untitled|demo\d*|app\d*|temp)$",
        "min_description_length": None,
    },
    {
        "code": "AI_NEURIY_RELEVANCE",
        "title": "Neuriy AI relevance",
        "description": "Prefer apps that mention AI, Neuriy, agent, model, prompt, or related tooling.",
        "severity": "warn",
        "pattern": r"\b(ai|neuriy|agent|model|prompt|llm|assistant|tool)\b",
        "min_description_length": None,
    },
    {
        "code": "AI_SAFE_CATEGORY",
        "title": "Valid marketplace category",
        "description": "Apps must use an approved marketplace category.",
        "severity": "block",
        "pattern": None,
        "min_description_length": None,
    },
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> dict[str, Any]:
    conn = get_connection()
    try:
        for statement in SCHEMA_STATEMENTS:
            execute(conn, statement)
        conn.commit()
        _seed_system_rules(conn)
        _seed_sample_apps_if_empty(conn)
        conn.commit()
        return {
            "ok": True,
            "backend": "turso" if using_turso() else "local-sqlite",
        }
    finally:
        conn.close()


def _seed_system_rules(conn) -> None:
    existing = rows_as_dicts(execute(conn, "SELECT code FROM rules WHERE is_system = 1"))
    existing_codes = {row["code"] for row in existing}
    now = utc_now_iso()
    for rule in SYSTEM_RULES:
        if rule["code"] in existing_codes:
            continue
        from uuid import uuid4

        execute(
            conn,
            """
            INSERT INTO rules (
                id, code, title, description, severity, pattern,
                min_description_length, enabled, is_system, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 'system_ai', ?)
            """,
            (
                str(uuid4()),
                rule["code"],
                rule["title"],
                rule["description"],
                rule["severity"],
                rule["pattern"],
                rule["min_description_length"],
                now,
            ),
        )


def _seed_sample_apps_if_empty(conn) -> None:
    count_rows = rows_as_dicts(execute(conn, "SELECT COUNT(*) AS c FROM apps"))
    count = int(count_rows[0]["c"] if count_rows else 0)
    if count > 0:
        return

    from pathlib import Path
    from uuid import uuid4

    from config import ICON_DIR, UPLOAD_DIR

    samples = [
        ("Neuriy Chat", "Conversational assistant tuned for Neuriy AI workflows and agents.", "Assistants", "Neuriy", True, 4.8, 18240),
        ("Prompt Studio", "Craft, version, and share reusable prompt packs for Neuriy models.", "Productivity", "Neuriy Labs", True, 4.6, 15410),
        ("Vision Desk", "Image understanding toolkit for multimodal Neuriy AI agents.", "Creative", "Pixel Forge", True, 4.5, 12100),
        ("Code Copilot", "Inline coding helper for Neuriy developer environments and tools.", "Developer Tools", "Neuriy", True, 4.9, 21050),
        ("Research Radar", "Scan papers and summarize findings for AI research teams.", "Research", "Atlas AI", False, 4.2, 8300),
        ("Lesson Builder", "Generate structured learning modules with Neuriy AI models.", "Education", "Campus Soft", False, 4.0, 5120),
        ("Workflow Glue", "Connect Neuriy tools into automated AI pipelines.", "Utilities", "Pipewright", False, 4.3, 9740),
        ("Voice Notes", "Transcribe and organize spoken ideas with Neuriy speech AI.", "Productivity", "Echo Works", False, 4.1, 6400),
        ("Style Transfer", "Apply artistic styles to images using Neuriy creative models.", "Creative", "Canvas AI", False, 4.4, 11020),
        ("Dataset Scout", "Discover and prepare datasets for Neuriy fine-tuning jobs.", "Developer Tools", "DataNest", False, 4.7, 14600),
        ("Meeting Scribe", "Capture action items from meetings with Neuriy summarization AI.", "Productivity", "Neuriy", True, 4.5, 9900),
        ("Safe Guard", "Content moderation utilities for Neuriy AI applications.", "Utilities", "Shield Soft", False, 4.2, 7200),
    ]
    colors = [
        "#2B6CB0", "#C05621", "#6B46C1", "#2F855A", "#B83280", "#2C7A7B",
        "#744210", "#1A365D", "#9B2C2C", "#285E61", "#553C9A", "#276749",
    ]
    now = utc_now_iso()
    for index, (name, description, category, developer, featured, rating, downloads) in enumerate(samples):
        app_id = str(uuid4())
        icon_name = f"{app_id}.svg"
        icon_path = ICON_DIR / icon_name
        initials = "".join(part[0] for part in name.split()[:2]).upper()
        icon_path.write_text(
            f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <rect width="128" height="128" rx="24" fill="{colors[index % len(colors)]}"/>
  <text x="64" y="78" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif"
        font-size="44" font-weight="700" fill="#ffffff">{initials}</text>
</svg>
""",
            encoding="utf-8",
        )
        package_name = f"{app_id}.neuriy"
        (UPLOAD_DIR / package_name).write_text(
            f"Neuriy AI package\nname={name}\nversion=1.0.0\n",
            encoding="utf-8",
        )
        execute(
            conn,
            """
            INSERT INTO apps (
                id, name, description, category, developer, price, version,
                rating, downloads, featured, icon_url, package_filename,
                owner_id, status, moderation_score, moderation_notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'Free', '1.0.0', ?, ?, ?, ?, ?, NULL,
                      'approved', 92.0, 'Seeded marketplace sample — approved by system_ai', ?, ?)
            """,
            (
                app_id,
                name,
                description,
                category,
                developer,
                rating,
                downloads,
                1 if featured else 0,
                f"/static/icons/{icon_name}",
                package_name,
                now,
                now,
            ),
        )
