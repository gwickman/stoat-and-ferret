import { useState } from 'react'
import SearchBar from '../components/SearchBar'
import SortControls from '../components/SortControls'
import VideoGrid from '../components/VideoGrid'
import ScanModal from '../components/ScanModal'
import { useDebounce } from '../hooks/useDebounce'
import { useVideos } from '../hooks/useVideos'
import { useLibraryStore } from '../stores/libraryStore'

export default function LibraryPage() {
  const {
    searchQuery,
    sortField,
    sortOrder,
    page,
    pageSize,
    setSearchQuery,
    setSortField,
    setSortOrder,
    setPage,
  } = useLibraryStore()

  const debouncedQuery = useDebounce(searchQuery, 300)
  const { videos, total, loading, error, refetch } = useVideos({
    searchQuery: debouncedQuery,
    sortField,
    sortOrder,
    page,
    pageSize,
  })

  const [scanOpen, setScanOpen] = useState(false)

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div className="p-6" data-testid="library-page">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Library</h2>
        <button
          onClick={() => setScanOpen(true)}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          data-testid="scan-button"
        >
          Scan Directory
        </button>
      </div>

      <div className="mb-4 flex items-center gap-4">
        <div className="flex-1">
          <SearchBar value={searchQuery} onChange={setSearchQuery} />
        </div>
        <SortControls
          sortField={sortField}
          sortOrder={sortOrder}
          onSortFieldChange={setSortField}
          onSortOrderChange={setSortOrder}
        />
      </div>

      <VideoGrid videos={videos} loading={loading} error={error} />

      {!loading && !error && total > pageSize && (
        <div
          className="mt-4 flex items-center justify-center gap-2"
          data-testid="pagination"
        >
          <button
            onClick={() => setPage(page - 1)}
            disabled={page === 0}
            className="rounded border border-gray-700 px-3 py-1 text-sm text-gray-300 hover:bg-gray-800 disabled:opacity-50"
            data-testid="page-prev"
          >
            Previous
          </button>
          <span className="text-sm text-gray-400" data-testid="page-info">
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page >= totalPages - 1}
            className="rounded border border-gray-700 px-3 py-1 text-sm text-gray-300 hover:bg-gray-800 disabled:opacity-50"
            data-testid="page-next"
          >
            Next
          </button>
        </div>
      )}

      <ScanModal
        open={scanOpen}
        onClose={() => setScanOpen(false)}
        onScanComplete={refetch}
      />
    </div>
  )
}
