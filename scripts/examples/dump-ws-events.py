#!/usr/bin/env python3
"""Dump stoat-and-ferret WebSocket events as newline-delimited JSON.

Connects to ``ws://<host>:<port>/ws`` and prints each frame on its own line.
Supports ``--last-event-id`` to send a ``Last-Event-ID`` HTTP header during the
WebSocket handshake — the server then replays buffered frames strictly newer
than that ``event_id`` (subject to the in-memory replay TTL).

Installation (websockets is in the optional ``[examples]`` group):
    uv pip install -e ".[examples]"
    # or: pip install "websockets>=12.0"

Usage:
    python scripts/examples/dump-ws-events.py
    python scripts/examples/dump-ws-events.py --host localhost --port 8765
    python scripts/examples/dump-ws-events.py --last-event-id event-00042

Send ``Ctrl+C`` to exit. Each printed line is a complete JSON object suitable
for piping into ``jq`` (e.g. ``... | jq 'select(.type != "heartbeat")'``).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    sys.stderr.write(
        'Error: the "websockets" library is required.\n'
        '       Install with: uv pip install -e ".[examples]"\n'
        '       or:           pip install "websockets>=12.0"\n'
    )
    sys.exit(1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Print stoat-and-ferret WebSocket events as newline-delimited JSON.",
    )
    parser.add_argument("--host", default="localhost", help="WebSocket host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port (default: 8765)")
    parser.add_argument(
        "--last-event-id",
        default=None,
        help="Send `Last-Event-ID: <id>` header to request replay since this event_id",
    )
    return parser.parse_args(argv)


async def stream_events(host: str, port: int, last_event_id: str | None) -> int:
    """Connect to the server's /ws endpoint and stream events to stdout.

    Returns 0 on graceful close, 1 on connection error.
    """
    url = f"ws://{host}:{port}/ws"
    headers: list[tuple[str, str]] | None = None
    if last_event_id is not None:
        headers = [("Last-Event-ID", last_event_id)]

    # `additional_headers` is the keyword used by websockets >= 13; earlier
    # 12.x releases accept the same headers under `extra_headers`. Try the
    # newer kwarg first and fall back so the script works against the full
    # `websockets>=12.0` dependency floor.
    try:
        connect = websockets.connect(url, additional_headers=headers)
    except TypeError:
        connect = websockets.connect(url, extra_headers=headers)

    try:
        async with connect as ws:
            async for message in ws:
                # Frames are JSON strings; emit verbatim, one per line.
                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="replace")
                sys.stdout.write(message + "\n")
                sys.stdout.flush()
    except ConnectionClosed:
        return 0
    except OSError as err:
        sys.stderr.write(f"connection error: {err}\n")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = parse_args(argv)
    try:
        return asyncio.run(stream_events(args.host, args.port, args.last_event_id))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
