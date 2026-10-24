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

  // Rewrite invalid or out-of-range URL values so the address bar matches what is shown
  const needsCorrection = Object.keys(corrections).length > 0 || (url.view !== null && url.view !== view)
  useEffect(() => {
    if (needsCorrection) setUrl({ ...corrections, ...(url.view !== view ? { view } : {}) })
  })

  return {
    view,
    filters,
    isDefault,
    setFilters: setUrl,
    resetFilters: () => setUrl({ start: '', end: '', cutoff: '' }),
    // Day-ahead is the default view, so it is left out of the URL
    setView: (next: View) => setUrl({ view: next === 'day-ahead' ? '' : next }),
  }
}
