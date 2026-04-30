import { useState, useCallback } from 'react'
import FilterPanel from './components/FilterPanel'
import StockTable from './components/StockTable'
import { Filters } from './types'

const COUNTRIES = [
  { key: 'kr',     flag: '🇰🇷', label: '한국',        subtitle: 'KOSPI 200' },
  { key: 'sp500',  flag: '🇺🇸', label: 'S&P 500',     subtitle: '미국 대형주 500' },
  { key: 'nasdaq', flag: '🇺🇸', label: 'NASDAQ 100',  subtitle: '미국 기술주 100' },
  { key: 'cn',     flag: '🇨🇳', label: '중국',        subtitle: 'CSI 300' },
  { key: 'jp',     flag: '🇯🇵', label: '일본',        subtitle: 'Nikkei 225' },
]

const DEFAULT_FILTERS: Filters = {
  per_max: 500,
  pbr_max: 20,
  roe_min: -20,
  rsi_max: 50,
  w52_min: -10,
}

export default function App() {
  const [activeTab, setActiveTab] = useState('kr')
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [refreshKey, setRefreshKey] = useState(0)
  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await fetch('/api/cache', { method: 'DELETE' })
    } finally {
      setRefreshKey(k => k + 1)
      setRefreshing(false)
    }
  }, [])

  return (
    <div className="min-h-screen bg-[#f0f2f5]">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-20 shadow-sm">
        <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">📊</span>
            <div>
              <h1 className="text-base font-bold text-gray-900 leading-tight">글로벌 저평가 주식 스크리너</h1>
              <p className="text-[11px] text-gray-400">PER · PBR · ROE · RSI · 52주 고점 대비 · 200일 이평선</p>
            </div>
          </div>
          <span className="text-xs text-gray-400">
            {new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })} 기준
          </span>
        </div>
      </header>

      <main className="max-w-screen-xl mx-auto px-6 py-6 space-y-4">
        {/* Filter */}
        <FilterPanel
          filters={filters}
          onChange={setFilters}
          onRefresh={handleRefresh}
          loading={refreshing}
        />

        {/* Card */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-gray-100">
            {COUNTRIES.map(c => (
              <button
                key={c.key}
                onClick={() => setActiveTab(c.key)}
                className={`flex items-center gap-2.5 px-6 py-4 transition-colors border-b-2 ${
                  activeTab === c.key ? 'tab-active' : 'tab-inactive'
                }`}
              >
                <span className="text-xl leading-none">{c.flag}</span>
                <div className="text-left">
                  <div className="text-sm font-semibold leading-tight">{c.label}</div>
                  <div className="text-[11px] text-gray-400 font-normal">{c.subtitle}</div>
                </div>
              </button>
            ))}
          </div>

          {/* Table */}
          <div className="p-6">
            <StockTable
              key={activeTab}
              country={activeTab}
              filters={filters}
              refreshKey={refreshKey}
            />
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-6 px-1 text-[11px] text-gray-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> 매우 양호
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" /> 보통
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> 주의
          </span>
          <span className="ml-auto">데이터 출처: KRX · Yahoo Finance · 당일 캐싱</span>
        </div>
      </main>
    </div>
  )
}
