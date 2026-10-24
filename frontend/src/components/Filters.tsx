import { CalendarDays, Clock, RotateCcw } from 'lucide-react'
import type { MouseEvent } from 'react'

// Open the native picker on any click, not only on the browser's small icon
const openPicker = (e: MouseEvent<HTMLInputElement>) => e.currentTarget.showPicker?.()

type Props = {
  start: string
  end: string
  cutoff: string
  min?: string
  max?: string
  isDefault: boolean
  onChange: (next: { start?: string; end?: string; cutoff?: string }) => void
  onReset: () => void
}

export function Filters({ start, end, cutoff, min, max, isDefault, onChange, onReset }: Props) {
  return (
    <div className="filters" role="group" aria-label="Filters">
      <div className="pill">
        <CalendarDays size={16} aria-hidden />
        <label className="sr-only" htmlFor="start">
          First delivery day
        </label>
        <input
          id="start"
          type="date"
          onClick={openPicker}
          value={start}
          min={min}
          max={max}
          onChange={(e) => e.target.value && onChange({ start: e.target.value, end: e.target.value > end ? e.target.value : end })}
        />
        <span aria-hidden>–</span>
        <label className="sr-only" htmlFor="end">
          Last delivery day
        </label>
        <input
          id="end"
          type="date"
          onClick={openPicker}
          value={end}
          min={start}
          max={max}
          onChange={(e) => e.target.value && onChange({ end: e.target.value })}
        />
      </div>

      <div className="pill" title="Latest forecast published by this time on the day before delivery is used">
        <Clock size={16} aria-hidden />
        <label htmlFor="cutoff">Cutoff</label>
        <input
          id="cutoff"
          type="time"
          value={cutoff}
          onClick={openPicker}
          onChange={(e) => e.target.value && onChange({ cutoff: e.target.value })} />
        <span className="pill-note">UK, D-1</span>
      </div>

      {!isDefault && (
        <button type="button" className="ghost-button" onClick={onReset}>
          <RotateCcw size={14} aria-hidden />
          Reset
        </button>
      )}
    </div>
  )
}
