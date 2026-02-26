# Frontend Scan Dialog Analysis

## Component: `ScanModal`

**File:** `gui/src/components/ScanModal.tsx` (272 lines)

### Props

```typescript
interface ScanModalProps {
  open: boolean
  onClose: () => void
  onScanComplete: () => void   // triggers library refresh
}
```

Mounted in `LibraryPage.tsx:90-94` with `onScanComplete={refetch}` — the `refetch` function from `useVideos` hook increments a `fetchKey` to trigger re-fetching the video list.

### State Management

```typescript
const [scanStatus, setScanStatus] = useState<ScanStatus>('idle')
// ScanStatus = 'idle' | 'scanning' | 'cancelling' | 'cancelled' | 'complete' | 'error'

const [progress, setProgress] = useState<number | null>(null)
const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
const jobIdRef = useRef<string | null>(null)
```

### Scan Flow

1. **Submit** (line 67): POST to `/api/v1/videos/scan`, receive `job_id`
2. **Poll** (line 90): `setInterval` every 1000ms polling `GET /api/v1/jobs/{job_id}`
3. **Update progress** (line 96): `setProgress(status.progress)`
4. **Check completion** (line 98): Compare `status.status` against known terminal states

### The Bug: Status String Mismatch

```typescript
// Line 12-18: TypeScript interface declares wrong enum value
interface JobStatus {
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  //                               ^^^^^^^^^^
  //  Backend sends "complete", not "completed"
}
```

```typescript
// Line 98: comparison never matches
if (status.status === 'completed') {   // "complete" !== "completed"
    cleanup()
    setScanStatus('complete')
    onScanComplete()                    // never called
}
```

**Result:** The polling loop runs forever. Progress shows 100% but no completion state is reached. Dialog stays in "Scanning..." mode. The close button is disabled because `isScanning` remains true.

### Missing `timeout` Handling

The interface type omits `'timeout'` entirely, and the polling logic has no branch for it (lines 98-109). A timed-out scan leaves the dialog frozen just like the completion mismatch.

### Cleanup

- `cleanup()` (line 34): Clears the polling interval
- `useEffect` on `!open` (line 41): Resets all state when modal closes
- `useEffect` return (line 53): Cleanup on unmount

### UI States

| `scanStatus` | Progress bar | Message | Close button | Cancel button |
|---|---|---|---|---|
| `idle` | hidden | — | enabled | hidden |
| `scanning` | shown | "Scanning... N%" | **disabled** | shown |
| `cancelling` | shown | "Cancelling..." | disabled | disabled |
| `complete` | hidden | green success box | enabled ("Close") | hidden |
| `cancelled` | hidden | yellow cancelled box | enabled ("Close") | hidden |
| `error` | hidden | red error box | enabled | hidden |

### Why the Dialog "Freezes"

When stuck in `scanning` state at 100%:
- Progress bar shows "100%" — looks complete
- Close button is disabled — user cannot dismiss the dialog
- Cancel button is visible but clicking it sends a cancel request for an already-complete job, which returns 409 Conflict
- The only escape is to reload the page

### Integration Points

- **DirectoryBrowser** (`DirectoryBrowser.tsx`): Nested modal for path selection, fetches `GET /api/v1/filesystem/directories`
- **useVideos hook** (`hooks/useVideos.ts`): `refetch()` callback increments `fetchKey` state to trigger re-query of `GET /api/v1/videos`
- **libraryStore** (`stores/libraryStore.ts`): Zustand store managing scan modal open/close state
