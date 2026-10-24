import { describe, expect, it } from 'vitest'
import { parseCutoff, parseDate, resolveFilters } from './filters'

const bounds = { first: '2026-01-01', last: '2026-02-01', defaultCutoff: '09:50:00' }
const none = { start: null, end: null, cutoff: null }

describe('parseDate', () => {
  it('accepts real dates in YYYY-MM-DD form', () => {
    expect(parseDate('2026-01-15')).toBe('2026-01-15')
    expect(parseDate('2024-02-29')).toBe('2024-02-29') // leap year
  })

  it.each(['banana', '', '2026-1-15', '15/01/2026', '2026-02-30', '2026-13-01', '2026-01-15T00:00', ' 2026-01-15'])(
    'rejects %j',
    (value) => expect(parseDate(value)).toBeNull(),
  )
})

describe('parseCutoff', () => {
  it('normalises to HH:MM', () => {
    expect(parseCutoff('09:50')).toBe('09:50')
    expect(parseCutoff('09:50:00')).toBe('09:50')
    expect(parseCutoff('00:00')).toBe('00:00')
    expect(parseCutoff('23:59')).toBe('23:59')
  })

  it.each(['24:00', '09:60', '9:50', '0950', 'noon', '09:50:61', '<script>'])('rejects %j', (value) =>
    expect(parseCutoff(value)).toBeNull(),
  )
})

describe('resolveFilters', () => {
  it('uses defaults when the URL has nothing, without asking for corrections', () => {
    expect(resolveFilters(none, bounds)).toEqual({
      filters: { start: '2026-01-01', end: '2026-02-01', cutoff: '09:50' },
      corrections: {},
    })
  })

  it('keeps valid values as they are', () => {
    const raw = { start: '2026-01-14', end: '2026-01-16', cutoff: '09:20' }
    expect(resolveFilters(raw, bounds)).toEqual({ filters: raw, corrections: {} })
  })

  it('replaces invalid values with defaults and reports them', () => {
    const { filters, corrections } = resolveFilters({ start: 'banana', end: null, cutoff: '25:00' }, bounds)
    expect(filters).toEqual({ start: '2026-01-01', end: '2026-02-01', cutoff: '09:50' })
    expect(corrections).toEqual({ start: '2026-01-01', cutoff: '09:50' })
  })

  it('clamps dates to the stored range', () => {
    const { filters } = resolveFilters({ start: '2025-06-01', end: '2026-12-31', cutoff: null }, bounds)
    expect(filters).toMatchObject({ start: '2026-01-01', end: '2026-02-01' })
  })

  it('swaps a reversed range', () => {
    const { filters } = resolveFilters({ start: '2026-01-20', end: '2026-01-10', cutoff: null }, bounds)
    expect(filters).toMatchObject({ start: '2026-01-10', end: '2026-01-20' })
  })

  it('limits the range to 62 days', () => {
    const wide = { first: '2025-01-01', last: '2026-12-31', defaultCutoff: '09:50' }
    const { filters } = resolveFilters({ start: '2026-01-01', end: '2026-12-31', cutoff: null }, wide)
    expect(filters.end).toBe('2026-03-03') // 1 Jan + 61 days
  })

  it('normalises a cutoff with seconds and reports it', () => {
    const { filters, corrections } = resolveFilters({ ...none, cutoff: '09:20:00' }, bounds)
    expect(filters.cutoff).toBe('09:20')
    expect(corrections).toEqual({ cutoff: '09:20' })
  })

  it('is stable: resolving corrected values needs no further correction', () => {
    const { filters } = resolveFilters({ start: '2026-01-20', end: 'x', cutoff: '9am' }, bounds)
    expect(resolveFilters(filters, bounds).corrections).toEqual({})
  })
})
