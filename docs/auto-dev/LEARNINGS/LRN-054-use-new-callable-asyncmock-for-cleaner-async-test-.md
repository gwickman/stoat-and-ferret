## Context

When testing async code that calls other async functions, the standard `unittest.mock.patch()` creates a regular `MagicMock` by default. This requires manually wrapping return values in coroutines or using `AsyncMock` directly, which is verbose and error-prone.

## Learning

Use `new_callable=AsyncMock` in `patch()` calls to automatically create an async-compatible mock. This is cleaner than manually wrapping return values in coroutines and ensures the mock behaves correctly as an awaitable in all cases, including when used as a context manager or iterable.

## Evidence

v010 Feature 001 (fix-blocking-ffprobe) converted `ffprobe_video()` to async and needed to update all test mocks. Using `new_callable=AsyncMock` in `patch()` calls was identified as cleaner than wrapping return values:

```python
# Clean approach (recommended)
with patch("module.ffprobe_video", new_callable=AsyncMock, return_value=metadata):
    result = await scan_directory(path)

# Verbose approach (avoid)
mock = MagicMock()
mock.return_value = asyncio.coroutine(lambda: metadata)()
```

The clean approach worked across all test files (test_videos.py, test_jobs.py, test_ffprobe.py) without issues.

## Application

When patching async functions in tests:
- Always use `new_callable=AsyncMock` in `patch()` calls
- Set `return_value` normally — `AsyncMock` handles the awaitable wrapping
- For `side_effect`, use an async function (`async def`) rather than a sync one
- This pattern works with both `patch()` as a decorator and as a context manager