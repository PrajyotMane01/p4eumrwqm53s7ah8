import type { SeriesPoint } from './api'

export type Summary = {
  avgActual: number | null
  avgForecast: number | null
  peakActual: { mw: number; at: string } | null
  forecastCoverage: number | null // share of half-hours with a forecast, 0..1
}

const mean = (values: number[]) => (values.length ? values.reduce((a, b) => a + b, 0) / values.length : null)

export function summarise(points: SeriesPoint[]): Summary {
  const actuals = points.filter((p) => p.actual_mw !== null)
  const forecasts = points.filter((p) => p.forecast_mw !== null).map((p) => p.forecast_mw as number)
  const peak = actuals.reduce<SeriesPoint | null>(
    (best, p) => (best === null || (p.actual_mw as number) > (best.actual_mw as number) ? p : best),
    null,
  )
  return {
    avgActual: mean(actuals.map((p) => p.actual_mw as number)),
    avgForecast: mean(forecasts),
    peakActual: peak ? { mw: peak.actual_mw as number, at: peak.start_time } : null,
    forecastCoverage: points.length ? forecasts.length / points.length : null,
  }
}

const mwFormatter = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })

export const formatMw = (value: number | null) => (value === null ? '–' : `${mwFormatter.format(value)} MW`)
