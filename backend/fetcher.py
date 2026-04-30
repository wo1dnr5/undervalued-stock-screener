import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import os, pickle, time, warnings

warnings.filterwarnings("ignore")
requests.packages.urllib3.disable_warnings()  # SSL verify=False 경고 억제

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


# ── 유틸리티 ────────────────────────────────────────────────────────

def _cache_path(name):
    return os.path.join(CACHE_DIR, f"{name}_{datetime.now().strftime('%Y%m%d')}.pkl")

def _load_cache(name):
    p = _cache_path(name)
    if os.path.exists(p):
        try:
            with open(p, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    return None

def _save_cache(name, data):
    try:
        with open(_cache_path(name), "wb") as f:
            pickle.dump(data, f)
    except Exception:
        pass

def clear_all_cache():
    import glob
    for f in glob.glob(os.path.join(CACHE_DIR, "*.pkl")):
        try:
            os.remove(f)
        except Exception:
            pass

def _last_biz_date(offset=0):
    d = datetime.now() - timedelta(days=offset)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")

def _one_year_ago():
    return (datetime.now() - timedelta(days=380)).strftime("%Y%m%d")

def calculate_rsi(closes, period=14):
    if closes is None or len(closes) < period + 1:
        return None
    delta = closes.diff().dropna()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 1) if pd.notna(val) else None

def _week52_pct(closes):
    if closes is None or len(closes) < 5:
        return None
    current = float(closes.iloc[-1])
    high = float(closes.max())
    if high == 0:
        return None
    return round((current - high) / high * 100, 1)

def _ma200_gap(closes):
    if closes is None or len(closes) < 200:
        return None
    ma200 = float(closes.rolling(200).mean().iloc[-1])
    current = float(closes.iloc[-1])
    if ma200 == 0:
        return None
    return round((current - ma200) / ma200 * 100, 1)


# ── 한국 (KOSPI 상위 종목 - yfinance .KS) ──────────────────────────

KOSPI_TICKERS = [
    "005930.KS",  # 삼성전자
    "000660.KS",  # SK하이닉스
    "373220.KS",  # LG에너지솔루션
    "207940.KS",  # 삼성바이오로직스
    "005490.KS",  # POSCO홀딩스
    "035420.KS",  # NAVER
    "000270.KS",  # 기아
    "005380.KS",  # 현대차
    "051910.KS",  # LG화학
    "006400.KS",  # 삼성SDI
    "028260.KS",  # 삼성물산
    "055550.KS",  # 신한지주
    "105560.KS",  # KB금융
    "086790.KS",  # 하나금융지주
    "032830.KS",  # 삼성생명
    "096770.KS",  # SK이노베이션
    "017670.KS",  # SK텔레콤
    "030200.KS",  # KT
    "034730.KS",  # SK
    "018260.KS",  # 삼성SDS
    "009150.KS",  # 삼성전기
    "003550.KS",  # LG
    "012330.KS",  # 현대모비스
    "066570.KS",  # LG전자
    "011200.KS",  # HMM
    "035720.KS",  # 카카오
    "003490.KS",  # 대한항공
    "024110.KS",  # 기업은행
    "010130.KS",  # 고려아연
    "012450.KS",  # 한화에어로스페이스
    "009830.KS",  # 한화솔루션
    "247540.KS",  # 에코프로비엠
    "042700.KS",  # 한미반도체
    "011170.KS",  # 롯데케미칼
    "004020.KS",  # 롯데케미칼 우
    "361610.KS",  # SK아이이테크놀로지
    "139480.KS",  # 이마트
    "023530.KS",  # 롯데쇼핑
    "000100.KS",  # 유한양행
    "068270.KS",  # 셀트리온
    "326030.KS",  # SK바이오팜
    "180640.KS",  # 한화시스템
    "011780.KS",  # 금호석유
    "033780.KS",  # KT&G
    "004170.KS",  # 신세계
    "097950.KS",  # CJ제일제당
    "010950.KS",  # S-Oil
    "002380.KS",  # KCC
    "000810.KS",  # 삼성화재
    "071050.KS",  # 한국금융지주
]

