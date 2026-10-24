import { CalendarDays, ChevronLeft, ChevronRight, Clock, RotateCcw } from 'lucide-react'
import type { MouseEvent } from 'react'
import { addDays, MAX_RANGE_DAYS } from '../lib/filters'
import { formatDayLong } from '../lib/ukTime'

// Open the native picker on any click, not only on the browser's small icon
const openPicker = (e: MouseEvent<HTMLInputElement>) => e.currentTarget.showPicker?.()

const WEEK_DAYS = 7

type Props = {
  start: string
  end: string
  cutoff: string
  defaultCutoff: string
  min: string
  max: string
  isDefault: boolean
  onChange: (next: { start?: string; end?: string; cutoff?: string }) => void
  onReset: () => void
}

// ISO dates compare correctly as strings
const earliest = (a: string, b: string) => (a < b ? a : b)
const latest = (a: string, b: string) => (a > b ? a : b)

/** A week from `start`, or the last week of the data when that would run past the end. */
function weekFrom(start: string, min: string, max: string) {
  const end = addDays(start, WEEK_DAYS - 1)
  return end <= max ? { start, end } : { start: latest(min, addDays(max, -(WEEK_DAYS - 1))), end: max }
}

export function Filters({ start, end, cutoff, defaultCutoff, min, max, isDefault, onChange, onReset }: Props) {
  const singleDay = start === end
  const setDay = (day: string) => onChange({ start: day, end: day })
  const fullPeriod = { start: min, end: earliest(max, addDays(min, MAX_RANGE_DAYS - 1)) }

  return (
    <div className="filters" role="group" aria-label="Filters">
      <div className="segmented" role="radiogroup" aria-label="Show one day or a range">
        <button type="button" role="radio" aria-checked={singleDay} className={singleDay ? 'is-on' : ''} onClick={() => setDay(start)}>
          Day
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={!singleDay}
          className={!singleDay ? 'is-on' : ''}
          onClick={() => singleDay && onChange(weekFrom(start, min, max))}
        >
          Range
        </button>
      </div>

      {singleDay ? (
        <div className="pill day-stepper">
          <button
            type="button"
            className="step"
            aria-label="Previous day"
            disabled={start <= min}
            onClick={() => setDay(addDays(start, -1))}
          >
            <ChevronLeft size={16} />
          </button>
          <label className="day-label">
            <CalendarDays size={16} aria-hidden />
            <span>{formatDayLong(start)}</span>
            <input
              className="day-input"
              type="date"
              aria-label="Delivery day"
              value={start}
              min={min}
              max={max}
              onClick={openPicker}
              onChange={(e) => e.target.value && setDay(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="step"
            aria-label="Next day"
            disabled={start >= max}
            onClick={() => setDay(addDays(start, 1))}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      ) : (
        <>
          <div className="pill">
            <CalendarDays size={16} aria-hidden />
            <label className="sr-only" htmlFor="start">
              First delivery day
            </label>
            <input
              id="start"
              type="date"
              value={start}
              min={min}
              max={max}
              onClick={openPicker}
              onChange={(e) =>
                e.target.value && onChange({ start: e.target.value, end: e.target.value > end ? e.target.value : end })
              }
            />
            <span aria-hidden>–</span>
            <label className="sr-only" htmlFor="end">
              Last delivery day
            </label>
            <input
              id="end"
              type="date"
              value={end}
              min={start}
              max={max}
              onClick={openPicker}
              onChange={(e) => e.target.value && onChange({ end: e.target.value })}
            />
          </div>
          <div className="chips" aria-label="Range presets">
            <button type="button" className="chip" onClick={() => onChange(weekFrom(start, min, max))}>
              7 days
            </button>
            <button
              type="button"
              className={`chip${start === fullPeriod.start && end === fullPeriod.end ? ' is-on' : ''}`}
              onClick={() => onChange(fullPeriod)}
            >
              Full period
            </button>
          </div>
        </>
      )}

      <div className="pill" title="The latest forecast published by this time on the day before delivery is used">
        <Clock size={16} aria-hidden />
        <label htmlFor="cutoff">Cutoff</label>
        <input id="cutoff" type="time" value={cutoff} onClick={openPicker} onChange={(e) => e.target.value && onChange({ cutoff: e.target.value })} />
        <span className="pill-note">UK, D-1</span>
      </div>
      {cutoff !== defaultCutoff && (
        <button type="button" className="chip" onClick={() => onChange({ cutoff: defaultCutoff })} title="Nord Pool N2EX day-ahead gate closure">
          {defaultCutoff} · N2EX
        </button>
      )}

      {!isDefault && (
        <button type="button" className="ghost-button" onClick={onReset}>
          <RotateCcw size={14} aria-hidden />
          Reset
        </button>
      )}
    </div>
  )
}
