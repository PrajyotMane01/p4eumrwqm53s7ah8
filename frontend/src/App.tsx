import { useQuery } from '@tanstack/react-query'
import { AccuracyPage } from './components/AccuracyPage'
import { DataPage } from './components/DataPage'
import { DayAheadPage } from './components/DayAheadPage'
import { PageHeader } from './components/PageHeader'
import { Sidebar } from './components/Sidebar'
import { fetchCoverage } from './lib/api'
import { type LoadedCoverage, useFilters } from './lib/useFilters'

const PAGES = {
  'day-ahead': {
    title: 'Day-ahead wind',
    subtitle: 'GB national wind generation against the forecast available at the decision cutoff. All times UK.',
  },
  accuracy: {
    title: 'Forecast accuracy',
    subtitle: 'How far the day-ahead forecast was from actual output. Error is forecast minus actual.',
  },
  data: {
    title: 'Data',
    subtitle: 'What is loaded, where it comes from, and how complete it is.',
  },
}

function Workspace({ coverage }: { coverage: LoadedCoverage }) {
  const { view, filters, isDefault, setFilters, resetFilters, setView, openDay } = useFilters(coverage)
  const page = PAGES[view]
  return (
    <div className="layout">
      <Sidebar coverage={coverage} view={view} onNavigate={setView} />
      <main className="main">
        <PageHeader
          {...page}
          showFilters={view !== 'data'}
          filters={filters}
          defaultCutoff={coverage.default_cutoff.slice(0, 5)}
          min={coverage.first_date}
          max={coverage.last_date}
          isDefault={isDefault}
          onChange={setFilters}
          onReset={resetFilters}
        />
        {view === 'accuracy' && <AccuracyPage filters={filters} onOpenDay={openDay} />}
        {view === 'data' && <DataPage />}
        {view === 'day-ahead' && <DayAheadPage filters={filters} />}
      </main>
    </div>
  )
}

function App() {
  const coverage = useQuery({ queryKey: ['coverage'], queryFn: fetchCoverage, staleTime: 5 * 60 * 1000 })
  const data = coverage.data

  if (data?.first_date && data.last_date) {
    return <Workspace coverage={{ ...data, first_date: data.first_date, last_date: data.last_date }} />
  }
  return (
    <div className="layout">
      <Sidebar coverage={data} />
      <main className="main">
        {coverage.isPending && <div className="card notice">Loading…</div>}
        {coverage.isError && (
          <section className="card notice is-error" role="alert">
            <p>Backend unreachable: {coverage.error.message}</p>
            <button type="button" className="ghost-button" onClick={() => coverage.refetch()}>
              Try again
            </button>
          </section>
        )}
        {data && !data.first_date && (
          <section className="card notice">No data loaded yet. Run the ingest refresh command first.</section>
        )}
      </main>
    </div>
  )
}

export default App
