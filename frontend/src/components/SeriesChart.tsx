import { useMemo } from 'react'
import type { SeriesPoint } from '../lib/api'
import { formatMw } from '../lib/stats'
import { theme } from '../lib/theme'
import { formatUkAxisLabel, formatUkDateTime } from '../lib/ukTime'
import { EChart, type ChartOption } from './EChart'

const HALF_HOURS_PER_DAY = 48

function tooltip(point: SeriesPoint): string {
  const { actual_mw: actual, forecast_mw: forecast } = point
  const diff = actual !== null && forecast !== null ? forecast - actual : null
  const sign = diff !== null && diff > 0 ? '+' : ''
  const row = (label: string, value: string, color?: string) =>
    `<div class="tt-row">${color ? `<i style="background:${color}"></i>` : '<i></i>'}<span>${label}</span><b>${value}</b></div>`
  return [
    `<div class="tt-time">${formatUkDateTime(point.start_time)} UK</div>`,
    row('Actual', formatMw(actual), theme.actual),
    row('Forecast', formatMw(forecast), theme.forecast),
    row('Forecast − actual', diff === null ? '–' : `${sign}${formatMw(diff)}`),
    point.publish_time
      ? `<div class="tt-meta">Forecast published ${formatUkDateTime(point.publish_time)} (${point.horizon_hours}h ahead)</div>`
      : '<div class="tt-meta">No forecast published by the cutoff</div>',
  ].join('')
}

function buildOption(points: SeriesPoint[]): ChartOption {
  const x = points.map((p) => Date.parse(p.start_time))
  const zoomable = points.length > 3 * HALF_HOURS_PER_DAY
  return {
    useUTC: true, // pick ticks in UTC (equal to UK time in winter); labels are formatted in UK time
    animation: false,
    grid: { left: 8, right: 16, top: 32, bottom: zoomable ? 64 : 24, containLabel: true },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: theme.grid } },
      axisTick: { show: false },
      axisLabel: { color: theme.muted, hideOverlap: true, formatter: (ms: number) => formatUkAxisLabel(ms) },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      name: 'MW',
      nameTextStyle: { color: theme.muted, align: 'right' },
      axisLabel: { color: theme.muted, formatter: (v: number) => `${v / 1000}k` },
      splitLine: { lineStyle: { color: theme.grid, type: 'dashed' } },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: theme.tooltipBg,
      borderColor: theme.tooltipBorder,
      padding: [10, 12],
      textStyle: { color: theme.text, fontSize: 12 },
      extraCssText: 'border-radius:10px;box-shadow:0 6px 20px rgba(28,35,33,0.08);',
      axisPointer: { type: 'line', lineStyle: { color: theme.forecast, type: 'dashed' } },
      formatter: (params: unknown) => {
        const first = (Array.isArray(params) ? params[0] : params) as { dataIndex: number }
        return tooltip(points[first.dataIndex])
      },
    },
    // Scroll or pinch to zoom at any range; the slider only once the range is long
    dataZoom: [
      { type: 'inside', filterMode: 'none' },
      ...(zoomable
        ? [
            {
            type: 'slider',
            height: 22,
            bottom: 12,
            borderColor: theme.grid,
            fillerColor: 'rgba(228, 244, 126, 0.35)',
            handleStyle: { color: theme.forecast, borderColor: theme.forecast },
            moveHandleStyle: { color: theme.grid },
            emphasis: { moveHandleStyle: { color: theme.forecast } },
            showDetail: false,
              dataBackground: { lineStyle: { color: theme.actual }, areaStyle: { color: theme.actualFill } },
            },
          ]
        : []),
    ],
    series: [
      {
        name: 'Actual',
        type: 'line',
        showSymbol: false,
        connectNulls: false,
        lineStyle: { color: theme.actual, width: 1.5 },
        itemStyle: { color: theme.actual },
        areaStyle: { color: theme.actualFill },
        data: points.map((p, i) => [x[i], p.actual_mw]),
      },
      {
        name: 'Day-ahead forecast',
        type: 'line',
        showSymbol: false,
        connectNulls: false,
        lineStyle: { color: theme.forecast, width: 2 },
        itemStyle: { color: theme.forecast },
        data: points.map((p, i) => [x[i], p.forecast_mw]),
      },
    ],
  }
}

export function SeriesChart({ points, label }: { points: SeriesPoint[]; label: string }) {
  const option = useMemo(() => buildOption(points), [points])
  return <EChart option={option} label={label} />
}
