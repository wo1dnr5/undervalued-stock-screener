from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json, sys, os

sys.path.insert(0, os.path.dirname(__file__))
from fetcher import fetch_korea, fetch_sp500, fetch_nasdaq100, fetch_japan, fetch_china, clear_all_cache

app = FastAPI(title="저평가 주식 스크리너 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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

@app.get("/api/stocks/{country}")
def get_stocks(country: str):
    fetcher = FETCHERS.get(country)
    if not fetcher:
        return JSONResponse(content={"stocks": [], "total": 0})

    df = fetcher()
    if df is None or df.empty:
        return JSONResponse(content={"stocks": [], "total": 0})

    # pandas to_json이 NaN → null 변환을 안전하게 처리함
    stocks = json.loads(df.to_json(orient="records"))
    return JSONResponse(content={"stocks": stocks, "total": len(df)})

@app.delete("/api/cache")
def clear_cache():
    clear_all_cache()
    return {"status": "cleared"}

@app.get("/api/health")
def health():
    return {"status": "ok"}
