import type { LucideIcon } from 'lucide-react'

type Props = {
  label: string
  value: string
  detail?: string
  icon: LucideIcon
  highlight?: boolean
}

export function StatCard({ label, value, detail, icon: Icon, highlight }: Props) {
  return (
    <section className={`card stat-card${highlight ? ' is-highlight' : ''}`}>
      <div className="stat-head">
        <span className="stat-label">{label}</span>
        <span className="icon-chip" aria-hidden>
          <Icon size={16} />
        </span>
      </div>
      <p className="stat-value">{value}</p>
      {detail && <p className="stat-detail">{detail}</p>}
    </section>
  )
}
