import { describe, it, expect, beforeEach } from 'vitest'
import { useTransitionStore } from '../transitionStore'

describe('useTransitionStore', () => {
  beforeEach(() => {
    useTransitionStore.getState().reset()
  })

  it('starts with null source and target', () => {
    const state = useTransitionStore.getState()
    expect(state.sourceClipId).toBeNull()
    expect(state.targetClipId).toBeNull()
  })

  it('selectSource sets source and clears target', () => {
    const store = useTransitionStore.getState()
    store.selectTarget('clip-2') // set target first
    store.selectSource('clip-1')

    const state = useTransitionStore.getState()
    expect(state.sourceClipId).toBe('clip-1')
    expect(state.targetClipId).toBeNull()
  })

  it('selectTarget sets target', () => {
    const store = useTransitionStore.getState()
    store.selectSource('clip-1')
    store.selectTarget('clip-2')

    const state = useTransitionStore.getState()
    expect(state.targetClipId).toBe('clip-2')
  })

  it('isReady returns false when only source selected', () => {
    useTransitionStore.getState().selectSource('clip-1')
    expect(useTransitionStore.getState().isReady()).toBe(false)
  })

  it('isReady returns false when neither selected', () => {
    expect(useTransitionStore.getState().isReady()).toBe(false)
  })

  it('isReady returns true when both selected', () => {
    const store = useTransitionStore.getState()
    store.selectSource('clip-1')
    store.selectTarget('clip-2')
    expect(useTransitionStore.getState().isReady()).toBe(true)
  })

  it('reset clears both selections', () => {
    const store = useTransitionStore.getState()
    store.selectSource('clip-1')
    store.selectTarget('clip-2')
    store.reset()

    const state = useTransitionStore.getState()
    expect(state.sourceClipId).toBeNull()
    expect(state.targetClipId).toBeNull()
  })
})
