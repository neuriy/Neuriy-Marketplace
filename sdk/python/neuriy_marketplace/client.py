from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional


class MarketplaceError(RuntimeError):
    pass


class MarketplaceClient:
    """HTTP client for Neuriy Marketplace — usable from Neuriy Chat tools."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        store_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("NEURIY_MARKETPLACE_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.store_url = (store_url or os.getenv("NEURIY_MARKETPLACE_STORE_URL") or "http://127.0.0.1:5011").rstrip("/")
        self.token = token or os.getenv("NEURIY_MARKETPLACE_TOKEN")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            filtered = {k: v for k, v in query.items() if v is not None and v != ""}
            if filtered:
                url = f"{url}?{urllib.parse.urlencode(filtered)}"

        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise MarketplaceError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise MarketplaceError(f"Cannot reach marketplace API at {self.base_url}: {exc.reason}") from exc

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def list_categories(self) -> list[str]:
        payload = self._request("GET", "/api/categories")
        return list(payload.get("categories") or [])

    def search_apps(
        self,
        query: Optional[str] = None,
        *,
        category: Optional[str] = None,
        sort: str = "popular",
        featured: Optional[bool] = None,
    ) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "/api/apps",
            query={
                "q": query,
                "category": category,
                "sort": sort,
                "featured": None if featured is None else str(featured).lower(),
            },
        )

    def get_app(self, app_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/apps/{urllib.parse.quote(app_id)}")

    def open_app(self, app_id: str) -> dict[str, Any]:
        """Return a Neuriy Chat open payload with deep links for the selected app."""
        app = self.get_app(app_id)
        details_url = f"{self.store_url}/Apps/Details/{urllib.parse.quote(app_id)}"
        download_url = f"{self.base_url}/api/apps/{urllib.parse.quote(app_id)}/download"
        return {
            "type": "neuriy.marketplace.open_app",
            "app": app,
            "actions": [
                {"label": "Open in Marketplace", "url": details_url},
                {"label": "Download for Neuriy AI", "url": download_url},
            ],
            "chat_card": {
                "title": app.get("name"),
                "subtitle": f"{app.get('developer')} · {app.get('category')} · {app.get('price')}",
                "body": app.get("description"),
                "status": app.get("status"),
                "score": app.get("moderation_score"),
            },
        }
