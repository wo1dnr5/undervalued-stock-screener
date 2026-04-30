import { useState, useEffect, useRef } from 'react'
import { StockResponse } from '../types'

export function useStocks(country: string, refreshKey: number) {
  const [data, setData] = useState<StockResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    setLoading(true)
    setError(null)

    fetch(`/api/stocks/${country}`, { signal: ctrl.signal })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(d => { setData(d); setLoading(false) })
      .catch(e => {
        if (e.name !== 'AbortError') {
          setError(e.message)
          setLoading(false)
        }
      })

    return () => ctrl.abort()
  }, [country, refreshKey])

  return { data, loading, error }
}
