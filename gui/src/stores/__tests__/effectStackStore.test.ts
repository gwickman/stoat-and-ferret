import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useEffectStackStore } from '../effectStackStore'
import type { AppliedEffect } from '../effectStackStore'

const projectId = 'proj-1'
const clipId = 'clip-1'

const effect = (type: string): AppliedEffect => ({
  effect_type: type,
  parameters: {},
  filter_string: `${type}=1`,
})

function mockClipsResponse(effects: AppliedEffect[]) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
    new Response(
      JSON.stringify({ clips: [{ id: clipId, effects }] }),
      { status: 200 },
    ),
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
  useEffectStackStore.getState().reset()
})

describe('effectStackStore', () => {
  it('selectClip clears effects and clientIds', () => {
    useEffectStackStore.setState({
      effects: [effect('a')],
      clientIds: ['id-a'],
      selectedClipId: 'other-clip',
    })

    useEffectStackStore.getState().selectClip(clipId)

    const state = useEffectStackStore.getState()
    expect(state.selectedClipId).toBe(clipId)
    expect(state.effects).toEqual([])
    expect(state.clientIds).toEqual([])
  })

  it('reset clears effects and clientIds', () => {
    useEffectStackStore.setState({
      effects: [effect('a')],
      clientIds: ['id-a'],
      selectedClipId: clipId,
    })

    useEffectStackStore.getState().reset()

    const state = useEffectStackStore.getState()
    expect(state.selectedClipId).toBeNull()
    expect(state.effects).toEqual([])
    expect(state.clientIds).toEqual([])
  })

  it('initial fetch generates one client id per effect', async () => {
    mockClipsResponse([effect('a'), effect('b')])

    await useEffectStackStore.getState().fetchEffects(projectId, clipId)

    const state = useEffectStackStore.getState()
    expect(state.effects).toHaveLength(2)
    expect(state.clientIds).toHaveLength(2)
    expect(new Set(state.clientIds).size).toBe(2)
  })

  it('same-length fetch preserves client ids by index', async () => {
    mockClipsResponse([effect('a'), effect('b')])
    await useEffectStackStore.getState().fetchEffects(projectId, clipId)
    const idsAfterFirstFetch = useEffectStackStore.getState().clientIds

    mockClipsResponse([effect('a'), effect('b')])
    await useEffectStackStore.getState().fetchEffects(projectId, clipId)

    const state = useEffectStackStore.getState()
    expect(state.clientIds).toEqual(idsAfterFirstFetch)
  })

  it('append fetch preserves the prefix and generates ids only for new tail entries', async () => {
    mockClipsResponse([effect('a'), effect('b')])
    await useEffectStackStore.getState().fetchEffects(projectId, clipId)
    const idsAfterFirstFetch = useEffectStackStore.getState().clientIds

    mockClipsResponse([effect('a'), effect('b'), effect('c')])
    await useEffectStackStore.getState().fetchEffects(projectId, clipId)

    const state = useEffectStackStore.getState()
    expect(state.clientIds).toHaveLength(3)
    expect(state.clientIds.slice(0, 2)).toEqual(idsAfterFirstFetch)
    expect(state.clientIds[2]).not.toBe(idsAfterFirstFetch[0])
    expect(state.clientIds[2]).not.toBe(idsAfterFirstFetch[1])
  })

  it('successful delete splices ids and effects together', async () => {
    mockClipsResponse([effect('a'), effect('b'), effect('c')])
    await useEffectStackStore.getState().fetchEffects(projectId, clipId)
    const idsBeforeDelete = useEffectStackStore.getState().clientIds

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(null, { status: 204 }))

    await useEffectStackStore.getState().removeEffect(projectId, clipId, 0)

    const state = useEffectStackStore.getState()
    expect(state.effects.map((e) => e.effect_type)).toEqual(['b', 'c'])
    expect(state.clientIds).toEqual([idsBeforeDelete[1], idsBeforeDelete[2]])
    expect(state.clientIds).toHaveLength(state.effects.length)
  })

  it('failed delete preserves effects and clientIds', async () => {
    mockClipsResponse([effect('a'), effect('b')])
    await useEffectStackStore.getState().fetchEffects(projectId, clipId)
    const effectsBeforeDelete = useEffectStackStore.getState().effects
    const idsBeforeDelete = useEffectStackStore.getState().clientIds

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(null, { status: 500 }))

    await useEffectStackStore.getState().removeEffect(projectId, clipId, 0)

    const state = useEffectStackStore.getState()
    expect(state.effects).toEqual(effectsBeforeDelete)
    expect(state.clientIds).toEqual(idsBeforeDelete)
    expect(state.error).not.toBeNull()
  })
})
