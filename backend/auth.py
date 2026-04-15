import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import ApiKey


def generate_api_key() -> str:
    return "ptr_" + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass
class AnonymousKey:
    permissions: List[str] = field(default_factory=lambda: ["read", "write", "admin"])
    namespace: str = "default"
    name: str = "anonymous"
    is_active: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    key_hash: str = ""
    last_used: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


async def get_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[ApiKey]:
    header_key = request.headers.get("X-API-Key")

    if not header_key:
        if not settings.REQUIRE_API_KEY:
            return AnonymousKey()
        raise HTTPException(status_code=401, detail="Valid API key required")

    key_hash = hash_api_key(header_key)

    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        # A key was explicitly provided but is invalid/revoked — always reject.
        # Silently falling back to anonymous would grant admin access on bad keys.
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(last_used=datetime.utcnow())
    )
    await db.commit()
    await db.refresh(api_key)

    return api_key


async def require_read(api_key: ApiKey = Depends(get_api_key)) -> ApiKey:
    if "read" not in api_key.permissions and "admin" not in api_key.permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    return api_key


async def require_write(api_key: ApiKey = Depends(get_api_key)) -> ApiKey:
    if "write" not in api_key.permissions and "admin" not in api_key.permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    return api_key


async def require_admin(api_key: ApiKey = Depends(get_api_key)) -> ApiKey:
    if "admin" not in api_key.permissions:
        raise HTTPException(status_code=403, detail="Admin permission required")
    return api_key
