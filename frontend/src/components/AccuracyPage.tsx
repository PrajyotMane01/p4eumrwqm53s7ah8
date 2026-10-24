import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Gauge, Scale, ShieldAlert, Sigma } from 'lucide-react'
import { useMemo } from 'react'
import { fetchMetrics, type Metrics } from '../lib/api'
import type { Filters } from '../lib/filters'
import { formatK, formatMw, formatSignedMw } from '../lib/stats'
import { theme } from '../lib/theme'
import { formatDate } from '../lib/ukTime'
import { EChart, type ChartOption } from './EChart'
import { ErrorNotice } from './ErrorNotice'
import { StatCard } from './StatCard'

type Props = { filters: Filters; onOpenDay: (day: string) => void }

const pct = (share: number) => `${Math.round(share * 100)}%`

const baseGrid = { left: 8, right: 16, top: 32, bottom: 8, containLabel: true }
const valueAxis = (name: string) => ({
  type: 'value',
  name,
  nameTextStyle: { color: theme.muted, align: 'right' },
  axisLabel: { color: theme.muted, formatter: formatK },
  splitLine: { lineStyle: { color: theme.grid, type: 'dashed' } },
})
const categoryAxis = (data: string[], name?: string) => ({
  type: 'category',
  data,
  name,
  nameLocation: 'middle',
  nameGap: 28,
  nameTextStyle: { color: theme.muted },
  axisLine: { lineStyle: { color: theme.grid } },
  axisTick: { show: false },
  axisLabel: { color: theme.muted },
})
const tooltip = {
  trigger: 'axis',
  backgroundColor: theme.tooltipBg,
  borderColor: theme.tooltipBorder,
  textStyle: { color: theme.text, fontSize: 12 },
  extraCssText: 'border-radius:10px;box-shadow:0 6px 20px rgba(28,35,33,0.08);',
}

function histogramOption(m: Metrics): ChartOption {
  const total = m.summary?.half_hours ?? 1
  const labels = m.histogram.map((b) => formatK(b.from_mw))
  return {
    animation: false,
    grid: { ...baseGrid, bottom: 32 },
    tooltip: {
      ...tooltip,
      formatter: (params: unknown) => {
        const { dataIndex } = (params as { dataIndex: number }[])[0]
        const b = m.histogram[dataIndex]
        return `<b>${formatSignedMw(b.from_mw)} to ${formatSignedMw(b.to_mw)}</b><br/>${b.count} half-hours (${pct(b.count / total)})`
      },
    },
    xAxis: { ...categoryAxis(labels, 'Forecast − actual (MW)'), axisLabel: { color: theme.muted, interval: 0 } },
    yAxis: {
      ...valueAxis('Half-hours'),
      nameTextStyle: { color: theme.muted, align: 'left' },
      axisLabel: { color: theme.muted },
    },
    series: [
      {
        type: 'bar',
        barCategoryGap: '12%',
        data: m.histogram.map((b) => ({
          value: b.count,
          // Over-forecasts (forecast above actual) in the forecast colour, under-forecasts in the actual colour
          itemStyle: { color: b.from_mw >= 0 ? theme.forecast : theme.actual, borderRadius: [4, 4, 0, 0] },
        })),
      },
    ],
  }
}

function levelOption(m: Metrics): ChartOption {
  const labels = m.by_forecast_level.map((b) =>
    b.to_mw === null ? `${b.from_mw / 1000}+ GW` : `${b.from_mw / 1000}–${b.to_mw / 1000} GW`,
  )
  return {
    animation: false,
    grid: { ...baseGrid, bottom: 32 },
    legend: { show: false },
    tooltip: {
      ...tooltip,
      formatter: (params: unknown) => {
        const { dataIndex } = (params as { dataIndex: number }[])[0]
        const b = m.by_forecast_level[dataIndex]
        return `<b>Forecast ${labels[dataIndex]}</b><br/>Bias ${formatSignedMw(b.bias_mw)}<br/>MAE ${formatMw(b.mae_mw)}<br/>${b.half_hours} half-hours`
      },
    },
    xAxis: categoryAxis(labels, 'Day-ahead forecast level'),
    yAxis: valueAxis('MW'),
    series: [
      { name: 'Bias', type: 'bar', data: m.by_forecast_level.map((b) => b.bias_mw), itemStyle: { color: theme.forecast, borderRadius: [4, 4, 0, 0] } },
      { name: 'MAE', type: 'bar', data: m.by_forecast_level.map((b) => b.mae_mw), itemStyle: { color: theme.actual, borderRadius: [4, 4, 0, 0] } },
    ],
  }
}

function hourOption(m: Metrics): ChartOption {
  const labels = m.by_hour.map((h) => `${String(h.hour).padStart(2, '0')}:00`)
  return {
    animation: false,
    grid: { ...baseGrid, bottom: 32 },
    tooltip: {
      ...tooltip,
      formatter: (params: unknown) => {
        const { dataIndex } = (params as { dataIndex: number }[])[0]
        const h = m.by_hour[dataIndex]
        return `<b>${labels[dataIndex]}–${String(h.hour).padStart(2, '0')}:59 UK</b><br/>MAE ${formatMw(h.mae_mw)}<br/>Bias ${formatSignedMw(h.bias_mw)}`
      },
    },
    xAxis: categoryAxis(labels, 'Hour of day (UK)'),
    yAxis: valueAxis('MW'),
    series: [
      { name: 'MAE', type: 'bar', data: m.by_hour.map((h) => h.mae_mw), itemStyle: { color: theme.actualFill.replace('0.28', '0.9'), borderRadius: [3, 3, 0, 0] } },
      { name: 'Bias', type: 'line', data: m.by_hour.map((h) => h.bias_mw), symbol: 'circle', symbolSize: 5, lineStyle: { color: theme.forecast, width: 2 }, itemStyle: { color: theme.forecast } },
    ],
  }
}

