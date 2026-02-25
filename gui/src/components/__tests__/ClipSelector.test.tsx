import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ClipSelector from '../ClipSelector'
import type { Clip } from '../../hooks/useProjects'

const mockClips: Clip[] = [
  {
    id: 'clip-1',
    project_id: 'proj-1',
    source_video_id: 'video-1',
    in_point: 0,
    out_point: 100,
    timeline_position: 0,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'clip-2',
    project_id: 'proj-1',
    source_video_id: 'video-2',
    in_point: 50,
    out_point: 200,
    timeline_position: 100,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
]

describe('ClipSelector', () => {
  it('renders clips with name and timeline position', () => {
    const onSelect = vi.fn()
    render(<ClipSelector clips={mockClips} selectedClipId={null} onSelect={onSelect} />)

    expect(screen.getByTestId('clip-selector')).toBeDefined()
    expect(screen.getByTestId('clip-option-clip-1')).toBeDefined()
    expect(screen.getByTestId('clip-option-clip-2')).toBeDefined()

    // Check that source_video_id is displayed
    expect(screen.getByText('video-1')).toBeDefined()
    expect(screen.getByText('video-2')).toBeDefined()
  })

  it('calls onSelect when a clip is clicked', () => {
    const onSelect = vi.fn()
    render(<ClipSelector clips={mockClips} selectedClipId={null} onSelect={onSelect} />)

    fireEvent.click(screen.getByTestId('clip-option-clip-2'))
    expect(onSelect).toHaveBeenCalledWith('clip-2')
  })

  it('highlights selected clip', () => {
    const onSelect = vi.fn()
    render(<ClipSelector clips={mockClips} selectedClipId="clip-1" onSelect={onSelect} />)

    const selected = screen.getByTestId('clip-option-clip-1')
    expect(selected.className).toContain('border-blue-500')
  })

  it('shows empty message when no clips', () => {
    const onSelect = vi.fn()
    render(<ClipSelector clips={[]} selectedClipId={null} onSelect={onSelect} />)

    expect(screen.getByTestId('clip-selector-empty')).toBeDefined()
    expect(screen.getByText('No clips in this project. Add clips to get started.')).toBeDefined()
  })
})

describe('ClipSelector pair-mode', () => {
  it('renders "Select Clip Pair" heading in pair-mode', () => {
    const onSelect = vi.fn()
    const onSelectPair = vi.fn()
    render(
      <ClipSelector
        clips={mockClips}
        selectedClipId={null}
        onSelect={onSelect}
        pairMode
        selectedFromId={null}
        selectedToId={null}
        onSelectPair={onSelectPair}
      />,
    )

    expect(screen.getByText('Select Clip Pair')).toBeDefined()
  })

  it('selects first clip as "from" when no source selected', () => {
    const onSelect = vi.fn()
    const onSelectPair = vi.fn()
    render(
      <ClipSelector
        clips={mockClips}
        selectedClipId={null}
        onSelect={onSelect}
        pairMode
        selectedFromId={null}
        selectedToId={null}
        onSelectPair={onSelectPair}
      />,
    )

    fireEvent.click(screen.getByTestId('clip-option-clip-1'))
    expect(onSelectPair).toHaveBeenCalledWith('clip-1', 'from')
  })

  it('selects second clip as "to" when source already selected', () => {
    const onSelect = vi.fn()
    const onSelectPair = vi.fn()
    render(
      <ClipSelector
        clips={mockClips}
        selectedClipId={null}
        onSelect={onSelect}
        pairMode
        selectedFromId="clip-1"
        selectedToId={null}
        onSelectPair={onSelectPair}
      />,
    )

    fireEvent.click(screen.getByTestId('clip-option-clip-2'))
    expect(onSelectPair).toHaveBeenCalledWith('clip-2', 'to')
  })

  it('shows FROM badge on source clip', () => {
    const onSelect = vi.fn()
    const onSelectPair = vi.fn()
    render(
      <ClipSelector
        clips={mockClips}
        selectedClipId={null}
        onSelect={onSelect}
        pairMode
        selectedFromId="clip-1"
        selectedToId={null}
        onSelectPair={onSelectPair}
      />,
    )

    expect(screen.getByTestId('clip-from-badge-clip-1')).toBeDefined()
    expect(screen.getByText('FROM')).toBeDefined()
  })

  it('shows TO badge on target clip', () => {
    const onSelect = vi.fn()
    const onSelectPair = vi.fn()
    render(
      <ClipSelector
        clips={mockClips}
        selectedClipId={null}
        onSelect={onSelect}
        pairMode
        selectedFromId="clip-1"
        selectedToId="clip-2"
        onSelectPair={onSelectPair}
      />,
    )

    expect(screen.getByTestId('clip-to-badge-clip-2')).toBeDefined()
    expect(screen.getByText('TO')).toBeDefined()
  })

  it('highlights source with green and target with orange', () => {
    const onSelect = vi.fn()
    const onSelectPair = vi.fn()
    render(
      <ClipSelector
        clips={mockClips}
        selectedClipId={null}
        onSelect={onSelect}
        pairMode
        selectedFromId="clip-1"
        selectedToId="clip-2"
        onSelectPair={onSelectPair}
      />,
    )

    const fromBtn = screen.getByTestId('clip-option-clip-1')
    expect(fromBtn.className).toContain('border-green-500')

    const toBtn = screen.getByTestId('clip-option-clip-2')
    expect(toBtn.className).toContain('border-orange-500')
  })
})
