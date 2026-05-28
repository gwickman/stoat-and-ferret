# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v069 (Render & Preview Reliability + Agent Doc Accuracy):** Fixed concurrent StreamReader race in preview subsystem using exclusive ownership and bounded asyncio.wait; added noop-mode serialization and FFmpeg progress reporting to render service; documented render_plan JSON schema and preview lifecycle patterns. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
