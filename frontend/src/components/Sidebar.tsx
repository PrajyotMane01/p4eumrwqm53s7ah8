import { Database, LayoutDashboard, Target, Wind } from 'lucide-react'
import type { Coverage } from '../lib/api'
import { formatUkDateTime } from '../lib/ukTime'

const NAV = [
  { label: 'Day-ahead', icon: LayoutDashboard, active: true },
  { label: 'Accuracy', icon: Target, soon: true },
  { label: 'Data', icon: Database, soon: true },
]

export function Sidebar({ coverage }: { coverage?: Coverage }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden>
          <Wind size={18} />
        </span>
        WindDesk
      </div>

      <nav className="nav" aria-label="Main">
        {NAV.map(({ label, icon: Icon, active, soon }) => (
          <a
            key={label}
            className={`nav-item${active ? ' is-active' : ''}${soon ? ' is-disabled' : ''}`}
            aria-current={active ? 'page' : undefined}
            aria-disabled={soon || undefined}
            href={active ? '#' : undefined}
          >
            <Icon size={18} />
            <span>{label}</span>
            {soon && <span className="soon">Soon</span>}
          </a>
        ))}
      </nav>

      <div className="source-card">
        <p className="source-title">Data source</p>
        <p>Elexon BMRS: FUELHH actuals and WINDFOR forecasts, GB national wind.</p>
        {coverage?.refreshed_at && <p className="source-meta">Loaded {formatUkDateTime(coverage.refreshed_at)} UK</p>}
      </div>
    </aside>
  )
}
