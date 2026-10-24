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

      <div className="source-card">
        <p className="source-title">Data source</p>
        <p>Elexon BMRS: FUELHH actuals and WINDFOR forecasts, GB national wind.</p>
        {coverage?.source === 'elexon' ? (
          <p className="source-meta">Live from Elexon: the database is unavailable, so data was fetched directly.</p>
        ) : (
          coverage?.refreshed_at && <p className="source-meta">Loaded {formatUkDateTime(coverage.refreshed_at)} UK</p>
        )}
      </div>

      <nav className="nav nav-footer" aria-label="Data">
        <NavButton label="Data" icon={Database} active={view === 'data'} onClick={() => onNavigate?.('data')} />
      </nav>
    </aside>
  )
}
