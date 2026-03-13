/** Client-side preset position data matching Rust LayoutPreset definitions. */
import type { LayoutPosition } from '../types/timeline'

/** Well-known positions for each layout preset. */
export const PRESET_POSITIONS: Record<string, LayoutPosition[]> = {
  PipTopLeft: [
    { x: 0.0, y: 0.0, width: 1.0, height: 1.0, z_index: 0 },
    { x: 0.02, y: 0.02, width: 0.25, height: 0.25, z_index: 1 },
  ],
  PipTopRight: [
    { x: 0.0, y: 0.0, width: 1.0, height: 1.0, z_index: 0 },
    { x: 0.73, y: 0.02, width: 0.25, height: 0.25, z_index: 1 },
  ],
  PipBottomLeft: [
    { x: 0.0, y: 0.0, width: 1.0, height: 1.0, z_index: 0 },
    { x: 0.02, y: 0.73, width: 0.25, height: 0.25, z_index: 1 },
  ],
  PipBottomRight: [
    { x: 0.0, y: 0.0, width: 1.0, height: 1.0, z_index: 0 },
    { x: 0.73, y: 0.73, width: 0.25, height: 0.25, z_index: 1 },
  ],
  SideBySide: [
    { x: 0.0, y: 0.0, width: 0.5, height: 1.0, z_index: 0 },
    { x: 0.5, y: 0.0, width: 0.5, height: 1.0, z_index: 0 },
  ],
  TopBottom: [
    { x: 0.0, y: 0.0, width: 1.0, height: 0.5, z_index: 0 },
    { x: 0.0, y: 0.5, width: 1.0, height: 0.5, z_index: 0 },
  ],
  Grid2x2: [
    { x: 0.0, y: 0.0, width: 0.5, height: 0.5, z_index: 0 },
    { x: 0.5, y: 0.0, width: 0.5, height: 0.5, z_index: 0 },
    { x: 0.0, y: 0.5, width: 0.5, height: 0.5, z_index: 0 },
    { x: 0.5, y: 0.5, width: 0.5, height: 0.5, z_index: 0 },
  ],
}
