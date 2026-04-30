# 글로벌 저평가 주식 스크리너

PER · PBR · ROE · RSI · 52주 고점 대비 · 200일 이평선 기준으로 한국·미국·중국·일본 주요 지수에서 저평가 종목을 실시간으로 탐색하는 풀스택 웹 애플리케이션입니다.

![Tech Stack](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)
![Tech Stack](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB?style=flat-square&logo=react)
![Tech Stack](https://img.shields.io/badge/Data-yfinance-blueviolet?style=flat-square)
![Tech Stack](https://img.shields.io/badge/Style-Tailwind%20CSS-06B6D4?style=flat-square&logo=tailwindcss)

---

## 주요 기능

- **5개 시장 탭**: 한국(KOSPI), S&P 500, NASDAQ 100, 중국(CSI 300), 일본(Nikkei 225)
- **6가지 지표 필터**: PER / PBR / ROE / RSI / 52주 고점 대비 / 200일 이평선 괴리율
- **멀티팩터 저평가 점수**: PER(25%) + PBR(20%) + ROE(20%) + RSI(20%) + 52주 변동(15%) 가중 합산
- **프론트엔드 실시간 필터링**: 슬라이더 조정 즉시 반영 (API 재호출 없음)
- **TradingView 연동**: 종목 행 클릭 시 해당 종목 차트 페이지로 이동
- **일별 캐싱**: 동일 날짜 내 재실행 시 캐시에서 즉시 응답 (yfinance API 부하 최소화)
- **새로고침 버튼**: 캐시 초기화 후 최신 데이터 재수집

---

## 기술 스택

### 백엔드
| 구성요소 | 기술 |
|---|---|
| API 프레임워크 | FastAPI + Uvicorn |
| 주가 데이터 | yfinance (Yahoo Finance) |
| 데이터 처리 | pandas, numpy |
| 병렬 수집 | ThreadPoolExecutor |
| 캐싱 | 파일 기반 pickle (일별) |
| 지수 구성종목 | Wikipedia HTML 스크래핑 (requests) |

### 프론트엔드
| 구성요소 | 기술 |
|---|---|
| UI 프레임워크 | React 18 + TypeScript |
| 빌드 도구 | Vite |
| 스타일 | Tailwind CSS |
| 상태 관리 | React hooks (useState, useMemo, useCallback) |
| API 통신 | fetch + AbortController |

---

## 프로젝트 구조

```
undervalued_stock/
├── backend/
│   ├── api.py            # FastAPI 앱 (라우터 정의)
│   ├── fetcher.py        # 국가별 주가 데이터 수집 (yfinance)
│   ├── screener.py       # 백엔드 필터/스코어 유틸 (참고용)
│   └── requirements.txt  # Python 의존성
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # 루트 컴포넌트 (탭 + 필터 상태)
│   │   ├── screener.ts                # 프론트엔드 필터링 + 점수 계산
│   │   ├── types.ts                   # TypeScript 타입 정의
│   │   ├── hooks/
│   │   │   └── useStocks.ts           # 데이터 페칭 커스텀 훅
│   │   └── components/
│   │       ├── FilterPanel.tsx        # 슬라이더 필터 패널
│   │       ├── StockTable.tsx         # 종목 테이블 + 정렬
│   │       └── ScoreBar.tsx           # 저평가 점수 바
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
└── BUYING_GUIDE.md       # 저평가 매수 기준 가이드 (퀀트 트레이더 관점)
```

---

## 커버리지 (수집 종목)

| 시장 | 지수 | 종목 수 |
|---|---|---|
| 🇰🇷 한국 | KOSPI 상위 50 | ~50개 |
| 🇺🇸 미국 | S&P 500 | ~500개 |
| 🇺🇸 미국 | NASDAQ 100 | ~100개 |
| 🇨🇳 중국 | CSI 300 주요 50 | ~50개 |
| 🇯🇵 일본 | Nikkei 225 | ~225개 |

---

## 설치 및 실행

### 사전 요구사항

- Python 3.10+
- Node.js 18+

### 백엔드 실행

```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

> **macOS SSL 이슈**: yfinance 및 Wikipedia 스크래핑이 SSL 인증서 오류를 겪는 경우, fetcher.py 내 `requests.get(verify=False)` 설정이 자동으로 우회합니다.

### 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 접속

---

## 동작 방식

### 데이터 흐름

```
[yfinance / Wikipedia]
        ↓
[fetcher.py] ThreadPoolExecutor로 병렬 수집
        ↓
[cache/] 파일 캐싱 (당일 재실행 시 즉시 반환)
        ↓
[api.py] GET /api/stocks/{country} → JSON 응답
        ↓
[useStocks.ts] React 훅으로 데이터 수신
        ↓
[screener.ts] 프론트엔드에서 필터링 + 점수 계산
        ↓
[StockTable.tsx] 테이블 렌더링 + 정렬
```

### 저평가 점수 계산

| 지표 | 가중치 | 방향 |
|---|---|---|
| PER | 25% | 낮을수록 유리 |
| PBR | 20% | 낮을수록 유리 |
| ROE | 20% | 높을수록 유리 |
| RSI | 20% | 낮을수록 유리 |
| 52주 고점 대비 | 15% | 낮을수록 유리 (더 많이 하락) |

각 지표를 0–100으로 정규화 후 가중 합산. 점수가 높을수록 더 저평가된 종목.

### 필터 기본값

| 필터 | 기본값 | 의미 |
|---|---|---|
| PER 최대 | 500 | PER 500 이하만 표시 |
| PBR 최대 | 20 | PBR 20 이하만 표시 |
| ROE 최소 | -20% | ROE -20% 이상만 표시 |
| RSI 최대 | 50 | RSI 50 이하 (과매도 구간) |
| 52주 고점 대비 | -10% | 고점에서 10% 이상 하락 |

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/stocks/{country}` | 국가별 종목 데이터 반환 (`kr`, `sp500`, `nasdaq`, `cn`, `jp`) |
| DELETE | `/api/cache` | 캐시 전체 삭제 (새로고침 트리거) |
| GET | `/api/health` | 서버 상태 확인 |

### 응답 형식

```json
{
  "stocks": [
    {
      "ticker": "005930.KS",
      "name": "Samsung Electronics Co., Ltd.",
      "price": 54000,
      "PER": 12.3,
      "PBR": 1.1,
      "ROE": 8.5,
      "RSI": 42.1,
      "52W_change": -18.5,
      "MA200_gap": -5.2,
      "currency": "KRW"
    }
  ],
  "total": 48
}
```

---

## TradingView 연동

종목 행 클릭 시 해당 거래소에 맞는 TradingView 차트로 이동합니다.

| 접미사 | 거래소 | TradingView 심볼 |
|---|---|---|
| `.KS` | 한국거래소 | `KRX:XXXXXX` |
| `.T` | 도쿄증권거래소 | `TSE:XXXX` |
| `.SS` | 상하이증권거래소 | `SSE:XXXXXX` |
| `.SZ` | 선전증권거래소 | `SZSE:XXXXXX` |
| `.HK` | 홍콩거래소 | `HKEX:XXXX` |
| (없음) | 미국 | `TICKER` |

---

## 매수 기준 가이드

퀀트 트레이더 관점의 상세한 매수 기준은 [BUYING_GUIDE.md](./BUYING_GUIDE.md)를 참고하세요.

- 국가별 저평가 기준 (PER/PBR/ROE 목표값)
- 5단계 체계적 매수 프레임워크
- 포지션 사이징 규칙 (A등급 5–8%, B등급 3–5%)
- 손절/익절 기준 (-12% 하드 스탑, +15%/+25%/+40% 단계적 익절)
- 2026년 4월 현재 시장 환경 분석 및 국가 우선순위

---

## 주의사항

- 본 프로젝트는 **투자 정보 제공 목적**이며 투자 권유가 아닙니다.
- yfinance는 Yahoo Finance의 비공식 API로, 데이터 누락 또는 지연이 발생할 수 있습니다.
- 실시간 시세가 아닌 **장 마감 기준 데이터**를 사용합니다.
- 모든 투자 결정은 본인의 책임 하에 이루어져야 합니다.

---

## 라이선스

MIT License
