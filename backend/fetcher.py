import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import os, pickle, time, warnings

warnings.filterwarnings("ignore")
requests.packages.urllib3.disable_warnings()

# yfinance 1.x 와 0.2.x 모두 지원
try:
    from yfinance.exceptions import YFRateLimitError
except ImportError:
    YFRateLimitError = Exception

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


# ── 캐시 유틸 ────────────────────────────────────────────────────────

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


# ── 지표 계산 ────────────────────────────────────────────────────────

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


# ── yfinance 공통 페치 (배치 download + 순차 info) ─────────────────

def _yf_session():
    """Yahoo Finance 크럼/쿠키를 획득해 requests 세션을 반환."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://finance.yahoo.com/",
    })
    try:
        s.get("https://finance.yahoo.com/quote/AAPL", timeout=10, verify=False)
    except Exception:
        pass
    return s

_SESSION = None

def _get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = _yf_session()
    return _SESSION


def _get_info_safe(ticker_str, retries=3):
    """단일 티커 info 조회. 429/RateLimit 시 재시도."""
    for attempt in range(retries):
        try:
            t = yf.Ticker(ticker_str)
            info = t.info
            if not info or len(info) < 5:
                return {}
            return info
        except YFRateLimitError:
            time.sleep(15 * (attempt + 1))
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "too many" in msg or "rate" in msg:
                time.sleep(15 * (attempt + 1))
            else:
                return {}
    return {}


def _download_closes(tickers, period="1y"):
    """yf.download() 로 배치 종가 데이터 획득. MultiIndex 처리."""
    for attempt in range(3):
        try:
            raw = yf.download(
                tickers,
                period=period,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if raw is None or raw.empty:
                return {}
            # MultiIndex(Close, Ticker) → dict
            if isinstance(raw.columns, pd.MultiIndex):
                close = raw["Close"]
            else:
                # 단일 티커: 컬럼이 OHLCV
                close = raw[["Close"]] if "Close" in raw.columns else raw
                close.columns = [tickers[0]] if len(tickers) == 1 else tickers
            result = {}
            for col in close.columns:
                s = close[col].dropna()
                if len(s) >= 20:
                    result[col] = s
            return result
        except YFRateLimitError:
            time.sleep(20 * (attempt + 1))
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "too many" in msg or "rate" in msg:
                time.sleep(20 * (attempt + 1))
            else:
                return {}
    return {}


def _fetch_country(tickers, currency, cache_name, info_delay=0.4):
    """
    1. yf.download() 로 배치 가격 수집
    2. 순차 t.info 로 PER/PBR/ROE 수집
    3. 결합 → DataFrame 반환
    """
    cached = _load_cache(cache_name)
    if cached is not None:
        return cached

    # 중복 제거
    tickers = list(dict.fromkeys(tickers))

    print(f"[{cache_name}] 가격 다운로드 중... ({len(tickers)}개)")
    closes_map = _download_closes(tickers)
    print(f"[{cache_name}] 가격 수집 완료: {len(closes_map)}개")

    records = []
    for i, ticker in enumerate(tickers):
        closes = closes_map.get(ticker)
        if closes is None or len(closes) < 20:
            time.sleep(info_delay)
            continue

        info = _get_info_safe(ticker)
        per = info.get("trailingPE") or info.get("forwardPE")
        if not per or per <= 0 or per > 5000:
            time.sleep(info_delay)
            continue

        pbr_raw = info.get("priceToBook")
        roe_raw = info.get("returnOnEquity")
        name = info.get("longName") or info.get("shortName") or ticker

        records.append({
            "ticker":      ticker,
            "name":        name,
            "price":       round(float(closes.iloc[-1]), 4),
            "PER":         round(float(per), 1),
            "PBR":         round(float(pbr_raw), 2) if pbr_raw and pbr_raw > 0 else None,
            "ROE":         round(float(roe_raw) * 100, 1) if roe_raw else None,
            "RSI":         calculate_rsi(closes),
            "52W_change":  _week52_pct(closes),
            "MA200_gap":   _ma200_gap(closes),
            "currency":    currency,
        })

        if (i + 1) % 10 == 0:
            print(f"[{cache_name}] {i+1}/{len(tickers)} 처리 중...")

        time.sleep(info_delay)

    df = pd.DataFrame(records)
    _save_cache(cache_name, df)
    print(f"[{cache_name}] 완료: {len(df)}개 종목")
    return df


# ── Wikipedia HTML 파싱 (SSL 우회) ───────────────────────────────────

def _html_tables(url):
    resp = requests.get(
        url,
        verify=False,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    resp.raise_for_status()
    return pd.read_html(resp.text)


# ── 한국 (KOSPI 상위 종목) ────────────────────────────────────────────

KOSPI_TICKERS = [
    # 반도체·전자
    "005930.KS",  # 삼성전자
    "000660.KS",  # SK하이닉스
    "009150.KS",  # 삼성전기
    "042700.KS",  # 한미반도체
    "018260.KS",  # 삼성SDS
    "066570.KS",  # LG전자
    "034220.KS",  # LG디스플레이
    "357780.KS",  # 솔브레인
    "240810.KS",  # 원익IPS
    # 2차전지·에너지
    "373220.KS",  # LG에너지솔루션
    "006400.KS",  # 삼성SDI
    "051910.KS",  # LG화학
    "247540.KS",  # 에코프로비엠
    "009830.KS",  # 한화솔루션
    "096770.KS",  # SK이노베이션
    "010950.KS",  # S-Oil
    "267250.KS",  # HD현대중공업
    "078930.KS",  # GS
    # 자동차·부품
    "005380.KS",  # 현대차
    "000270.KS",  # 기아
    "012330.KS",  # 현대모비스
    "011210.KS",  # 현대위아
    "000240.KS",  # 한국타이어앤테크놀로지
    # 금융·보험
    "055550.KS",  # 신한지주
    "105560.KS",  # KB금융
    "086790.KS",  # 하나금융지주
    "032830.KS",  # 삼성생명
    "000810.KS",  # 삼성화재
    "024110.KS",  # 기업은행
    "071050.KS",  # 한국금융지주
    "316140.KS",  # 우리금융지주
    "039490.KS",  # 키움증권
    "006800.KS",  # 미래에셋증권
    "138930.KS",  # BNK금융지주
    "139130.KS",  # DGB금융지주
    # 통신·IT
    "017670.KS",  # SK텔레콤
    "030200.KS",  # KT
    "035420.KS",  # NAVER
    "035720.KS",  # 카카오
    "034730.KS",  # SK
    "259960.KS",  # 크래프톤
    "036570.KS",  # 엔씨소프트
    # 철강·소재·화학
    "005490.KS",  # POSCO홀딩스
    "010130.KS",  # 고려아연
    "002380.KS",  # KCC
    "011170.KS",  # 롯데케미칼
    "011780.KS",  # 금호석유
    "003670.KS",  # 포스코퓨처엠
    "047050.KS",  # 포스코인터내셔널
    # 건설·중공업
    "006360.KS",  # GS건설
    "000720.KS",  # 현대건설
    "042660.KS",  # 한화오션
    "009540.KS",  # HD한국조선해양
    "010140.KS",  # 삼성중공업
    # 바이오·헬스
    "207940.KS",  # 삼성바이오로직스
    "068270.KS",  # 셀트리온
    "000100.KS",  # 유한양행
    "326030.KS",  # SK바이오팜
    "128940.KS",  # 한미약품
    "012450.KS",  # 한화에어로스페이스
    "180640.KS",  # 한화시스템
    # 유통·소비·운수
    "028260.KS",  # 삼성물산
    "139480.KS",  # 이마트
    "023530.KS",  # 롯데쇼핑
    "004170.KS",  # 신세계
    "033780.KS",  # KT&G
    "097950.KS",  # CJ제일제당
    "003550.KS",  # LG
    "001040.KS",  # CJ
    "000120.KS",  # CJ대한통운
    "011200.KS",  # HMM
    "003490.KS",  # 대한항공
    # 에너지·공기업
    "015760.KS",  # 한국전력
    "036460.KS",  # 한국가스공사
    "051600.KS",  # 한전KPS
]

def fetch_korea():
    return _fetch_country(KOSPI_TICKERS, "KRW", "korea", info_delay=0.3)


# ── 미국 S&P 500 ────────────────────────────────────────────────────

_SP500_FALLBACK = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK-B","AVGO","JPM",
    "UNH","XOM","JNJ","V","MA","PG","HD","COST","ABBV","MRK",
    "CVX","PEP","KO","LLY","ADBE","WMT","BAC","TMO","MCD","CSCO",
    "ACN","CRM","ABT","NKE","NFLX","LIN","TXN","DHR","PM","AMGN",
    "DIS","MS","UPS","NEE","BMY","ORCL","GS","INTC","INTU","QCOM",
    "MDT","LOW","CAT","SPGI","HON","AMAT","GE","ELV","ADI","BKNG",
    "ISRG","PLD","SCHW","T","AXP","DE","SYK","GILD","TJX","C",
    "ETN","RTX","ZTS","CB","VRTX","REGN","NOW","MU","PANW","LRCX",
    "AMT","PGR","BSX","CI","SO","AON","MMC","WM","KLAC","SNPS",
    "CME","SLB","DUK","ITW","HUM","APD","EMR","ICE","NSC","USB",
    "WFC","BLK","AIG","COF","FDX","CSX","ECL","FISV","MCK","NOC",
    "AFL","TGT","FCX","ADSK","MRVL","CDNS","MCO","EW","PSA","YUM",
    "CTAS","MNST","ORLY","KDP","PAYX","AEP","FAST","ODFL","MAR","DXCM",
    "XEL","IDXX","CPRT","ON","BKR","PCAR","KHC","VRSK","ANSS","BIIB",
    "TMUS","MMM","GD","F","GM","UBER","LYFT","ABNB","ROST","FTNT",
    "SHW","PH","CARR","OTIS","LHX","HCA","CNC","DVN","EOG","OXY",
    "HAL","MPC","VLO","PSX","COP","PXD","APA","FANG","MRO","HES",
    "STZ","CPB","MKC","SJM","HRL","CAG","K","GIS","TSN","PPC",
    "EXC","PCG","AEE","CMS","ED","WEC","ETR","EIX","FE","PPL",
    "O","WELL","AVB","EQR","INVH","MAA","UDR","CPT","NNN","VTR",
]

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
    "MDLZ","ROP","PDD","MCHP","WBA","CTSH","CDW","CCEP","NTES","ARM",
]

def _get_sp500_tickers():
    try:
        tables = _html_tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        tickers = tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
        if len(tickers) > 400:
            return tickers
    except Exception:
        pass
    return _SP500_FALLBACK

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

def fetch_sp500():
    return _fetch_country(_get_sp500_tickers(), "USD", "sp500", info_delay=0.3)

def fetch_nasdaq100():
    return _fetch_country(_get_nasdaq100_tickers(), "USD", "nasdaq100", info_delay=0.3)

def fetch_us():
    return fetch_sp500()


# ── 일본 (Nikkei 225) ────────────────────────────────────────────────

_NIKKEI225_FALLBACK = [
    # 전기기기
    "6758.T","6752.T","6954.T","6971.T","6981.T","6723.T","6762.T","6857.T",
    "6861.T","6920.T","6869.T","6594.T","6506.T","6473.T","6479.T","6503.T",
    "6501.T","6702.T","6701.T","6724.T","6770.T","6841.T","6963.T","6645.T",
    # 수송기기
    "7203.T","7267.T","7269.T","7270.T","7201.T","7261.T","7272.T","6902.T",
    # 기계
    "6301.T","6326.T","6273.T","6367.T","6113.T","7011.T","7012.T","7013.T",
    # 화학
    "4063.T","4188.T","4005.T","4183.T","4568.T","4523.T","4502.T","4519.T",
    "4507.T","4578.T","4021.T","4042.T","4612.T",
    # 철강·금속
    "5401.T","5411.T","5406.T","5713.T","5802.T","5801.T","5108.T",
    # 금융
    "8306.T","8316.T","8411.T","8309.T","8308.T","8604.T","8601.T",
    "8766.T","8725.T","8750.T","8630.T","8591.T","8697.T",
    # 상사
    "8058.T","8031.T","8001.T","8002.T","8053.T","8015.T",
    # 통신·IT
    "9432.T","9433.T","9434.T","9613.T","4689.T","4704.T",
    # 유통·서비스
    "3382.T","8267.T","9983.T","9843.T","4661.T","9735.T","9766.T",
    # 부동산
    "8801.T","8802.T","8830.T",
    # 운수
    "9020.T","9021.T","9022.T","9101.T","9104.T","9107.T","9201.T","9202.T",
    # 제약·의료
    "4543.T","7741.T",
    # 정밀기기
    "7731.T","7733.T","7751.T","4901.T",
    # 식품·음료
    "2914.T","2502.T","2503.T","2801.T","2802.T",
    # 기타
    "9984.T","7974.T","7832.T","7951.T","5020.T","5019.T",
]

def _get_nikkei225_tickers():
    try:
        tables = _html_tables("https://en.wikipedia.org/wiki/Nikkei_225")
        for t in tables:
            for col in t.columns:
                vals = t[col].astype(str)
                matches = vals[vals.str.match(r"^\d{4}$")]
                if len(matches) > 100:
                    return [v + ".T" for v in matches.tolist()]
    except Exception:
        pass
    return _NIKKEI225_FALLBACK

def fetch_japan():
    return _fetch_country(_get_nikkei225_tickers(), "JPY", "japan", info_delay=0.3)


# ── 중국 (CSI 300 주요 종목) ─────────────────────────────────────────

CSI300_TICKERS = [
    # 상하이 (.SS)
    "600519.SS",  # 귀주마오타이
    "601318.SS",  # 핑안보험
    "600036.SS",  # 초상은행
    "601166.SS",  # 흥업은행
    "600276.SS",  # 항서제약
    "601398.SS",  # 공상은행
    "601288.SS",  # 농업은행
    "601988.SS",  # 중국은행
    "600028.SS",  # 시노펙
    "601857.SS",  # 페트로차이나
    "601601.SS",  # 중국태평양보험
    "601628.SS",  # 중국인수보험
    "600900.SS",  # 장강전력
    "600016.SS",  # 민생은행
    "601668.SS",  # 중국건축
    "600030.SS",  # 중신증권
    "601169.SS",  # 북경은행
    "601328.SS",  # 교통은행
    "601088.SS",  # 중국선화에너지
    "600104.SS",  # SAIC Motor
    "600309.SS",  # 완화화학
    "600585.SS",  # 해라시멘트
    "601012.SS",  # 융기실리콘(LONGi)
    "601899.SS",  # 자금광업
    "601919.SS",  # COSCO해운
    "603501.SS",  # 웨이얼반도체
    "600048.SS",  # 보리발전
    "601800.SS",  # 중국교통건설
    "600050.SS",  # 차이나유니콤
    "601211.SS",  # 국태군안증권
    "600031.SS",  # 삼일중공업
    "601021.SS",  # 춘추항공
    "601225.SS",  # 섬서석탄공업
    "601390.SS",  # 중국중철
    "601186.SS",  # 중국철건
    "600196.SS",  # 복성의약
    "601766.SS",  # 중국중차(CRRC)
    "600905.SS",  # 삼협능원
    "603799.SS",  # 화유코발트
    "600600.SS",  # 청도맥주
    "600887.SS",  # 이리실업
    "600999.SS",  # 초상증권
    "601006.SS",  # 대진철도
    "600660.SS",  # 복요유리
    "603986.SS",  # 조위전자
    "601985.SS",  # 중국핵전
    "603288.SS",  # 해천미업
    "600690.SS",  # 하이얼스마트홈
    "601688.SS",  # 화태증권
    "600406.SS",  # 국전남서
    # 선전 (.SZ)
    "000333.SZ",  # 메이디그룹
    "000002.SZ",  # 완커부동산
    "300750.SZ",  # CATL
    "002594.SZ",  # BYD
    "000001.SZ",  # 핑안은행
    "002415.SZ",  # 하이크비전
    "300760.SZ",  # 마인드레이
    "000725.SZ",  # BOE기술
    "002230.SZ",  # 아이플라이텍
    "000568.SZ",  # 로주라오자오
    "000100.SZ",  # TCL기술
    "300014.SZ",  # EVE에너지
    "002304.SZ",  # 양하주식
    "000661.SZ",  # 장춘고신
    "002714.SZ",  # 목원식품
    "000858.SZ",  # 오량액
    "300059.SZ",  # 동방재부
    "002352.SZ",  # 순풍지주
    "300015.SZ",  # 애얼안과
    "001979.SZ",  # 초상쇼핑
    "002460.SZ",  # 간봉리튬
    "300274.SZ",  # 양광전원
    "002027.SZ",  # 분중광학
    "000776.SZ",  # 광발증권
    "002475.SZ",  # 입신정밀
    "300124.SZ",  # 회천기술
    "000651.SZ",  # 거리전기
    "300408.SZ",  # 삼안광전
    "002142.SZ",  # 영파은행
    "002049.SZ",  # 자광국미
    "002129.SZ",  # TCL중환
    "002466.SZ",  # 천제리튬
    "000876.SZ",  # 신희망
    "002371.SZ",  # 낙양몰리브덴
    "300122.SZ",  # 지오제약
    "300003.SZ",  # 낙보의약
    "002007.SZ",  # 화란생물
    "000800.SZ",  # 일기자동차
    "002601.SZ",  # 용흥소재
    "000538.SZ",  # 운남백약
    "000069.SZ",  # 화교성부동산
    "000032.SZ",  # 심전투자
]

def fetch_china():
    return _fetch_country(CSI300_TICKERS, "CNY", "china", info_delay=0.4)
