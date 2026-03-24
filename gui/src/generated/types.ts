/**
 * Convenience type aliases for generated OpenAPI schema types.
 *
 * Consumers should import from this module instead of hand-authoring
 * TypeScript interfaces that mirror backend schemas.
 */
import type { components } from './api-types'

// API-derived entity types
export type Effect = components['schemas']['EffectResponse']
export type Project = components['schemas']['ProjectResponse']
export type Clip = components['schemas']['ClipResponse']
export type Video = components['schemas']['VideoResponse']
export type Track = components['schemas']['TrackResponse']
export type LayoutPosition = components['schemas']['LayoutResponsePosition']
export type LayoutPreset = components['schemas']['LayoutPresetResponse']
export type TimelineClip = components['schemas']['TimelineClipResponse']

// API-derived response types
export type TimelineResponse = components['schemas']['TimelineResponse']
export type LayoutPresetListResponse = components['schemas']['LayoutPresetListResponse']

// Frontend-only sorting types (not API-derived, consolidated here for single import source)
export type SortField = 'date' | 'name' | 'duration'
export type SortOrder = 'asc' | 'desc'