def _fetch_yf_stock_kr(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        per = info.get("trailingPE") or info.get("forwardPE")
        pbr = info.get("priceToBook")
        roe_raw = info.get("returnOnEquity")

        hist = t.history(period="1y", auto_adjust=True)
        if hist.empty or len(hist) < 20:
            return None
        closes = hist["Close"]

        price = info.get("currentPrice") or info.get("regularMarketPrice") or float(closes.iloc[-1])

        return {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName", ticker),
            "price": round(float(price), 0),
            "PER": round(float(per), 1) if per and per > 0 else None,
            "PBR": round(float(pbr), 2) if pbr and pbr > 0 else None,
            "ROE": round(float(roe_raw) * 100, 1) if roe_raw else None,
            "RSI": calculate_rsi(closes),
            "52W_change": _week52_pct(closes),
            "MA200_gap": _ma200_gap(closes),
            "currency": "KRW",
        }
    except Exception:
        return None

def fetch_korea():
    cached = _load_cache("korea")
    if cached is not None:
        return cached

    records = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_fetch_yf_stock_kr, t): t for t in KOSPI_TICKERS}
        for future in as_completed(futures):
            result = future.result()
            if result:
                records.append(result)

    result = pd.DataFrame(records)
    _save_cache("korea", result)
    return result


# ── 미국 (S&P 500 + NASDAQ 100) ─────────────────────────────────────

# NASDAQ 100 고정 리스트 (Wikipedia SSL 실패 시 fallback)
_NASDAQ100_FALLBACK = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","TSLA","AVGO","COST",
    "NFLX","AMD","ADBE","QCOM","INTU","AMGN","PEP","AMAT","TXN","ISRG",
    "BKNG","HON","VRTX","REGN","MU","GILD","PANW","ADI","LRCX","MRVL",
    "KLAC","SNPS","CDNS","CTAS","MNST","MELI","ORLY","KDP","PAYX","AEP",
    "ABNB","ROST","FTNT","TEAM","NXPI","FAST","ODFL","MAR","DXCM","EXC",
    "XEL","IDXX","CPRT","FANG","ON","BKR","PCAR","KHC","VRSK","ANSS",
    "BIIB","ILMN","DDOG","ZS","CRWD","WDAY","TTWO","GEHC","CEG","SMCI",
    "TTD","CSGP","WBD","DLTR","CHTR","LULU","PYPL","EBAY","ZM","OKTA",
    "SGEN","RIVN","ALGN","ZBRA","TCOM","ASML","AZN","TMUS","LIN","CSX",
    "MDLZ","ROP","PDD","MCHP","WBA","CTSH","CDW","CCEP","GEHC","ARM",
]

def _html_tables(url):
    """SSL 인증서 검증 없이 Wikipedia HTML을 가져와 파싱."""
    resp = requests.get(
        url,
        verify=False,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    resp.raise_for_status()
    return pd.read_html(resp.text)

def _get_sp500_tickers():
    try:
        tables = _html_tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        table = tables[0]
        return table["Symbol"].str.replace(".", "-", regex=False).tolist()
    except Exception:
        return []

def _get_nasdaq100_tickers():
    try:
        tables = _html_tables("https://en.wikipedia.org/wiki/Nasdaq-100")
        for t in tables:
            if "Ticker" in t.columns:
                tickers = t["Ticker"].dropna().tolist()
                if len(tickers) > 50:
                    return tickers
    except Exception:
        pass
    return _NASDAQ100_FALLBACK

def _fetch_yf_stock(ticker, currency="USD"):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        per = info.get("trailingPE") or info.get("forwardPE")
        pbr = info.get("priceToBook")
        if not per or not pbr or per <= 0 or pbr <= 0:
            return None

        hist = t.history(period="1y", auto_adjust=True)
        if hist.empty or len(hist) < 20:
            return None
        closes = hist["Close"]

        roe_raw = info.get("returnOnEquity")
        roe = round(float(roe_raw) * 100, 1) if roe_raw else None

        return {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName", ticker),
            "price": round(float(closes.iloc[-1]), 2),
            "PER": round(float(per), 1),
            "PBR": round(float(pbr), 2),
            "ROE": roe,
            "RSI": calculate_rsi(closes),
            "52W_change": _week52_pct(closes),
            "MA200_gap": _ma200_gap(closes),
            "currency": currency,
        }
    except Exception:
        return None

def _fetch_batch(tickers, currency="USD", cache_name="us"):
    cached = _load_cache(cache_name)
    if cached is not None:
        return cached

    records = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_yf_stock, t, currency): t for t in tickers}
        for future in as_completed(futures):
            result = future.result()
            if result:
                records.append(result)

    df = pd.DataFrame(records)
    _save_cache(cache_name, df)
    return df

