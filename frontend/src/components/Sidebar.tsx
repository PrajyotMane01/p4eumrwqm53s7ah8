import { Database, LayoutDashboard, Target, Wind } from 'lucide-react'
import type { Coverage } from '../lib/api'
import { formatUkDateTime } from '../lib/ukTime'
import type { View } from '../lib/useFilters'

const NAV: { label: string; icon: typeof Wind; view?: View }[] = [
  { label: 'Day-ahead', icon: LayoutDashboard, view: 'day-ahead' },
  { label: 'Accuracy', icon: Target, view: 'accuracy' },
  { label: 'Data', icon: Database },
]

type Props = { coverage?: Coverage; view?: View; onNavigate?: (view: View) => void }

export function Sidebar({ coverage, view, onNavigate }: Props) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden>
          <Wind size={18} />
        </span>
        WindDesk
      </div>

      <nav className="nav" aria-label="Main">
        {NAV.map(({ label, icon: Icon, view: target }) =>
          target ? (
            <button
              key={label}
              type="button"
              className={`nav-item${view === target ? ' is-active' : ''}`}
              aria-current={view === target ? 'page' : undefined}
              onClick={() => onNavigate?.(target)}
            >
              <Icon size={18} />
              <span>{label}</span>
            </button>
          ) : (
            <span key={label} className="nav-item is-disabled" aria-disabled>
              <Icon size={18} />
              <span>{label}</span>
              <span className="soon">Soon</span>
            </span>
          ),
        )}
      </nav>

      <div className="source-card">
        <p className="source-title">Data source</p>
        <p>Elexon BMRS: FUELHH actuals and WINDFOR forecasts, GB national wind.</p>
        {coverage?.refreshed_at && <p className="source-meta">Loaded {formatUkDateTime(coverage.refreshed_at)} UK</p>}
      </div>
    </aside>
  )
}
