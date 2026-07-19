# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""User-asset library REST endpoints (BL-515).

Provides upload, list, metadata, download, and soft-delete for user assets.
Business logic (content-sniff, path safety, dedup) lives here following the
asyncio.to_thread pattern for blocking I/O.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from stoat_ferret.api.schemas.assets import AssetListResponse, AssetRead
from stoat_ferret.db.asset_repository import AssetRecord, AsyncSQLiteAssetRepository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])

# Allow-listed Pillow format strings for image kind uploads.
_IMAGE_FORMAT_ALLOWLIST: frozenset[str] = frozenset({"PNG", "JPEG"})

# Map kind → accepted MIME types (v090: image only)
_KIND_MIME_MAP: dict[str, frozenset[str]] = {
    "image": frozenset({"image/png", "image/jpeg", "image/jpg"}),
}

# Shared 404 detail for asset-not-found responses (get/download/delete).
_ASSET_NOT_FOUND_DETAIL = "Asset not found."


def _get_repo(request: Request) -> AsyncSQLiteAssetRepository:
    repo: AsyncSQLiteAssetRepository = request.app.state.asset_repository
    return repo


def _get_settings(request: Request) -> object:
    return request.app.state._settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Blocking helpers (run via asyncio.to_thread)
# ---------------------------------------------------------------------------


def _hash_and_write(data: bytes, dest_path: Path) -> str:
    """Compute SHA-256 of data and write to dest_path.

    Args:
        data: Raw file bytes.
        dest_path: Destination path (parent must exist).

    Returns:
        Hex-encoded SHA-256 digest.
    """
    digest = hashlib.sha256(data).hexdigest()
    dest_path.write_bytes(data)
    return digest


def _validate_image_magic_bytes(data: bytes) -> tuple[str, str]:
    """Validate data as an image via Pillow magic-bytes sniff.

    Args:
        data: Raw uploaded bytes.

    Returns:
        Tuple of (pillow_format, mime_type) for an accepted image.

    Raises:
        ValueError: If the data is not a recognised/allowed image format.
    """
    try:
        from PIL import Image
    except ImportError:
        raise ValueError("Pillow is required for content validation") from None

    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format
    except Exception as exc:
        raise ValueError(f"Cannot identify image format: {exc}") from exc

    if fmt not in _IMAGE_FORMAT_ALLOWLIST:
        raise ValueError(
            f"Image format '{fmt}' is not allowed. Accepted: {sorted(_IMAGE_FORMAT_ALLOWLIST)}"
        )

    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return fmt, mime


def _resolve_safe_path(assets_dir: Path, filename: str) -> Path:
    """Resolve filename under assets_dir and verify no path escape.

    Args:
        assets_dir: Configured root directory.
        filename: Content-hash-derived filename (no user input).

    Returns:
        Resolved absolute path under assets_dir.

    Raises:
        ValueError: If the resolved path escapes assets_dir (should not happen
            with hash-derived names, but enforced as a defence-in-depth guard).
    """
    root = assets_dir.resolve()
    candidate = (root / filename).resolve()
    if not str(candidate).startswith(str(root)):
        raise ValueError(f"Path '{candidate}' escapes assets_dir root '{root}'")
    return candidate


# ---------------------------------------------------------------------------
# Upload helpers (extracted from upload_asset to reduce handler complexity)
# ---------------------------------------------------------------------------


async def _check_dedup(
    repo: AsyncSQLiteAssetRepository, content_hash: str
) -> AssetRead | None:
    """Check for an existing asset with the given content hash.

    Args:
        repo: Asset repository.
        content_hash: SHA-256 hex digest of the uploaded content.

    Returns:
        An `AssetRead` if a dedup hit (active or restored) was found, else None.

    Raises:
        HTTPException: 500 if a soft-deleted match fails to restore.
    """
    existing = await repo.get_by_content_hash(content_hash)
    if existing is None:
        return None

    if existing.deleted_at is None:
        # Active asset with same content already exists — return it
        logger.info(
            "asset.dedup_hit",
            asset_id=existing.id,
            content_hash=content_hash,
        )
        return _to_schema(existing)

    # Soft-deleted asset: restore and return
    restored = await repo.restore(existing.id)
    if restored is None:
        raise HTTPException(status_code=500, detail="Failed to restore asset.")
    logger.info(
        "asset.restored",
        asset_id=restored.id,
        content_hash=content_hash,
    )
    return _to_schema(restored)


def _validate_upload_size(data: bytes, max_bytes: int) -> None:
    """Raise 413 if the uploaded payload exceeds the configured size limit.

    Args:
        data: Raw uploaded bytes.
        max_bytes: Configured STOAT_ASSETS_MAX_SIZE_BYTES limit.

    Raises:
        HTTPException: 413 if `data` exceeds `max_bytes`.
    """
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Upload exceeds maximum allowed size of {max_bytes} bytes.",
        )


