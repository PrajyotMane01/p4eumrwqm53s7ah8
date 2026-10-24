// All times in the app are shown in UK time, whatever the viewer's own time zone.

const UK = 'Europe/London'

const timeFormatter = new Intl.DateTimeFormat('en-GB', { timeZone: UK, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })

const dayFormatter = new Intl.DateTimeFormat('en-GB', { timeZone: UK, day: 'numeric', month: 'short' })

/**
 * Axis label for a moment in time, in UK time: the date at UK midnight, otherwise the time.
 * Points are placed by their real moment, so the repeated hour when clocks go back is
 * drawn in order rather than folded onto itself.
 */
export function formatUkAxisLabel(ms: number): string {
  const time = timeFormatter.format(ms)
  return time === '00:00' ? dayFormatter.format(ms) : time
}

const dateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: UK,
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})

const dateFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC', // inputs are plain dates
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

export const formatUkDateTime = (iso: string) => dateTimeFormatter.format(new Date(iso))

/** "2026-01-15" -> "15 Jan 2026" */
export const formatDate = (isoDate: string) => dateFormatter.format(new Date(`${isoDate}T00:00:00Z`))
