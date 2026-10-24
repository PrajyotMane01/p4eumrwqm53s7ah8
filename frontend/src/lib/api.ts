export type Coverage = {
  first_date: string | null
  last_date: string | null
  refreshed_at: string | null
  default_cutoff: string // "HH:MM:SS"
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