function Legend({ items }: { items: [string, string][] }) {
  return (
    <ul className="legend" aria-label="Legend">
      {items.map(([label, className]) => (
        <li key={label}>
          <i className={`swatch ${className}`} /> {label}
        </li>
      ))}
    </ul>
  )
}

export function AccuracyPage({ filters, onOpenDay }: Props) {
  const query = useQuery({
    queryKey: ['metrics', filters],
    queryFn: () => fetchMetrics(filters),
    placeholderData: keepPreviousData,
  })
  const m = query.data
  const options = useMemo(
    () => (m ? { histogram: histogramOption(m), level: levelOption(m), hour: hourOption(m) } : null),
    [m],
  )

  if (query.isError) return <ErrorNotice error={query.error} onRetry={() => query.refetch()} />
  if (query.isPending || !m || !options) return <div className="card chart skeleton" aria-label="Loading accuracy" />

  const s = m.summary
  if (!s) {
    return <section className="card notice">No half-hours in this range have both an actual and a forecast to score.</section>
  }
  const range = `${formatDate(filters.start)} – ${formatDate(filters.end)} · cutoff ${filters.cutoff} UK on D-1`

  return (
    <>
      <div className="stat-grid" aria-busy={query.isFetching}>
        <StatCard
          label="Mean absolute error"
          value={formatMw(s.mae_mw)}
          detail={`${s.mae_pct.toFixed(1)}% of average actual`}
          icon={Gauge}
          highlight
        />
        <StatCard
          label="Bias (forecast − actual)"
          value={formatSignedMw(s.bias_mw)}
          detail={`Over-forecast in ${pct(s.over_forecast_share)} of half-hours`}
          icon={Scale}
        />
        <StatCard
          label="P90 shortfall"
          value={formatMw(Math.max(s.p90_mw, 0))}
          detail="In 9 of 10 half-hours, actual was at most this far below forecast"
          icon={ShieldAlert}
        />
        <StatCard label="RMSE" value={formatMw(s.rmse_mw)} detail="Weights large misses more heavily" icon={Sigma} />
      </div>

      <section className="card insight">
        <h2>What this means for buying</h2>
        <p>
          Over this range the day-ahead forecast was {formatSignedMw(s.bias_mw)} off on average and too high in{' '}
          {pct(s.over_forecast_share)} of half-hours, so relying on it as-is leads to under-buying. Holding back{' '}
          <b>{formatMw(Math.max(s.p90_mw, 0))}</b> would have covered the shortfall in 9 of 10 half-hours.
        </p>
        {s.missing > 0 && (
          <p className="insight-note">
            Scored {s.half_hours.toLocaleString('en-GB')} of {(s.half_hours + s.missing).toLocaleString('en-GB')}{' '}
            half-hours: {s.missing.toLocaleString('en-GB')} had no forecast published by the cutoff, or no actual.
          </p>
        )}
        <p className="insight-note">
          The over-forecast grows with wind level (below). That pattern is consistent with wind farms being curtailed
          at high output, which these two datasets cannot confirm.
        </p>
      </section>

      <div className="chart-grid">
        <section className="card chart-card">
          <div className="card-head">
            <div>
              <h2>Error distribution</h2>
              <p className="card-sub">
                P10 {formatSignedMw(s.p10_mw)} · median {formatSignedMw(s.p50_mw)} · P90 {formatSignedMw(s.p90_mw)}
              </p>
            </div>
            <Legend items={[['Over-forecast', 'is-forecast'], ['Under-forecast', 'is-actual']]} />
          </div>
          <EChart option={options.histogram} className="chart is-compact" label={`Histogram of forecast error, ${range}`} />
        </section>

        <section className="card chart-card">
          <div className="card-head">
            <div>
              <h2>Error by forecast level</h2>
              <p className="card-sub">The more wind forecast, the more it over-shoots</p>
            </div>
            <Legend items={[['Bias', 'is-forecast'], ['MAE', 'is-actual']]} />
          </div>
          <EChart option={options.level} className="chart is-compact" label={`Bar chart of bias and MAE by forecast level, ${range}`} />
        </section>
      </div>

      <section className="card chart-card">
        <div className="card-head">
          <div>
            <h2>Error by hour of day</h2>
            <p className="card-sub">
              {range}. With a fixed cutoff, later hours are also forecast further ahead.
            </p>
          </div>
          <Legend items={[['MAE', 'is-actual-soft'], ['Bias', 'is-forecast']]} />
        </div>
        <EChart option={options.hour} className="chart is-compact" label={`Bar chart of error by UK hour of day, ${range}`} />
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <h2>Worst days</h2>
            <p className="card-sub">Delivery days with the largest mean absolute error</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Delivery day</th>
                <th scope="col">MAE</th>
                <th scope="col">Bias</th>
                <th scope="col">Largest miss</th>
                <th scope="col">
                  <span className="sr-only">Action</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {m.worst_days.map((d) => (
                <tr key={d.delivery_date}>
                  <td>{formatDate(d.delivery_date)}</td>
                  <td>{formatMw(d.mae_mw)}</td>
                  <td>
                    <span className={`badge ${d.bias_mw > 0 ? 'is-over' : 'is-under'}`}>{formatSignedMw(d.bias_mw)}</span>
                  </td>
                  <td>{formatMw(d.max_abs_error_mw)}</td>
                  <td className="cell-action">
                    <button type="button" className="ghost-button" onClick={() => onOpenDay(d.delivery_date)}>
                      View day
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}
