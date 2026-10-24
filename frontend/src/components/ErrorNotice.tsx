export function ErrorNotice({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <section className="card notice is-error" role="alert">
      <p>Could not load data: {error.message}</p>
      <button type="button" className="ghost-button" onClick={onRetry}>
        Try again
      </button>
    </section>
  )
}
