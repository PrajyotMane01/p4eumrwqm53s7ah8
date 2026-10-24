import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { CircleCheck, LineChart, Wind, Zap } from 'lucide-react'
import { fetchSeries, type SeriesPoint } from '../lib/api'
import type { Filters } from '../lib/filters'
import { formatMw, summarise } from '../lib/stats'
import { formatDate, formatUkDateTime } from '../lib/ukTime'
import { ErrorNotice } from './ErrorNotice'
import { SeriesChart } from './SeriesChart'
import { StatCard } from './StatCard'

/** Which forecast run the cutoff selects: named for a single run, described for several. */
function runNote(points: SeriesPoint[], cutoff: string): string {
  const runs = [...new Set(points.map((p) => p.publish_time).filter((t): t is string => t !== null))]
  if (runs.length === 1) return `using the forecast published ${formatUkDateTime(runs[0])} UK (latest by ${cutoff} on D-1)`
  if (runs.length === 0) return `no forecast was published by ${cutoff} UK on D-1`
  return `each day uses the latest forecast published by ${cutoff} UK the day before`
}

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
              {filters.start === filters.end
                ? formatDate(filters.start)
                : `${formatDate(filters.start)} – ${formatDate(filters.end)}`}{' '}
              · {runNote(points, filters.cutoff)}
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
