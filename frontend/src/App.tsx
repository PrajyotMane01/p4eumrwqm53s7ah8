import { useEffect, useState } from 'react'

type Health = {
  status: string
  db: string
}

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/v1/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<Health>
      })
      .then(setHealth)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: 16 }}>
      <h1>Wind Forecast Monitor</h1>
      {error && <p>Backend unreachable: {error}</p>}
      {!error && !health && <p>Checking backend…</p>}
      {health && (
        <p>
          API: {health.status} · Database: {health.db}
        </p>
      )}
    </main>
  )
}

export default App
