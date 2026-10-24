import { useEffect } from 'react'
import type { Coverage } from './api'
import { resolveFilters } from './filters'
import { useUrlState } from './useUrlState'

const KEYS = ['view', 'start', 'end', 'cutoff'] as const

export type View = 'day-ahead' | 'accuracy'

export type LoadedCoverage = Coverage & { first_date: string; last_date: string }

/** The current view and filters, read from and written to the URL. Shared by every page. */
export function useFilters(coverage: LoadedCoverage) {
  const [url, setUrl] = useUrlState(KEYS)
  const bounds = { first: coverage.first_date, last: coverage.last_date, defaultCutoff: coverage.default_cutoff }
  const { filters, corrections } = resolveFilters(url, bounds)
  const defaults = resolveFilters({ start: null, end: null, cutoff: null }, bounds).filters
  const isDefault = filters.start === defaults.start && filters.end === defaults.end && filters.cutoff === defaults.cutoff
  const view: View = url.view === 'accuracy' ? 'accuracy' : 'day-ahead'

  // Rewrite invalid or out-of-range URL values so the address bar matches what is shown.
  // Day-ahead is the default view, so an unknown view is removed rather than spelled out.
  const badView = url.view !== null && url.view !== 'accuracy'
  const needsCorrection = Object.keys(corrections).length > 0 || badView
  useEffect(() => {
    if (needsCorrection) setUrl({ ...corrections, ...(badView ? { view: '' } : {}) })
  })

  return {
    view,
    filters,
    isDefault,
    setFilters: setUrl,
    resetFilters: () => setUrl({ start: '', end: '', cutoff: '' }),
    // Moving between views adds a history entry, so Back returns to where the user was
    setView: (next: View) => setUrl({ view: next === 'day-ahead' ? '' : next }, { push: true }),
    openDay: (day: string) => setUrl({ view: '', start: day, end: day }, { push: true }),
  }
}