async def _sniff_content(
    kind: str, data: bytes, original_filename: str, file: UploadFile
) -> tuple[str, str]:
    """Detect MIME type and extension, validating content for image kind.

    Args:
        kind: Asset kind (e.g. "image", "audio").
        data: Raw uploaded bytes.
        original_filename: Client-supplied filename, used for extension fallback.
        file: The original UploadFile, used for its declared content-type.

    Returns:
        Tuple of (mime_type, ext).

    Raises:
        HTTPException: 415 if image content-sniff validation fails.
    """
    if kind == "image":
        try:
            _fmt, mime_type = await asyncio.to_thread(_validate_image_magic_bytes, data)
        except ValueError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        ext = "png" if _fmt == "PNG" else "jpg"
    else:
        # Non-image kinds: use uploaded content-type (v090 out of scope for magic-bytes)
        mime_type = file.content_type or "application/octet-stream"
        ext = Path(original_filename).suffix.lstrip(".") or "bin"
    return mime_type, ext


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201, response_model=AssetRead)
async def upload_asset(
    request: Request,
    file: UploadFile,
    kind: Literal["image", "audio", "subtitle", "font", "lut"] = Query(default="image"),
) -> AssetRead:
    """Upload an asset file (multipart/form-data).

    - Validates content via Pillow magic-bytes sniff (image kind only in v090).
    - Enforces STOAT_ASSETS_MAX_SIZE_BYTES.
    - Deduplicates by content hash; re-upload of a soft-deleted asset restores it.
    - File is stored under STOAT_ASSETS_DIR as <sha256hex>.<ext>.
    """
    settings = _get_settings(request)
    repo = _get_repo(request)

    max_bytes: int = settings.assets_max_size_bytes  # type: ignore[attr-defined]
    assets_dir: Path = settings.assets_dir  # type: ignore[attr-defined]

    # Read uploaded bytes (bounded by max_size)
    data = await file.read(max_bytes + 1)
    _validate_upload_size(data, max_bytes)

    if len(data) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    original_filename = file.filename or "upload"

    # Content-sniff validation (v090: image kind only)
    mime_type, ext = await _sniff_content(kind, data, original_filename, file)

    # Compute content hash (blocking) — also needed for dedup check before file write
    content_hash = hashlib.sha256(data).hexdigest()

    # Deduplication: check existing record before touching disk
    dedup_hit = await _check_dedup(repo, content_hash)
    if dedup_hit is not None:
        return dedup_hit

    # Ensure assets_dir exists
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Derive safe filename from content hash
    dest_filename = f"{content_hash}.{ext}"

    # Validate path safety (defence-in-depth; hash-derived names should never escape)
    try:
        dest_path = _resolve_safe_path(assets_dir, dest_filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Write file via asyncio.to_thread (NFR-001: non-blocking I/O)
    await asyncio.to_thread(_hash_and_write, data, dest_path)

    asset_id = str(uuid.uuid4())
    now = _now_iso()
    record = AssetRecord(
        id=asset_id,
        original_filename=original_filename,
        content_hash=content_hash,
        mime_type=mime_type,
        kind=kind,
        size_bytes=len(data),
        file_path=str(dest_path),
        deleted_at=None,
        created_at=now,
        updated_at=now,
    )
    saved = await repo.insert(record)
    logger.info(
        "asset.uploaded",
        asset_id=saved.id,
        kind=kind,
        size_bytes=saved.size_bytes,
    )
    return _to_schema(saved)


@router.get("", response_model=AssetListResponse)
async def list_assets(
    request: Request,
    kind: str | None = Query(default=None, description="Filter by asset kind."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    limit: int = Query(default=50, ge=1, le=200, description="Page size."),
) -> AssetListResponse:
    """List active (non-deleted) assets with optional kind filter."""
    repo = _get_repo(request)
    items = await repo.list_assets(kind=kind, tags=None, offset=offset, limit=limit)
    return AssetListResponse(
        items=[_to_schema(a) for a in items],
        offset=offset,
        limit=limit,
        total=len(items),
    )


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: str, request: Request) -> AssetRead:
    """Get asset metadata by UUID. Soft-deleted assets return 404."""
    repo = _get_repo(request)
    record = await repo.get_by_id(asset_id)
    if record is None or record.deleted_at is not None:
        raise HTTPException(status_code=404, detail=_ASSET_NOT_FOUND_DETAIL)
    return _to_schema(record)


@router.get("/{asset_id}/file")
async def download_asset(asset_id: str, request: Request) -> FileResponse:
    """Download the raw file for an asset. Soft-deleted assets return 404."""
    repo = _get_repo(request)
    record = await repo.get_by_id(asset_id)
    if record is None or record.deleted_at is not None:
        raise HTTPException(status_code=404, detail=_ASSET_NOT_FOUND_DETAIL)
    file_path = Path(record.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Asset file not found on disk.")
    return FileResponse(path=file_path, media_type=record.mime_type)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: str, request: Request) -> None:
    """Soft-delete an asset. The physical file is not removed."""
    repo = _get_repo(request)
    record = await repo.get_by_id(asset_id)
    if record is None or record.deleted_at is not None:
        raise HTTPException(status_code=404, detail=_ASSET_NOT_FOUND_DETAIL)
    deleted = await repo.soft_delete(asset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=_ASSET_NOT_FOUND_DETAIL)
    logger.info("asset.deleted", asset_id=asset_id)


# ---------------------------------------------------------------------------
# Schema conversion helper
# ---------------------------------------------------------------------------


def _to_schema(record: AssetRecord) -> AssetRead:
    return AssetRead(
        id=record.id,
        original_filename=record.original_filename,
        content_hash=record.content_hash,
        mime_type=record.mime_type,
        kind=record.kind,  # type: ignore[arg-type]
        size_bytes=record.size_bytes,
        deleted_at=record.deleted_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
