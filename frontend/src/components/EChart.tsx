import { BarChart, LineChart } from 'echarts/charts'
import { DataZoomComponent, GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useRef } from 'react'

echarts.use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, DataZoomComponent, CanvasRenderer])

export type ChartOption = echarts.EChartsCoreOption

/** An ECharts canvas that resizes with its container. `label` describes the chart for screen readers. */
export function EChart({ option, label, className = 'chart' }: { option: ChartOption; label: string; className?: string }) {
  const container = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!container.current) return
    const instance = echarts.init(container.current)
    chart.current = instance
    const observer = new ResizeObserver(() => instance.resize())
    observer.observe(container.current)
    return () => {
      observer.disconnect()
      instance.dispose()
      chart.current = null
    }
  }, [])

  useEffect(() => {
    chart.current?.setOption(option, true)
  }, [option])

  return <div ref={container} className={className} role="img" aria-label={label} />
}
