import { Stock, Filters } from './types'

export function applyFilters(stocks: Stock[], f: Filters): Stock[] {
  return stocks.filter(s => {
    // 값이 null이면 해당 항목은 필터 통과 (데이터 없음 = 필터 적용 불가)
    if (s.PER !== null && (s.PER <= 0 || s.PER > f.per_max)) return false
    if (s.PBR !== null && (s.PBR <= 0 || s.PBR > f.pbr_max)) return false
    if (s.ROE !== null && s.ROE < f.roe_min) return false
    if (s.RSI !== null && s.RSI > f.rsi_max) return false
    if (s['52W_change'] !== null && s['52W_change'] > f.w52_min) return false
    // PER은 필수: 아예 없으면 제외
    if (s.PER === null) return false
    return true
  })
}

function normalize(values: number[], higherIsBetter: boolean): number[] {
  const min = Math.min(...values)
  const max = Math.max(...values)
  if (max === min) return values.map(() => 50)
  return values.map(v => {
    const n = ((v - min) / (max - min)) * 100
    return higherIsBetter ? n : 100 - n
  })
}

const WEIGHTS: { key: keyof Stock; weight: number; higherIsBetter: boolean }[] = [
  { key: 'PER',        weight: 0.25, higherIsBetter: false },
  { key: 'PBR',        weight: 0.20, higherIsBetter: false },
  { key: 'ROE',        weight: 0.20, higherIsBetter: true  },
  { key: 'RSI',        weight: 0.20, higherIsBetter: false },
  { key: '52W_change', weight: 0.15, higherIsBetter: false },
]

export function calculateScores(stocks: Stock[]): (Stock & { score: number })[] {
  if (stocks.length === 0) return []

  const scores = new Array(stocks.length).fill(0)

  for (const { key, weight, higherIsBetter } of WEIGHTS) {
    const vals = stocks.map(s => s[key] as number | null)
    const valids = vals.filter((v): v is number => v !== null)
    if (valids.length < 2) continue

    const normed = normalize(valids, higherIsBetter)
    let ni = 0
    for (let i = 0; i < stocks.length; i++) {
      if (vals[i] !== null) {
        scores[i] += normed[ni++] * weight
      }
    }
  }

  return stocks.map((s, i) => ({ ...s, score: Math.round(scores[i] * 10) / 10 }))
}
