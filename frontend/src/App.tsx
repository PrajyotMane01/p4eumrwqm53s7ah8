import { useQuery } from '@tanstack/react-query'
import { DayAheadPage } from './components/DayAheadPage'
import { Sidebar } from './components/Sidebar'
import { fetchCoverage } from './lib/api'

function App() {
  const coverage = useQuery({ queryKey: ['coverage'], queryFn: fetchCoverage, staleTime: 5 * 60 * 1000 })

  return (
    <div className="layout">
      <Sidebar coverage={coverage.data} />
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
        {coverage.data && !coverage.data.first_date && (
          <section className="card notice">No data loaded yet. Run the ingest refresh command first.</section>
        )}
        {coverage.data?.first_date && coverage.data.last_date && (
          <DayAheadPage
            coverage={{ ...coverage.data, first_date: coverage.data.first_date, last_date: coverage.data.last_date }}
          />
        )}
      </main>
    </div>
  )
}

export default App
