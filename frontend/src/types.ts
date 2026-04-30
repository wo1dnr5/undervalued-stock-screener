export interface Stock {
  ticker: string
  name: string
  price: number | null
  PER: number | null
  PBR: number | null
  ROE: number | null
  RSI: number | null
  '52W_change': number | null
  MA200_gap: number | null
  currency: string
  score?: number
}

export interface StockResponse {
  stocks: Stock[]
  total: number
}

export interface Filters {
  per_max: number
  pbr_max: number
  roe_min: number
  rsi_max: number
  w52_min: number
}

export type SortKey = keyof Stock
export type SortDir = 'asc' | 'desc'
