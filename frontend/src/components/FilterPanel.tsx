import { Filters } from '../types'

interface Props {
  filters: Filters
  onChange: (f: Filters) => void
  onRefresh: () => void
  loading: boolean
}

function Slider({
  label, desc, value, min, max, step, onChange,
}: {
  label: string; desc: string; value: number
  min: number; max: number; step: number
  onChange: (v: number) => void
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{label}</span>
        <span className="text-sm font-bold text-gray-800 tabular-nums">{value}</span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer accent-blue-500 bg-gray-200"
      />
      <span className="text-[11px] text-gray-400">{desc}</span>
    </div>
  )
}

export default function FilterPanel({ filters, onChange, onRefresh, loading }: Props) {
  const set = (key: keyof Filters) => (v: number) => onChange({ ...filters, [key]: v })

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm px-6 py-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-sm font-semibold text-gray-800">필터</h2>
          <p className="text-xs text-gray-400 mt-0.5">슬라이더 조정 시 즉시 반영</p>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <span className={loading ? 'animate-spin inline-block' : ''}>↺</span>
          {loading ? '수집 중...' : '새로고침'}
        </button>
      </div>

      <div className="grid grid-cols-5 gap-6">
        <Slider
          label="PER 최대" desc={`PER ${filters.per_max} 이하`}
          value={filters.per_max} min={5} max={500} step={5}
          onChange={set('per_max')}
        />
        <Slider
          label="PBR 최대" desc={`PBR ${filters.pbr_max} 이하`}
          value={filters.pbr_max} min={0.5} max={20} step={0.5}
          onChange={set('pbr_max')}
        />
        <Slider
          label="ROE 최소 (%)" desc={`ROE ${filters.roe_min}% 이상`}
          value={filters.roe_min} min={-50} max={50} step={1}
          onChange={set('roe_min')}
        />
        <Slider
          label="RSI 최대" desc={`RSI ${filters.rsi_max} 이하`}
          value={filters.rsi_max} min={10} max={100} step={1}
          onChange={set('rsi_max')}
        />
        <Slider
          label="52주 최대 하락 (%)" desc={`고점 대비 ${filters.w52_min}% 이하`}
          value={filters.w52_min} min={-80} max={0} step={5}
          onChange={set('w52_min')}
        />
      </div>
    </div>
  )
}
