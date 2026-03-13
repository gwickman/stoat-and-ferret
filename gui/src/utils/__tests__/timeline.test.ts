import { describe, it, expect } from 'vitest'
import {
  timeToPixel,
  pixelToTime,
  getMarkerInterval,
  formatRulerTime,
} from '../timeline'

describe('timeToPixel', () => {
  it('converts time at zoom 1 with no scroll', () => {
    expect(timeToPixel(1, 1, 0)).toBe(100)
    expect(timeToPixel(2.5, 1, 0)).toBe(250)
  })

  it('applies zoom multiplier', () => {
    expect(timeToPixel(1, 2, 0)).toBe(200)
    expect(timeToPixel(1, 0.5, 0)).toBe(50)
  })

  it('subtracts scroll offset', () => {
    expect(timeToPixel(1, 1, 50)).toBe(50)
    expect(timeToPixel(2, 1, 100)).toBe(100)
  })

  it('handles zero zoom', () => {
    expect(timeToPixel(5, 0, 0)).toBe(0)
  })

  it('handles sub-second clips', () => {
    expect(timeToPixel(0.1, 1, 0)).toBeCloseTo(10)
    expect(timeToPixel(0.001, 1, 0)).toBeCloseTo(0.1)
  })

  it('handles very long timelines', () => {
    // 2 hour timeline at 100px/s = 720000 pixels
    expect(timeToPixel(7200, 1, 0)).toBe(720000)
  })

  it('handles negative scroll offset', () => {
    // Negative scroll means canvas shifted right
    expect(timeToPixel(1, 1, -50)).toBe(150)
  })

  it('uses custom pixelsPerSecond', () => {
    expect(timeToPixel(1, 1, 0, 200)).toBe(200)
    expect(timeToPixel(1, 2, 0, 50)).toBe(100)
  })

  it('returns 0 for time 0', () => {
    expect(timeToPixel(0, 1, 0)).toBe(0)
    expect(timeToPixel(0, 5, 100)).toBe(-100)
  })
})

describe('pixelToTime', () => {
  it('inverse of timeToPixel at zoom 1 with no scroll', () => {
    expect(pixelToTime(100, 1, 0)).toBe(1)
    expect(pixelToTime(250, 1, 0)).toBe(2.5)
  })

  it('accounts for zoom', () => {
    expect(pixelToTime(200, 2, 0)).toBe(1)
  })

  it('accounts for scroll offset', () => {
    expect(pixelToTime(50, 1, 50)).toBe(1)
  })

  it('returns 0 for zero zoom', () => {
    expect(pixelToTime(100, 0, 0)).toBe(0)
  })

  it('returns 0 for zero pixelsPerSecond', () => {
    expect(pixelToTime(100, 1, 0, 0)).toBe(0)
  })
})

describe('getMarkerInterval', () => {
  it('returns 1s interval at default zoom', () => {
    // At 100px/s, 1s interval = 100px gap (>= 80)
    expect(getMarkerInterval(1)).toBe(1)
  })

  it('returns smaller interval when zoomed in', () => {
    // At zoom 5, 100*5=500px/s. 0.25s * 500 = 125px
    const interval = getMarkerInterval(5)
    expect(interval).toBeLessThan(1)
  })

  it('returns larger interval when zoomed out', () => {
    // At zoom 0.1, 100*0.1=10px/s. Need large intervals
    const interval = getMarkerInterval(0.1)
    expect(interval).toBeGreaterThan(1)
  })
})

describe('formatRulerTime', () => {
  it('formats whole seconds', () => {
    expect(formatRulerTime(0)).toBe('0:00')
    expect(formatRulerTime(5)).toBe('0:05')
    expect(formatRulerTime(65)).toBe('1:05')
  })

  it('formats fractional seconds', () => {
    expect(formatRulerTime(0.5)).toBe('0:00.5')
    expect(formatRulerTime(1.5)).toBe('0:01.5')
  })

  it('formats minutes', () => {
    expect(formatRulerTime(60)).toBe('1:00')
    expect(formatRulerTime(90)).toBe('1:30')
    expect(formatRulerTime(125)).toBe('2:05')
  })
})
