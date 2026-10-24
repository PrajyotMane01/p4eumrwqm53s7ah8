export type Coverage = {
  first_date: string | null
  last_date: string | null
  refreshed_at: string | null
  default_cutoff: string // "HH:MM:SS"
  source: 'database' | 'elexon' // 'elexon': database unavailable, fetched live
}

export type SeriesPoint = {
  start_time: string
  actual_mw: number | null
  forecast_mw: number | null
  publish_time: string | null
  horizon_hours: number | null
}

export type Series = {
  start: string
  end: string
  cutoff: string
  points: SeriesPoint[]
}

export type SeriesQuery = {
  start: string // YYYY-MM-DD, UK delivery day, inclusive
  end: string // YYYY-MM-DD, inclusive
  cutoff: string // HH:MM, UK time on the day before delivery
}

async function getJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = params ? `${path}?${new URLSearchParams(params)}` : path
  let res: Response
  try {
    res = await fetch(url)
  } catch {
    // The browser's own message ("Failed to fetch") means nothing to a user
    throw new Error('cannot reach the server. Check your connection and try again.')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : `HTTP ${res.status}`
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const fetchCoverage = () => getJson<Coverage>('/api/v1/coverage')

export const fetchSeries = (query: SeriesQuery) => getJson<Series>('/api/v1/series', query)

export type AccuracySummary = {
  half_hours: number
  missing: number
  mean_actual_mw: number
  mean_forecast_mw: number
  bias_mw: number
  mae_mw: number
  rmse_mw: number
  mae_pct: number
  p10_mw: number
  p50_mw: number
  p90_mw: number
  over_forecast_share: number
}

export type GroupStats = { half_hours: number; bias_mw: number; mae_mw: number }

export type Metrics = {
  start: string
  end: string
  cutoff: string
  summary: AccuracySummary | null
  histogram: { from_mw: number; to_mw: number; count: number }[]
  by_hour: (GroupStats & { hour: number })[]
  by_forecast_level: (GroupStats & { from_mw: number; to_mw: number | null })[]
  worst_days: (GroupStats & { delivery_date: string; max_abs_error_mw: number })[]
}

export const fetchMetrics = (query: SeriesQuery) => getJson<Metrics>('/api/v1/metrics', query)

export type DataStatus = {
  source: 'database' | 'elexon'
  refreshed_at: string | null
  first_date: string | null
  last_date: string | null
  actual_rows: number
  forecast_rows: number
  forecast_runs: number
  first_publish_time: string | null
  last_publish_time: string | null
  days: { delivery_date: string; expected_half_hours: number; actual_half_hours: number; forecast_runs: number }[]
  runs: { dataset: string; range_start: string; range_end: string; row_count: number; finished_at: string }[]
}

export const fetchDataStatus = () => getJson<DataStatus>('/api/v1/data')
