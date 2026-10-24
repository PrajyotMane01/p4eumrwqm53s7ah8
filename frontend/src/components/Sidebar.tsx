import { Database, LayoutDashboard, Target, Wind } from 'lucide-react'
import type { Coverage } from '../lib/api'
import { formatUkDateTime } from '../lib/ukTime'
import type { View } from '../lib/useFilters'

const NAV: { label: string; icon: typeof Wind; view: View }[] = [
  { label: 'Day-ahead', icon: LayoutDashboard, view: 'day-ahead' },
  { label: 'Accuracy', icon: Target, view: 'accuracy' },
]

type Props = { coverage?: Coverage; view?: View; onNavigate?: (view: View) => void }

type NavButtonProps = { label: string; icon: typeof Wind; active: boolean; onClick: () => void }

/** Where the data on screen comes from: the database, or the live Elexon API fallback. */
function SourceStatus({ coverage }: { coverage: Coverage }) {
  const live = coverage.source === 'elexon'
  return (
    <div className={`source-status${live ? ' is-live' : ''}`} role="status">
      <span className="source-dot" aria-hidden />
      <div>
        <p className="source-status-title">{live ? 'Live Elexon API' : `Database · ${coverage.database}`}</p>
        <p className="source-status-meta">
          {live
            ? 'Fallback: the database is unavailable'
            : coverage.refreshed_at
              ? `Loaded ${formatUkDateTime(coverage.refreshed_at)} UK`
              : 'Serving stored data'}
        </p>
      </div>
    </div>
  )
}

function NavButton({ label, icon: Icon, active, onClick }: NavButtonProps) {
  return (
    <button
      type="button"
      className={`nav-item${active ? ' is-active' : ''}`}
      aria-current={active ? 'page' : undefined}
      onClick={onClick}
    >
      <Icon size={18} />
      <span>{label}</span>
    </button>
  )
}

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
        {NAV.map(({ label, icon, view: target }) => (
          <NavButton key={label} label={label} icon={icon} active={view === target} onClick={() => onNavigate?.(target)} />
        ))}
      </nav>

      <div className="sidebar-footer">
        {coverage && <SourceStatus coverage={coverage} />}
        <nav className="nav" aria-label="Data">
          <NavButton label="Data" icon={Database} active={view === 'data'} onClick={() => onNavigate?.('data')} />
        </nav>
      </div>
    </aside>
  )
}
