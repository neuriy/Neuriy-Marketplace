from __future__ import annotations

from typing import Any, Optional

from .client import MarketplaceClient


def chat_tools() -> list[dict[str, Any]]:
    """OpenAI / Neuriy Chat compatible tool schemas."""
    return [
        {
            "type": "function",
            "function": {
                "name": "marketplace_search",
                "description": "Search Neuriy Marketplace for AI apps and tools.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search text"},
                        "category": {"type": "string", "description": "Optional category filter"},
                        "sort": {"type": "string", "enum": ["popular", "new"], "default": "popular"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "marketplace_get_app",
                "description": "Get details for one marketplace app by id.",
                "parameters": {
                    "type": "object",
                    "properties": {"app_id": {"type": "string"}},
                    "required": ["app_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "marketplace_list_categories",
                "description": "List Neuriy Marketplace categories.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "marketplace_open_app",
                "description": "Open a marketplace app inside Neuriy Chat (returns deep links and a chat card).",
                "parameters": {
                    "type": "object",
                    "properties": {"app_id": {"type": "string"}},
                    "required": ["app_id"],
                },
            },
        },
    ]


def execute_tool(
    name: str,
    arguments: Optional[dict[str, Any]] = None,
    *,
    client: Optional[MarketplaceClient] = None,
) -> Any:
    """Dispatch a Neuriy Chat tool call to the marketplace client."""
    client = client or MarketplaceClient()
    args = arguments or {}

    if name == "marketplace_search":
        return client.search_apps(
            args.get("query"),
            category=args.get("category"),
            sort=args.get("sort") or "popular",
        )
    if name == "marketplace_get_app":
        return client.get_app(args["app_id"])
    if name == "marketplace_list_categories":
        return client.list_categories()
    if name == "marketplace_open_app":
        return client.open_app(args["app_id"])
    raise ValueError(f"Unknown marketplace tool: {name}")