def fetch_sp500():
    return _fetch_batch(_get_sp500_tickers(), "USD", "sp500")

def fetch_nasdaq100():
    return _fetch_batch(_get_nasdaq100_tickers(), "USD", "nasdaq100")

def fetch_us():
    return fetch_sp500()


# ── 일본 (Nikkei 225) ───────────────────────────────────────────────

def _get_nikkei225_tickers():
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/Nikkei_225")
        for t in tables:
            for col in t.columns:
                vals = t[col].astype(str)
                matches = vals[vals.str.match(r"^\d{4}$")]
                if len(matches) > 100:
                    return [v + ".T" for v in matches.tolist()]
    except Exception:
        pass
    return [
        "7203.T", "6758.T", "9432.T", "9984.T", "6861.T",
        "8306.T", "7267.T", "4063.T", "9433.T", "8058.T",
        "6902.T", "4502.T", "7751.T", "8031.T", "4661.T",
        "8001.T", "8002.T", "8035.T", "7974.T", "9022.T",
        "4543.T", "6954.T", "4519.T", "8802.T", "9020.T",
        "7733.T", "8591.T", "4901.T", "3382.T", "2914.T",
    ]

def fetch_japan():
    cached = _load_cache("japan")
    if cached is not None:
        return cached

    tickers = _get_nikkei225_tickers()
    records = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_yf_stock, t, "JPY"): t for t in tickers}
        for future in as_completed(futures):
            result = future.result()
            if result:
                records.append(result)

    df = pd.DataFrame(records)
    _save_cache("japan", df)
    return df


# ── 중국 (CSI 300 주요 종목) ─────────────────────────────────────────

CSI300_TICKERS = [
    "600519.SS", "601318.SS", "600036.SS", "601166.SS", "600276.SS",
    "601398.SS", "601288.SS", "601988.SS", "600028.SS", "601857.SS",
    "601601.SS", "601628.SS", "600900.SS", "600016.SS", "601668.SS",
    "600030.SS", "601169.SS", "601328.SS", "601088.SS", "600104.SS",
    "600309.SS", "600585.SS", "601012.SS", "601899.SS", "601919.SS",
    "603501.SS", "600048.SS", "601800.SS", "600050.SS", "601211.SS",
    "000333.SZ", "000002.SZ", "300750.SZ", "002594.SZ", "000001.SZ",
    "002415.SZ", "300760.SZ", "000725.SZ", "002230.SZ", "000568.SZ",
    "000100.SZ", "300014.SZ", "002304.SZ", "000661.SZ", "002714.SZ",
    "000858.SZ", "300059.SZ", "002352.SZ", "300015.SZ", "001979.SZ",
]

def _fetch_yf_stock_cn(ticker):
    currency = "CNY" if (".SS" in ticker or ".SZ" in ticker) else "HKD"
    return _fetch_yf_stock(ticker, currency)

def fetch_china():
    cached = _load_cache("china")
    if cached is not None:
        return cached

    records = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_fetch_yf_stock_cn, t): t for t in CSI300_TICKERS}
        for future in as_completed(futures):
            result = future.result()
            if result:
                records.append(result)

    df = pd.DataFrame(records)
    _save_cache("china", df)
    return df
