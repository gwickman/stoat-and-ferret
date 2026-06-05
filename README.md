# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v072 (Render Reliability & Data Integrity):** Eliminated cancel/complete TOCTOU race (BL-412); fixed stale WS payload.status (BL-401); added per-job output_path collision prevention (BL-403); fixed proxy failure path with odd-dimension rounding and PROXY_FAILED WS event (BL-406); enabled SQLite foreign key enforcement (BL-413); added partial_file_detected fingerprint on cancel (BL-415); added VIDEO_DELETED/CLIP_DELETED WS events (BL-416); extended smoke test suite with FFmpeg-gated and Python-3.13-gated discharge procedures. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
