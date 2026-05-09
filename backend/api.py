from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json, sys, os

sys.path.insert(0, os.path.dirname(__file__))
from fetcher import fetch_korea, fetch_sp500, fetch_nasdaq100, fetch_japan, fetch_china, clear_all_cache, clear_country_cache

app = FastAPI(title="저평가 주식 스크리너 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FETCHERS = {
    "kr":     fetch_korea,
    "sp500":  fetch_sp500,
    "nasdaq": fetch_nasdaq100,
    "cn":     fetch_china,
    "jp":     fetch_japan,
}

CACHE_NAME_MAP = {
    "kr":     "korea",
    "sp500":  "sp500",
    "nasdaq": "nasdaq100",
    "cn":     "china",
    "jp":     "japan",
}

@app.get("/api/stocks/{country}")
def get_stocks(country: str):
    # 필터링·점수 계산은 프론트엔드(screener.ts)에서 수행 — 여기서는 원본 데이터 그대로 반환
    fetcher = FETCHERS.get(country)
    if not fetcher:
        return JSONResponse(content={"stocks": [], "total": 0, "fetched_at": None})

    df, fetched_at = fetcher()
    if df is None or df.empty:
        return JSONResponse(content={"stocks": [], "total": 0, "fetched_at": None})

    stocks = json.loads(df.to_json(orient="records"))
    return JSONResponse(content={"stocks": stocks, "total": len(df), "fetched_at": fetched_at})

@app.delete("/api/cache")
def clear_cache(country: str = None):
    if country and country in CACHE_NAME_MAP:
        clear_country_cache(CACHE_NAME_MAP[country])
    else:
        clear_all_cache()
    return {"status": "cleared"}

@app.get("/api/health")
def health():
    return {"status": "ok"}
