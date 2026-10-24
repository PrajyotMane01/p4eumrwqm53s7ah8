// Filters arrive from the URL, which anyone can edit. Everything is checked here so the
// page only ever requests a valid range; the API validates again on its side.

export type Filters = { start: string; end: string; cutoff: string }

export type RawFilters = { start: string | null; end: string | null; cutoff: string | null }

export type Bounds = { first: string; last: string; defaultCutoff: string }

// Matches the API's limit
export const MAX_RANGE_DAYS = 62

const DAY_MS = 24 * 60 * 60 * 1000

/** "2026-01-15" if it is a real calendar date in that exact form, otherwise null. */
export function parseDate(value: string | null): string | null {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
  const [y, m, d] = value.split('-').map(Number)
  const date = new Date(Date.UTC(y, m - 1, d))
  // Rejects dates that roll over, such as 2026-02-30
  return date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d ? value : null
}

/** "09:50" from "09:50" or "09:50:00", otherwise null. */
export function parseCutoff(value: string | null): string | null {
  const match = value?.match(/^(\d{2}):(\d{2})(?::(\d{2}))?$/)
  if (!match) return null
  const [, hh, mm, ss] = match
  if (+hh > 23 || +mm > 59 || (ss !== undefined && +ss > 59)) return null
  return `${hh}:${mm}`
}

export const addDays = (date: string, days: number) => new Date(Date.parse(`${date}T00:00:00Z`) + days * DAY_MS).toISOString().slice(0, 10)

// ISO dates compare correctly as strings
const clamp = (date: string, lo: string, hi: string) => (date < lo ? lo : date > hi ? hi : date)

/**
 * Turn whatever is in the URL into filters the API will accept.
 * `corrections` lists the URL values that had to change, so the URL can be rewritten
 * to match what is shown.
 */
export function resolveFilters(raw: RawFilters, bounds: Bounds): { filters: Filters; corrections: Partial<Filters> } {
  const defaultCutoff = parseCutoff(bounds.defaultCutoff) ?? '09:50'
  let start = clamp(parseDate(raw.start) ?? bounds.first, bounds.first, bounds.last)
  let end = clamp(parseDate(raw.end) ?? bounds.last, bounds.first, bounds.last)
  if (start > end) [start, end] = [end, start]
  const longest = addDays(start, MAX_RANGE_DAYS - 1)
  if (end > longest) end = longest
  const cutoff = parseCutoff(raw.cutoff) ?? defaultCutoff

  const filters = { start, end, cutoff }
  const corrections: Partial<Filters> = {}
  for (const key of ['start', 'end', 'cutoff'] as const) {
    if (raw[key] !== null && raw[key] !== filters[key]) corrections[key] = filters[key]
  }
  return { filters, corrections }
}
