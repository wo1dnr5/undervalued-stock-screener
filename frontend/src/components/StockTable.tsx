import { useState, useMemo } from 'react'
import { Filters, SortKey, SortDir } from '../types'
import { useStocks } from '../hooks/useStocks'
import { applyFilters, calculateScores } from '../screener'
import ScoreBar from './ScoreBar'

interface Props { country: string; filters: Filters; refreshKey: number }

const COLS = [
  { key: 'name',        label: '종목명',           align: 'left'  },
  { key: 'ticker',      label: '티커',             align: 'left'  },
  { key: 'price',       label: '현재가',           align: 'right' },
  { key: 'PER',         label: 'PER',              align: 'right' },
  { key: 'PBR',         label: 'PBR',              align: 'right' },
  { key: 'ROE',         label: 'ROE (%)',           align: 'right' },
  { key: 'RSI',         label: 'RSI',              align: 'right' },
  { key: '52W_change',  label: '52주 고점 대비',    align: 'right' },
  { key: 'MA200_gap',   label: '200일선 괴리',      align: 'right' },
  { key: 'score',       label: '저평가 점수',       align: 'left'  },
] as const

// ── TradingView URL 변환 ──────────────────────────────────────────
function toTvUrl(ticker: string): string {
  let symbol: string
  if (ticker.endsWith('.KS'))      symbol = `KRX:${ticker.slice(0, -3)}`
  else if (ticker.endsWith('.T'))  symbol = `TSE:${ticker.slice(0, -2)}`
  else if (ticker.endsWith('.SS')) symbol = `SSE:${ticker.slice(0, -3)}`
  else if (ticker.endsWith('.SZ')) symbol = `SZSE:${ticker.slice(0, -3)}`
  else if (ticker.endsWith('.HK')) symbol = `HKEX:${ticker.slice(0, -3)}`
  else                             symbol = ticker.replace(/-/g, '.')   // US: BRK-B → BRK.B
  return `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}`
}

// ── 색상 및 포맷 유틸 ────────────────────────────────────────────
function badge(val: number | null, good: (v: number) => boolean, ok: (v: number) => boolean) {
  if (val === null) return 'text-gray-300'
  if (good(val)) return 'text-emerald-600 font-semibold'
  if (ok(val))   return 'text-amber-500'
  return 'text-red-500'
}

function fmt(val: number | null, digits = 1, suffix = ''): React.ReactNode {
  if (val === null || val === undefined) return <span className="text-gray-200">—</span>
  return `${val.toFixed(digits)}${suffix}`
}

const CURRENCY_SYM: Record<string, string> = {
  KRW: '₩', USD: '$', JPY: '¥', CNY: '¥', HKD: 'HK$',
}

function fmtPrice(val: number | null, currency: string) {
  if (val === null) return '—'
  const sym = CURRENCY_SYM[currency] ?? ''
  return `${sym}${val.toLocaleString()}`
}

function Skeleton() {
  return (
    <tr className="border-b border-gray-50">
      {COLS.map(c => (
        <td key={c.key} className="px-4 py-3.5">
          <div className="h-3.5 rounded bg-gray-100 animate-pulse" style={{ width: c.key === 'name' ? '120px' : '60px' }} />
        </td>
      ))}
    </tr>
  )
}

