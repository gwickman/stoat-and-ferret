# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Application settings with environment variable support."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings.

    Settings can be configured via environment variables with STOAT_ prefix,
    a .env file, or direct instantiation.

    Example:
        STOAT_API_PORT=9000 python -m stoat_ferret.api
    """

    model_config = SettingsConfigDict(
        env_prefix="STOAT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_path: str = Field(
        default="data/stoat.db",
        description="Path to SQLite database file",
    )

    # API Server
    api_host: str = Field(
        default="127.0.0.1",
        description="API server host",
    )
    api_port: int = Field(
        default=8765,
        ge=1,
        le=65535,
        description="API server port",
    )

    # Development
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # Storage
    thumbnail_dir: str = Field(
        default="data/thumbnails",
        description="Directory for storing generated thumbnails",
    )

    # Frontend
    gui_static_path: str = Field(
        default="gui/dist",
        description="Path to GUI static files directory",
    )

    # WebSocket
    ws_heartbeat_interval: int = Field(
        default=30,
        ge=1,
        description="WebSocket heartbeat interval in seconds",
    )

    # Logging
    log_backup_count: int = Field(
        default=5,
        ge=0,
        description="Number of rotated log file backups to keep",
    )
    log_max_bytes: int = Field(
        default=10_485_760,
        ge=0,
        description="Maximum log file size in bytes before rotation (default 10MB)",
    )

    # Batch rendering
    batch_parallel_limit: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum number of batch render jobs to execute in parallel",
    )
    batch_max_jobs: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of jobs allowed in a single batch request",
    )

    # Render queue
    render_max_concurrent: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum concurrent render jobs",
    )
    render_max_queue_depth: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum queue depth before rejection",
    )

    # Render service
    render_retry_count: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retry attempts for transient render failures",
    )

    # Render executor
    render_mode: Literal["real", "noop"] = Field(
        default="real",
        description=(
            "Render execution mode (STOAT_RENDER_MODE): 'real' invokes FFmpeg "
            "(default); 'noop' short-circuits the render service for synthetic "
            "load testing without spawning FFmpeg processes."
        ),
    )
    render_timeout_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Render job timeout in seconds",
    )
    render_cancel_grace_seconds: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Grace period for FFmpeg to finalize after cancel",
    )
    render_disk_degraded_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Disk usage ratio that triggers render health degradation (0.0-1.0)",
    )
    render_stuck_threshold_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description=(
            "Seconds before a stale-running render job is transitioned to failed "
            "(STOAT_RENDER_STUCK_THRESHOLD_SECONDS). Default 300s (noop); "
            "production real-mode deployments should increase to 1800s."
        ),
    )

    # Version retention
    version_retention_count: int | None = Field(
        default=None,
        ge=1,
        description="Keep-last-N version retention per project. None retains all versions.",
    )

    # Thumbnail strips
    thumbnail_strip_interval: float = Field(
        default=5.0,
        ge=0.5,
        description="Seconds between frames in thumbnail strip sprite sheets",
    )

    # Waveforms
    waveform_dir: str = Field(
        default="data/waveforms",
        description="Directory for storing generated waveform files",
    )

    # Render storage
    render_output_dir: str = Field(
        default="data/renders",
        description="Directory for storing rendered output files",
    )

    # Proxy storage
    proxy_output_dir: str = Field(
        default="data/proxies",
        description="Directory for storing generated proxy files",
    )
    proxy_max_storage_bytes: int = Field(
        default=10_737_418_240,
        ge=0,
        description="Maximum total storage for proxy files in bytes (default 10 GB)",
    )
    proxy_cleanup_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Storage usage ratio that triggers proxy cleanup (0.0-1.0)",
    )
    proxy_auto_generate: bool = Field(
        default=False,
        description="Automatically queue proxy generation for newly scanned videos",
    )

    # Preview
    preview_output_dir: str = Field(
        default="data/previews",
        description="Directory for storing generated preview files",
    )
    preview_session_ttl_seconds: int = Field(
        default=3600,
        ge=1,
        description="Preview session time-to-live in seconds (default 1 hour)",
    )
    preview_segment_duration: float = Field(
        default=2.0,
        ge=1.0,
        le=6.0,
        description="HLS segment duration in seconds for preview generation",
    )
    preview_cache_max_sessions: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of concurrent preview sessions",
    )
    preview_cache_max_bytes: int = Field(
        default=1_073_741_824,
        ge=0,
        description="Maximum total storage for preview cache in bytes (default 1 GB)",
    )

    # Security
    allowed_scan_roots: list[str] = Field(
        default_factory=list,
        description="Allowed root directories for scanning. Empty list allows all directories.",
    )

    # Migration safety (BL-266)
    migration_backup_dir: str = Field(
        default="data/migration_backups",
        description="Directory for storing pre-migration SQLite backup files.",
    )

    # Feature flags (BL-268)
    testing_mode: bool = Field(
        default=False,
        description="Enable deployment-time testing mode (STOAT_TESTING_MODE).",
    )
    seed_endpoint: bool = Field(
        default=False,
        description="Enable the test seed endpoint (STOAT_SEED_ENDPOINT).",
    )
    synthetic_monitoring: bool = Field(
        default=False,
        description="Enable synthetic monitoring probes (STOAT_SYNTHETIC_MONITORING).",
    )
    synthetic_monitoring_interval_seconds: int = Field(
        default=60,
        ge=1,
        description=(
            "Interval in seconds between synthetic monitoring probe cycles "
            "(STOAT_SYNTHETIC_MONITORING_INTERVAL_SECONDS)."
        ),
    )
    batch_rendering: bool = Field(
        default=True,
        description="Enable batch rendering support (STOAT_BATCH_RENDERING).",
    )
    render_worker_enabled: bool = Field(
        default=True,
        description="Enable the background render worker loop (STOAT_RENDER_WORKER_ENABLED).",
    )

    # Reverse effect buffer limit (BL-444)
    reverse_max_duration_s: float = Field(
        default=30.0,
        gt=0,
        description=(
            "Maximum clip duration in seconds allowed for the reverse effect "
            "(STOAT_REVERSE_MAX_DURATION_S). The FFmpeg reverse/areverse filters buffer "
            "the entire segment in memory; clips exceeding this limit are rejected with "
            "HTTP 422. Default 30.0 s. Must be > 0."
        ),
    )

    # WebSocket replay buffer (BL-313)
    ws_replay_buffer_size: int = Field(
        default=1000,
        ge=0,
        description="Maximum number of messages retained per WebSocket replay buffer.",
    )
    ws_replay_ttl_seconds: int = Field(
        default=300,
        ge=0,
        description="Time-to-live for buffered replay messages in seconds.",
    )

    # Render evidence access (BL-554)
    render_evidence_full_access: bool = Field(
        default=False,
        description=(
            "Enable the full render evidence endpoint (STOAT_RENDER_EVIDENCE_FULL_ACCESS). "
            "When true, GET /render/{job_id}/evidence returns command_args, stderr_tail, "
            "output_path, and filter_script_path. When false (default), the endpoint returns 403."
        ),
    )

    # Asset library (BL-515)
    assets_dir: Path = Field(
        default=Path("working/assets"),
        description=(
            "Directory for storing uploaded asset files (STOAT_ASSETS_DIR). "
            "Created automatically if it does not exist. Relative paths are "
            "resolved from the working directory."
        ),
    )
    assets_max_size_bytes: int = Field(
        default=100 * 1024 * 1024,
        ge=1,
        description=(
            "Maximum upload size in bytes for the asset library "
            "(STOAT_ASSETS_MAX_SIZE_BYTES). Default 104857600 (100 MB)."
        ),
    )

    # AGPL §13 source-offer (BL-525)
    source_url: str = Field(
        default="https://github.com/gwickman/stoat-and-ferret",
        description=(
            "URL of the corresponding source code for AGPL §13 compliance "
            "(STOAT_SOURCE_URL). Operator MUST override per network-served "
            "deployment to point at the actual deployed commit's source."
        ),
    )
    build_commit: str = Field(
        default="unknown",
        description=(
            "Build commit SHA injected by the deploy pipeline (STOAT_BUILD_COMMIT). "
            "Returned verbatim in GET /api/v1/source. If not set, returns 'unknown'."
        ),
    )

    @property
    def database_path_resolved(self) -> Path:
        """Get database path as a Path object.

        Returns:
            The database path as a Path instance.
        """
        return Path(self.database_path)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Application settings instance, cached for performance.
    """
    return Settings()
