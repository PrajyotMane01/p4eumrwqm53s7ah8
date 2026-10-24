import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { CircleCheck, LineChart, Wind, Zap } from 'lucide-react'
import { fetchSeries } from '../lib/api'
import type { Filters } from '../lib/filters'
import { formatMw, summarise } from '../lib/stats'
import { formatDate, formatUkDateTime } from '../lib/ukTime'
import { ErrorNotice } from './ErrorNotice'
import { SeriesChart } from './SeriesChart'
import { StatCard } from './StatCard'

export function DayAheadPage({ filters }: { filters: Filters }) {
  const series = useQuery({
    queryKey: ['series', filters],
    queryFn: () => fetchSeries(filters),
    placeholderData: keepPreviousData,
  })

  if (series.isError) return <ErrorNotice error={series.error} onRetry={() => series.refetch()} />

  const points = series.data?.points ?? []
  const summary = summarise(points)
  const withForecast = points.filter((p) => p.forecast_mw !== null).length

  return (
    <>
      <div className="stat-grid" aria-busy={series.isFetching}>
        <StatCard label="Average actual" value={formatMw(summary.avgActual)} icon={Wind} highlight />
        <StatCard label="Average day-ahead forecast" value={formatMw(summary.avgForecast)} icon={LineChart} />
        <StatCard
          label="Peak actual"
          value={formatMw(summary.peakActual?.mw ?? null)}
          detail={summary.peakActual ? `${formatUkDateTime(summary.peakActual.at)} UK` : undefined}
          icon={Zap}
        />
        <StatCard
          label="Forecast coverage"
          value={summary.forecastCoverage === null ? '–' : `${Math.round(summary.forecastCoverage * 100)}%`}
          detail={`${withForecast.toLocaleString('en-GB')} of ${points.length.toLocaleString('en-GB')} half-hours`}
          icon={CircleCheck}
        />
      </div>

      <section className="card chart-card">
        <div className="card-head">
          <div>
            <h2>Actual vs day-ahead forecast</h2>
            <p className="card-sub">
              {formatDate(filters.start)} – {formatDate(filters.end)} · forecast as published by {filters.cutoff} UK
              the day before
            </p>
          </div>
          <ul className="legend" aria-label="Legend">
            <li>
              <i className="swatch is-actual" /> Actual
            </li>
            <li>
              <i className="swatch is-forecast" /> Day-ahead forecast
            </li>
          </ul>
        </div>
        {series.isPending ? (
          <div className="chart skeleton" aria-label="Loading chart" />
        ) : (
          <SeriesChart
            points={points}
            label={`Line chart of actual and day-ahead forecast wind generation, ${filters.start} to ${filters.end}`}
          />
        )}
      </section>
    </>
  )
}
