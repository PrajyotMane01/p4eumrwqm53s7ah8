import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { CircleCheck, LineChart, Wind, Zap } from 'lucide-react'
import { fetchSeries, type Coverage } from '../lib/api'
import { resolveFilters } from '../lib/filters'
import { formatMw, summarise } from '../lib/stats'
import { formatDate, formatUkDateTime } from '../lib/ukTime'
import { useUrlState } from '../lib/useUrlState'
import { Filters } from './Filters'
import { SeriesChart } from './SeriesChart'
import { StatCard } from './StatCard'

const KEYS = ['start', 'end', 'cutoff'] as const

type Props = { coverage: Coverage & { first_date: string; last_date: string } }

export function DayAheadPage({ coverage }: Props) {
  const [url, setUrl] = useUrlState(KEYS)
  const bounds = { first: coverage.first_date, last: coverage.last_date, defaultCutoff: coverage.default_cutoff }
  const { filters: query, corrections } = resolveFilters(url, bounds)
  const defaults = resolveFilters({ start: null, end: null, cutoff: null }, bounds).filters
  const isDefault = query.start === defaults.start && query.end === defaults.end && query.cutoff === defaults.cutoff

  // Rewrite invalid or out-of-range URL values so the address bar matches what is shown
  const needsCorrection = Object.keys(corrections).length > 0
  useEffect(() => {
    if (needsCorrection) setUrl(corrections)
  })

  const series = useQuery({
    queryKey: ['series', query],
    queryFn: () => fetchSeries(query),
    placeholderData: keepPreviousData,
  })

  const points = series.data?.points ?? []
  const summary = summarise(points)
  const withForecast = points.filter((p) => p.forecast_mw !== null).length

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Day-ahead wind</h1>
          <p className="subtitle">
            GB national wind generation against the forecast available at the decision cutoff. All times UK.
          </p>
        </div>
        <Filters
          {...query}
          min={coverage.first_date}
          max={coverage.last_date}
          isDefault={isDefault}
          onChange={setUrl}
          onReset={() => setUrl({ start: '', end: '', cutoff: '' })}
        />
      </header>

      {series.isError ? (
        <section className="card notice is-error" role="alert">
          <p>Could not load data: {series.error.message}</p>
          <button type="button" className="ghost-button" onClick={() => series.refetch()}>
            Try again
          </button>
        </section>
      ) : (
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
                  {formatDate(query.start)} – {formatDate(query.end)} · forecast as published by {query.cutoff} UK the
                  day before
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
                label={`Line chart of actual and day-ahead forecast wind generation, ${query.start} to ${query.end}`}
              />
            )}
          </section>
        </>
      )}
    </>
  )
}
