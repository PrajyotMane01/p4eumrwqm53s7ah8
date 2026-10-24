import { useCallback, useSyncExternalStore } from 'react'

// Filters live in the URL so any view can be bookmarked or shared.

// Our own updates use replaceState, which fires no event, so we announce them with this one
const URL_CHANGE = 'urlstatechange'

const subscribe = (onChange: () => void) => {
  window.addEventListener('popstate', onChange) // back and forward buttons
  window.addEventListener(URL_CHANGE, onChange)
  return () => {
    window.removeEventListener('popstate', onChange)
    window.removeEventListener(URL_CHANGE, onChange)
  }
}

const getSearch = () => window.location.search

export function useUrlState<K extends string>(keys: readonly K[]) {
  const search = useSyncExternalStore(subscribe, getSearch)
  const params = new URLSearchParams(search)
  const values = Object.fromEntries(keys.map((k) => [k, params.get(k)])) as Record<K, string | null>

  /**
   * Set or, with an empty string, remove params. By default the history entry is replaced, so
   * editing a filter does not fill up Back; pass `push` for moves the user may want to undo.
   */
  const setValues = useCallback((next: Partial<Record<K, string>>, { push = false } = {}) => {
    const updated = new URLSearchParams(window.location.search)
    for (const [key, value] of Object.entries(next)) {
      if (value) updated.set(key, value as string)
      else updated.delete(key)
    }
    // Colons are valid in a query string; keep them readable (cutoff=09:20, not 09%3A20)
    const query = updated.toString().replace(/%3A/gi, ':')
    const target = query ? `?${query}` : window.location.pathname
    if (push) window.history.pushState(null, '', target)
    else window.history.replaceState(null, '', target)
    window.dispatchEvent(new Event(URL_CHANGE))
  }, [])

  return [values, setValues] as const
}
