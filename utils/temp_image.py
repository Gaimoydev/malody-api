import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Request


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def ensure_temp_dir() -> Path:
    d = _project_root() / "static" / "temp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def media_ext(fmt: str) -> str:
    f = (fmt or "jpeg").lower()
    if f in ("jpeg", "jpg"):
        return "jpg"
    if f == "png":
        return "png"
    return "jpg"


def public_base_url(request: Request) -> str:
    base = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if base:
        return base
    return str(request.base_url).rstrip("/")


def _schedule_delete(path: Path, ttl_seconds: int) -> None:
    async def _run():
        await asyncio.sleep(ttl_seconds)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    asyncio.create_task(_run())


def save_temp_image_url_payload(request: Request, img_bytes: bytes, fmt: str, ttl_seconds: int) -> dict:
    ext = media_ext(fmt)
    name = f"{uuid.uuid4().hex}.{ext}"
    path = ensure_temp_dir() / name
    path.write_bytes(img_bytes)
    _schedule_delete(path, ttl_seconds)
    url = f"{public_base_url(request)}/static/{name}"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    return {
        "url": url,
        "expires_in_seconds": ttl_seconds,
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
    }
