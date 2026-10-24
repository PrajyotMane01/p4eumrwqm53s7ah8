import { useQuery } from '@tanstack/react-query'
import { CalendarRange, Clock3, Layers, ListChecks } from 'lucide-react'
import { fetchDataStatus } from '../lib/api'
import { formatDate, formatUkDateTime } from '../lib/ukTime'
import { ErrorNotice } from './ErrorNotice'
import { StatCard } from './StatCard'

const n = (value: number) => value.toLocaleString('en-GB')

const SOURCES = [
  {
    code: 'FUELHH',
    name: 'Generation outturn by fuel type',
    use: 'Actuals: fuelType WIND only',
    detail: 'Half-hourly metered generation for Great Britain, as average MW over each 30 minutes.',
    href: 'https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream',
  },
  {
    code: 'WINDFOR',
    name: 'Wind generation forecast',
    use: 'Forecasts: one row per run and target hour',
    detail:
      'Hourly forecast for wind farms visible to the system operator with operational metering, published up to 8 times a day.',
    href: 'https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream',
  },
]

export function DataPage() {
  const query = useQuery({ queryKey: ['data-status'], queryFn: fetchDataStatus })

  if (query.isError) return <ErrorNotice error={query.error} onRetry={() => query.refetch()} />
  if (query.isPending) return <div className="card chart skeleton" aria-label="Loading data status" />

  const d = query.data
  const expected = d.days.reduce((sum, day) => sum + day.expected_half_hours, 0)
  const actual = d.days.reduce((sum, day) => sum + Math.min(day.actual_half_hours, day.expected_half_hours), 0)
  const incomplete = d.days.filter((day) => day.actual_half_hours < day.expected_half_hours)
  const perDay = d.days.length ? Math.round(d.days.reduce((sum, day) => sum + day.forecast_runs, 0) / d.days.length) : 0

  return (
    <>
      <div className="stat-grid">
        <StatCard
          label="Delivery days"
          value={n(d.days.length)}
          detail={d.first_date && d.last_date ? `${formatDate(d.first_date)} – ${formatDate(d.last_date)}` : 'None loaded'}
          icon={CalendarRange}
          highlight
        />
        <StatCard
          label="Actual half-hours"
          value={n(d.actual_rows)}
          detail={
            expected
              ? `${Math.round((actual / expected) * 100)}% complete${incomplete.length ? `, ${incomplete.length} days with gaps` : ''}`
              : undefined
          }
          icon={ListChecks}
        />
        <StatCard
          label="Forecast runs"
          value={n(d.forecast_runs)}
          detail={`${n(d.forecast_rows)} hourly values, about ${perDay} runs a day`}
          icon={Layers}
        />
        <StatCard
          label="Last loaded"
          value={d.source === 'elexon' ? 'Live' : d.refreshed_at ? formatUkDateTime(d.refreshed_at) : '–'}
          detail={d.source === 'elexon' ? 'Fetched from Elexon: database unavailable' : 'From the database, UK time'}
          icon={Clock3}
        />
      </div>

      <section className="card">
        <div className="card-head">
          <div>
            <h2>Sources</h2>
            <p className="card-sub">Elexon BMRS, GB national wind. No other data is used.</p>
          </div>
        </div>
        <div className="source-grid">
          {SOURCES.map((s) => (
            <article key={s.code} className="source-item">
              <p className="source-code">{s.code}</p>
              <h3>{s.name}</h3>
              <p className="card-sub">{s.use}</p>
              <p>{s.detail}</p>
              <a href={s.href} target="_blank" rel="noreferrer">
                Elexon documentation
              </a>
            </article>
          ))}
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <h2>Daily coverage</h2>
            <p className="card-sub">
              Actual half-hours per UK delivery day (46 or 50 on clock-change days) and forecast runs published that day
            </p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Delivery day</th>
                <th scope="col">Actual half-hours</th>
                <th scope="col">Status</th>
                <th scope="col">Forecast runs published</th>
              </tr>
            </thead>
            <tbody>
              {d.days.map((day) => {
                const missing = day.expected_half_hours - day.actual_half_hours
                return (
                  <tr key={day.delivery_date}>
                    <td>{formatDate(day.delivery_date)}</td>
                    <td>
                      {day.actual_half_hours} / {day.expected_half_hours}
                    </td>
                    <td>
                      <span className={`badge ${missing > 0 ? 'is-over' : 'is-under'}`}>
                        {missing > 0 ? `${missing} missing` : 'Complete'}
                      </span>
                    </td>
                    <td>{day.forecast_runs}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <h2>Load history</h2>
            <p className="card-sub">Recent loads from Elexon, newest first</p>
          </div>
        </div>
        {d.runs.length === 0 ? (
          <p className="card-sub">No loads recorded{d.source === 'elexon' ? ': data is being fetched live' : ''}.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Finished (UK)</th>
                  <th scope="col">Dataset</th>
                  <th scope="col">Delivery range</th>
                  <th scope="col">Rows</th>
                </tr>
              </thead>
              <tbody>
                {d.runs.map((run) => (
                  <tr key={`${run.dataset}-${run.finished_at}`}>
                    <td>{formatUkDateTime(run.finished_at)}</td>
                    <td>{run.dataset}</td>
                    <td>
                      {formatUkDateTime(run.range_start)} – {formatUkDateTime(run.range_end)}
                    </td>
                    <td>{n(run.row_count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}
