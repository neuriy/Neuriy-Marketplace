from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AppCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=1, max_length=4000)
    category: str = Field(..., min_length=1, max_length=80)
    developer: str = Field(default="Community", max_length=120)
    price: str = Field(default="Free", max_length=40)
    version: str = Field(default="1.0.0", max_length=40)
    featured: bool = False


class AppUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, min_length=1, max_length=4000)
    category: Optional[str] = Field(default=None, min_length=1, max_length=80)
    developer: Optional[str] = Field(default=None, min_length=1, max_length=120)
    price: Optional[str] = Field(default=None, max_length=40)
    version: Optional[str] = Field(default=None, max_length=40)
    featured: Optional[bool] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)


class App(BaseModel):
    id: str
    name: str
    description: str
    category: str
    developer: str
    price: str = "Free"
    version: str = "1.0.0"
    rating: float = 0.0
    downloads: int = 0
    featured: bool = False
    icon_url: Optional[str] = None
    package_filename: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new(cls, payload: AppCreate, icon_url: Optional[str] = None) -> "App":
        now = utc_now()
        return cls(
            id=str(uuid4()),
            name=payload.name.strip(),
            description=payload.description.strip(),
            category=payload.category.strip(),
            developer=payload.developer.strip() or "Community",
            price=payload.price.strip() or "Free",
            version=payload.version.strip() or "1.0.0",
            featured=payload.featured,
            icon_url=icon_url,
            created_at=now,
            updated_at=now,
        )