export default function StockTable({ country, filters, refreshKey }: Props) {
  const { data, loading, error } = useStocks(country, refreshKey)
  const [sortKey, setSortKey] = useState<SortKey>('score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const processed = useMemo(() => {
    if (!data?.stocks) return []
    const filtered = applyFilters(data.stocks, filters)
    const scored = calculateScores(filtered)
    return scored.sort((a, b) => {
      const av = a[sortKey] as number | string | null
      const bv = b[sortKey] as number | string | null
      if (av === null || av === undefined) return 1
      if (bv === null || bv === undefined) return -1
      if (sortDir === 'asc') return av > bv ? 1 : -1
      return av < bv ? 1 : -1
    })
  }, [data, filters, sortKey, sortDir])

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key as SortKey); setSortDir('desc') }
  }

  const total = data?.total ?? 0

  return (
    <div>
      {/* 통계 + 클릭 안내 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4 text-sm">
          <span className="text-gray-400">전체 <strong className="text-gray-700">{total.toLocaleString()}</strong>개</span>
          <span className="text-gray-200">|</span>
          <span className="text-gray-400">
            조건 충족 <strong className="text-blue-600">{processed.length.toLocaleString()}</strong>개
          </span>
          {total > 0 && (
            <>
              <span className="text-gray-200">|</span>
              <span className="text-gray-400">
                통과율 <strong className="text-gray-700">{((processed.length / total) * 100).toFixed(1)}%</strong>
              </span>
            </>
          )}
        </div>
        <span className="text-[11px] text-gray-400 flex items-center gap-1">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
          행 클릭 시 TradingView 차트 열림
        </span>
      </div>

      {error && (
        <div className="py-12 text-center text-sm text-red-400 bg-red-50 rounded-xl">
          백엔드 서버에 연결할 수 없습니다. <code className="text-xs bg-red-100 px-1 rounded">uvicorn api:app --reload</code> 를 실행해 주세요.
        </div>
      )}

      {!error && (
        <div className="overflow-x-auto rounded-xl border border-gray-100">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50/80">
                {COLS.map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`px-4 py-3 text-[11px] font-semibold text-gray-400 uppercase tracking-wider cursor-pointer select-none hover:text-gray-600 transition-colors whitespace-nowrap ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                  >
                    {col.label}
                    {sortKey === col.key
                      ? <span className="ml-1 text-blue-400">{sortDir === 'asc' ? '↑' : '↓'}</span>
                      : <span className="ml-1 text-gray-200">↕</span>
                    }
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 7 }).map((_, i) => <Skeleton key={i} />)
                : processed.length === 0
                  ? (
                    <tr>
                      <td colSpan={COLS.length} className="py-20 text-center text-sm text-gray-400">
                        조건에 맞는 종목이 없습니다. 필터 값을 완화해 보세요.
                      </td>
                    </tr>
                  )
                  : processed.map((stock, i) => (
                    <tr
                      key={stock.ticker}
                      onClick={() => window.open(toTvUrl(stock.ticker), '_blank')}
                      className={`border-b border-gray-50 cursor-pointer group transition-colors ${i % 2 === 1 ? 'bg-gray-50/30' : 'bg-white'} hover:bg-blue-50 hover:shadow-[inset_3px_0_0_#3b82f6]`}
                    >
                      <td className="px-4 py-3.5 max-w-[180px]">
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-gray-900 truncate" title={stock.name}>
                            {stock.name}
                          </span>
                          <svg
                            className="w-3 h-3 text-gray-300 group-hover:text-blue-400 flex-shrink-0 transition-colors"
                            fill="none" stroke="currentColor" viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-gray-400">{stock.ticker}</td>
                      <td className="px-4 py-3.5 text-right font-medium text-gray-700 tabular-nums">
                        {fmtPrice(stock.price, stock.currency)}
                      </td>
                      <td className={`px-4 py-3.5 text-right tabular-nums ${badge(stock.PER, v => v < 10, v => v < 15)}`}>
                        {fmt(stock.PER)}
                      </td>
                      <td className={`px-4 py-3.5 text-right tabular-nums ${badge(stock.PBR, v => v < 1, v => v < 1.5)}`}>
                        {fmt(stock.PBR, 2)}
                      </td>
                      <td className={`px-4 py-3.5 text-right tabular-nums ${badge(stock.ROE, v => v >= 20, v => v >= 10)}`}>
                        {fmt(stock.ROE)}
                      </td>
                      <td className={`px-4 py-3.5 text-right tabular-nums ${badge(stock.RSI, v => v < 30, v => v < 40)}`}>
                        {fmt(stock.RSI)}
                      </td>
                      <td className={`px-4 py-3.5 text-right tabular-nums ${badge(stock['52W_change'], v => v < -30, v => v < -20)}`}>
                        {fmt(stock['52W_change'], 1, '%')}
                      </td>
                      <td className="px-4 py-3.5 text-right tabular-nums text-gray-500">
                        {fmt(stock.MA200_gap, 1, '%')}
                      </td>
                      <td className="px-4 py-3.5 w-36 min-w-[140px]">
                        <ScoreBar score={stock.score ?? 0} />
                      </td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
