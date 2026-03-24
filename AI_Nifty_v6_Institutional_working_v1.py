import streamlit as st
from streamlit_autorefresh import st_autorefresh  # ← NEW!
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import requests, feedparser, time, warnings
from scipy.stats import norm
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
warnings.filterwarnings("ignore")

st.set_page_config(layout="wide", page_title="NIFTY Terminal v5.1", initial_sidebar_state="expanded")

_cache={"news":[],"nts":0,"w":{},"wts":0,"i":{},"its":0}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, .stApp {
  background: #0b0f19 !important;
  color: #dde3ee !important;
  font-family: 'Inter', sans-serif !important;
}

/* ── Streamlit Container Fixes (No gap: 0) ── */
[data-testid="stPlotlyChart"] { margin: 0 !important; padding: 0 !important; }
[data-testid="stPlotlyChart"] > div { margin: 0 !important; padding: 0 !important; }
.js-plotly-plot .plotly { margin: 0 !important; }
iframe { display: block; margin: 0; padding: 0; }
div[data-testid="element-container"]:has(> [data-testid="stPlotlyChart"]) { margin: 0 !important; padding: 0 !important; }
.main .block-container { padding: 10px 14px 14px 14px !important; max-width: 100% !important; }

/* ── Metric cards ── */
div[data-testid="metric-container"] {
  background: #141928 !important;
  border: 1px solid #1f2d45 !important;
  border-radius: 7px !important;
  padding: 8px 10px !important; /* Proper 8-10px spacing */
}
div[data-testid="metric-container"] label {
  font-size: 8.5px !important;
  color: #6e7f9c !important;
  letter-spacing: 0.5px !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
  font-size: 13px !important;
  font-weight: 700 !important;
  color: #dde3ee !important;
  line-height: 1.2 !important;
}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
  font-size: 9px !important;
}

/* Base structural gaps */
[data-testid="stHorizontalBlock"] { gap: 8px !important; }
[data-testid="stVerticalBlock"] { gap: 8px !important; }

/* ── Section heading ── */
.sec {
  font-size: 8.5px; font-weight: 800; letter-spacing: 1.3px;
  text-transform: uppercase; color: #4a6080;
  border-bottom: 1px solid #1a2640;
  padding-bottom: 4px; margin: 10px 0 6px 0; /* Clear section separation */
}

/* ── Signal card ── */
.sig { border-radius: 10px; padding: 10px 14px; margin: 6px 0 8px 0; }
.sig-bull { background: #091f14; border: 1.5px solid #1a6644; }
.sig-bear { background: #200d0d; border: 1.5px solid #6e2020; }
.sig-wait { background: #141928; border: 1px solid #1f2d45; }
.sig-title { font-size: 20px; font-weight: 900; }
.sig-meta  { font-size: 9px; color: #6e7f9c; margin-top: 3px; }
.sig-grid  {
  display: grid; grid-template-columns: repeat(8,minmax(0,1fr));
  gap: 8px; margin-top: 10px;
}
.sig-box { background: #0f1926; border-radius: 6px; padding: 6px 8px; }
.sig-lbl { display: block; font-size: 8px; color: #4a6080; text-transform: uppercase; letter-spacing: .6px; }
.sig-val { display: block; font-size: 12px; font-weight: 700; margin-top: 2px; }

/* ── Right rail ── */
.ph {
  font-size: 9.5px; font-weight: 800; letter-spacing: 1.2px;
  text-transform: uppercase; color: #5a7090;
  border-bottom: 1px solid #1a2640;
  padding-bottom: 4px; margin: 10px 0 6px 0;
}
.idx {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 8px; margin-bottom: 4px; border-radius: 5px; font-size: 12.5px;
}
.idx-u { background: #081910; color: #4ade80; border-left: 2px solid #10b981; }
.idx-d { background: #1a0808; color: #f87171; border-left: 2px solid #ef4444; }
.idx-n { background: #111828; color: #6e7f9c; border-left: 2px solid #1f2d45; }
.inm   { font-weight: 600; max-width: 105px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 12px; }
.ivl   { font-size: 11px; text-align: right; line-height: 1.2; font-weight:600; }

.hot { background: #1a130a; border-left: 3px solid #f59e0b; border-radius: 5px; padding: 6px 8px; margin-bottom: 6px; font-size: 11px; line-height: 1.4; }
.reg { background: #0f141f; border-left: 2px solid #1a2640; border-radius: 5px; padding: 6px 8px; margin-bottom: 6px; font-size: 10.5px; line-height: 1.35; color: #8fa3bc; }
.stg { font-size: 8px; font-weight: 800; padding: 1px 4px; border-radius: 3px; margin-right: 3px; }

/* ── Spread cards ── */
.spr { background: #0f141f; border: 1px solid #1f2d45; border-radius: 8px; padding: 8px 10px; }
.spr-title { font-size: 11px; font-weight: 700; margin-bottom: 4px; }
.spr-row   { display: flex; justify-content: space-between; font-size: 10px; color: #8fa3bc; padding: 2px 0; }
.spr-row b { color: #dde3ee; }

/* ── Control strip ── */
.ctl { background: #0e1420; border: 1px solid #1a2640; border-radius: 8px; padding: 8px 10px; display: flex; gap: 18px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
.ctl-item { display: flex; flex-direction: column; align-items: center; }
.ctl-lbl  { font-size: 8px; color: #4a6080; letter-spacing: .6px; text-transform: uppercase; margin-bottom: 2px;}
.ctl-val  { font-size: 11px; font-weight: 700; color: #dde3ee; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "lk" not in st.session_state:
    st.session_state.lk = {"signal":None,"strike":None,"sl":None,"t1":None,"t2":None,
                            "lots":0,"rr":"—","pop":"—","conf":0,"locked_at":None,
                            "hold":"—","bev":"—","spread":"—","entry":None}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    tf       = st.selectbox("Timeframe", ["1m","3m","5m","15m","30m"], index=2)
    per      = st.selectbox("Period",    ["1d","2d","5d"], index=1)
    candles  = st.slider("Candles", 40, 250, 100)
    iv_m     = st.slider("IV %", 5, 50, 15)
    conf_thr = st.slider("Signal %", 35, 80, 50)
    lock_min = st.slider("Lock (min)", 1, 30, 5)
    risk_pct = st.slider("Risk %", 0.5, 3.0, 1.0) / 100
    account  = st.number_input("Account ₹", 100000, 5000000, 500000, step=50000)
    mute     = st.toggle("Mute Sound", False)
    tg_on    = st.toggle("Telegram",   False)
    BOT      = st.text_input("Bot Token", type="password")
    CID      = st.text_input("Chat ID",   type="password")
    show_bb   = st.toggle("Bollinger Bands", False)
    show_e50  = st.toggle("EMA 50", True)
    st.markdown('---')
    price_h = st.slider("Chart Height (px)", 500, 1100, 720, step=20)
    st.caption("v5.2 — Institutional Terminal")

LOCK_DUR  = lock_min * 60
HOT_KW    = ["crash","surge","rally","plunge","war","fed","rbi","rate","inflation",
             "recession","gdp","budget","election","rupee","nifty","sensex","gold",
             "breakout","circuit","sanctions","oil"]
SRC_COL   = {"ET Markets":"#f59e0b","Moneycontrol":"#3b82f6",
             "Biz Standard":"#ef4444","LiveMint":"#10b981","Reuters":"#8b5cf6"}
INDIA_YF  = {"NIFTY 50":"^NSEI","SENSEX":"^BSESN","Bank NIFTY":"^NSEBANK","India VIX":"^INDIAVIX"}
NSE_MAP   = {"NIFTY 50":"NIFTY 50","SENSEX":"SENSEX","Bank NIFTY":"NIFTY BANK",
             "NIFTY IT":"NIFTY IT","NIFTY Pharma":"NIFTY PHARMA","NIFTY Auto":"NIFTY AUTO",
             "NIFTY FMCG":"NIFTY FMCG","NIFTY Metal":"NIFTY METAL",
             "Midcap 50":"NIFTY MIDCAP 50","India VIX":"India VIX"}
WORLD_IDX = {"S&P 500":"^GSPC","Dow Jones":"^DJI","NASDAQ":"^IXIC","VIX(US)":"^VIX",
             "FTSE 100":"^FTSE","DAX":"^GDAXI","Nikkei":"^N225","Crude Oil":"CL=F",
             "Gold":"GC=F","USD/INR":"INR=X","US 10Y":"^TNX"}
RSS_FEEDS = [("ET Markets","https://economictimes.indiatimes.com/markets/rss.cms"),
             ("Moneycontrol","https://www.moneycontrol.com/rss/marketreports.xml"),
             ("Biz Standard","https://www.business-standard.com/rss/markets-106.rss"),
             ("LiveMint","https://www.livemint.com/rss/markets"),
             ("Reuters","https://feeds.reuters.com/reuters/INbusinessNews")]

def alert(msg):
    if not mute:
        try: import winsound; winsound.Beep(1760,400)
        except: pass
    if tg_on and BOT and CID:
        try: requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",
                           data={"chat_id":CID,"text":msg}, timeout=5)
        except: pass

# ── Data helpers ───────────────────────────────────────────────────────────────
def _fast(ns):
    n,s=ns
    try:
        fi=yf.Ticker(s).fast_info
        c=float(fi.last_price or 0); p=float(fi.previous_close or 0)
        if c and p: return n,{"price":c,"pct":((c-p)/p)*100}
        if c:       return n,{"price":c,"pct":0}
    except: pass
    try:
        h=yf.Ticker(s).history(period="2d",interval="1d")
        if len(h)>=2:
            p2,c2=float(h["Close"].iloc[-2]),float(h["Close"].iloc[-1])
            return n,{"price":c2,"pct":((c2-p2)/p2)*100 if p2 else 0}
    except: pass
    return n,{"price":None,"pct":0}

def fetch_india(ttl=15):
    now=time.time()
    if (now-_cache["its"])<ttl and _cache["i"]: return _cache["i"]
    res={k:{"price":None,"pct":0} for k in NSE_MAP}
    try:
        ss=requests.Session()
        ss.headers.update({"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com"})
        ss.get("https://www.nseindia.com",timeout=5)
        r=ss.get("https://www.nseindia.com/api/allIndices",timeout=8)
        if r.status_code==200:
            lkp={i.get("indexSymbol",i.get("index","")):i for i in r.json().get("data",[])}
            for lbl,nm in NSE_MAP.items():
                it=lkp.get(nm)
                if it:
                    c=float(it.get("last") or it.get("indexValue") or 0)
                    p=float(it.get("percentChange") or it.get("pChange") or 0)
                    if c: res[lbl]={"price":c,"pct":p}
    except: pass
    miss={k:INDIA_YF[k] for k,v in res.items() if not v["price"] and k in INDIA_YF}
    if miss:
        with ThreadPoolExecutor(max_workers=5) as ex:
            for f in as_completed({ex.submit(_fast,(n,s)):n for n,s in miss.items()},timeout=10):
                try: n2,d2=f.result(); res[n2]=d2
                except: pass
    _cache["i"]=res; _cache["its"]=now; return res

def fetch_world(ttl=25):
    now=time.time()
    if (now-_cache["wts"])<ttl and _cache["w"]: return _cache["w"]
    with ThreadPoolExecutor(max_workers=10) as ex:
        fts={ex.submit(_fast,(n,s)):n for n,s in WORLD_IDX.items()}
        res={}
        for f in as_completed(fts,timeout=14):
            try: n2,d2=f.result(); res[n2]=d2
            except: res[fts[f]]={"price":None,"pct":0}
    out={n:res.get(n,{"price":None,"pct":0}) for n in WORLD_IDX}
    _cache["w"]=out; _cache["wts"]=now; return out

def fetch_news(ttl=90):
    now=time.time()
    if (now-_cache["nts"])<ttl and _cache["news"]: return _cache["news"]
    items=[]; seen=set()
    def _rss(src,url):
        out=[]
        try:
            feed=feedparser.parse(url)
            for e in feed.entries[:6]:
                t=e.get("title","").strip()
                if not t or t in seen: continue
                seen.add(t)
                try: ts=time.mktime(e.published_parsed) if e.published_parsed else now
                except: ts=now
                out.append({"title":t,"src":src,"link":e.get("link","#"),
                            "time":datetime.fromtimestamp(ts).strftime("%H:%M"),"ts":ts})
        except: pass
        return out
    with ThreadPoolExecutor(max_workers=5) as ex:
        for r in ex.map(lambda x:_rss(*x),RSS_FEEDS): items.extend(r)
    items.sort(key=lambda x:x["ts"],reverse=True)
    _cache["news"]=items[:28]; _cache["nts"]=now; return _cache["news"]

# ── BS helpers ─────────────────────────────────────────────────────────────────
def bsg(S,K,T,r,sig):
    T=max(T,1e-4)
    d1=(np.log(S/K)+(r+.5*sig**2)*T)/(sig*np.sqrt(T)); d2=d1-sig*np.sqrt(T)
    return {"dc":norm.cdf(d1),"dp":-norm.cdf(-d1),
            "gamma":norm.pdf(d1)/(S*sig*np.sqrt(T)),
            "theta":(-(S*norm.pdf(d1)*sig)/(2*np.sqrt(T))-r*K*np.exp(-r*T)*norm.cdf(d2))/365,
            "vega":S*norm.pdf(d1)*np.sqrt(T)/100}

def bsp(S,K,T,r,sig,opt="C"):
    T=max(T,1e-4)
    d1=(np.log(S/K)+(r+.5*sig**2)*T)/(sig*np.sqrt(T)); d2=d1-sig*np.sqrt(T)
    if opt=="C": return S*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d2)
    return K*np.exp(-r*T)*norm.cdf(-d2)-S*norm.cdf(-d1)

def pop_fn(S,K,T,sig,opt="C"):
    T=max(T,1e-4)
    d2=(np.log(S/K)+(.05-.5*sig**2)*T)/(sig*np.sqrt(T))
    return norm.cdf(d2)*100 if opt=="C" else norm.cdf(-d2)*100

@st.cache_resource
def _nse():
    ss=requests.Session()
    ss.headers.update({"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com"})
    try: ss.get("https://www.nseindia.com",timeout=5)
    except: pass
    return ss

@st.cache_data(ttl=30)
def get_chain():
    try:
        r=_nse().get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",timeout=8)
        if r.status_code!=200: return [],None
        recs=r.json()["records"]["data"]
        near=min({d["expiryDate"] for d in recs},key=lambda x:datetime.strptime(x,"%d-%b-%Y"))
        return [d for d in recs if d["expiryDate"]==near],near
    except: return [],None

@st.cache_data(ttl=300)
def get_fii():
    try:
        r=_nse().get("https://www.nseindia.com/api/fiidiiTradeReact",timeout=8)
        return r.json() if r.status_code==200 else None
    except: return None

@st.cache_data(ttl=20)
def get_nifty(per,tf):
    t=yf.Ticker("^NSEI")
    return t.history(period=per,interval=tf).dropna(), t.history(period="60d",interval="1d").dropna()

@st.cache_data(ttl=20)
def get_vix():
    try: return yf.Ticker("^INDIAVIX").history(period="5d",interval="1d").dropna()
    except: return pd.DataFrame()

# ── Fetch main data ────────────────────────────────────────────────────────────
data, daily = get_nifty(per, tf)
vix_df      = get_vix()

if data.empty:
    st.error("⚠️ No data. Check connection."); st.stop()

price = float(data["Close"].iloc[-1])
pdh   = float(daily["High"].iloc[-2])  if len(daily)>=2 else price
pdl   = float(daily["Low"].iloc[-2])   if len(daily)>=2 else price
ivix  = round(float(vix_df["Close"].iloc[-1]),2) if not vix_df.empty else 15.0
pvix  = round(float(vix_df["Close"].iloc[-2]),2) if len(vix_df)>1   else ivix

# Indicators
data["TP"]   = (data["High"]+data["Low"]+data["Close"])/3
data["Vol"]  = data["Volume"].replace(0,1)
data["VWAP"] = (data["TP"]*data["Vol"]).cumsum() / data["Vol"].cumsum()
vwap = float(data["VWAP"].iloc[-1])
data["TR"]=np.maximum(data["High"]-data["Low"],
            np.maximum(abs(data["High"]-data["Close"].shift(1)),
                       abs(data["Low"] -data["Close"].shift(1))))
atr=float(data["TR"].rolling(14).mean().iloc[-1])
if np.isnan(atr): atr=float(data["TR"].mean())
for sp,col in [(9,"EMA9"),(21,"EMA21"),(50,"EMA50")]:
    data[col]=data["Close"].ewm(span=sp,adjust=False).mean()
dr=data["Close"].diff()
g_=dr.clip(lower=0).rolling(14).mean(); l_=(-dr.clip(upper=0)).rolling(14).mean()
data["RSI"]=100-(100/(1+(g_/l_).replace(0,1e-9)))
rsi=round(float(data["RSI"].iloc[-1]),1)
data["MACD"]=data["Close"].ewm(span=12,adjust=False).mean()-data["Close"].ewm(span=26,adjust=False).mean()
data["MS"]=data["MACD"].ewm(span=9,adjust=False).mean()
data["MH"]=data["MACD"]-data["MS"]
macd=round(float(data["MACD"].iloc[-1]),2); ms=round(float(data["MS"].iloc[-1]),2)
macd_p=round(float(data["MACD"].iloc[-2]),2) if len(data)>1 else macd
ms_p  =round(float(data["MS"].iloc[-2]),2)   if len(data)>1 else ms
data["BB_M"]=data["Close"].rolling(20).mean()
data["BB_S"]=data["Close"].rolling(20).std()
data["BB_U"]=data["BB_M"]+2*data["BB_S"]; data["BB_D"]=data["BB_M"]-2*data["BB_S"]
data["CD"]=np.where(data["Close"]>=data["Open"],data["Vol"],-data["Vol"])
data["CDS"]=data["CD"].cumsum(); cum_d=int(data["CDS"].iloc[-1])
op=data.iloc[:max(1,int(len(data)*.04))]
or_hi=float(op["High"].max()); or_lo=float(op["Low"].min())
trend ="Bullish" if price>vwap   else "Bearish"
etrend="Bullish" if float(data["EMA9"].iloc[-1])>float(data["EMA21"].iloc[-1]) else "Bearish"
macd_bx=macd_p<=ms_p and macd>ms; macd_sx=macd_p>=ms_p and macd<ms; sigma=iv_m/100

# OI chain
recs,near_exp=get_chain()
coi={};poi={};civ={};piv={};cvol={};pvol={};clp={};plp={}
pcr=1.0;cwall=pwall=None;mpain=price;gex_s={};gex_t=0;zgamma=price;all_s=[];oisig="Neutral";T_=7/365
if near_exp:
    try: T_=max(1,(datetime.strptime(near_exp,"%d-%b-%Y")-datetime.now()).days)/365
    except: pass
if recs:
    for rec in recs:
        s=rec["strikePrice"]; ce=rec.get("CE",{}); pe=rec.get("PE",{})
        coi[s]=ce.get("openInterest",0)or 0; poi[s]=pe.get("openInterest",0)or 0
        civ[s]=ce.get("impliedVolatility",iv_m)or iv_m; piv[s]=pe.get("impliedVolatility",iv_m)or iv_m
        cvol[s]=ce.get("totalTradedVolume",0)or 0; pvol[s]=pe.get("totalTradedVolume",0)or 0
        clp[s]=ce.get("lastPrice",0)or 0; plp[s]=pe.get("lastPrice",0)or 0
    tc,tp=sum(coi.values()),sum(poi.values()); pcr=tp/tc if tc else 1.0
    if coi: cwall=max(coi,key=coi.get)
    if poi: pwall=max(poi,key=poi.get)
    all_s=sorted(set(coi)|set(poi))
    if all_s:
        pain={s:sum(max(0,s-k)*v for k,v in coi.items())+sum(max(0,k-s)*v for k,v in poi.items()) for s in all_s}
        mpain=min(pain,key=pain.get)
        for s in all_s:
            siv=max((civ.get(s,iv_m)+piv.get(s,iv_m))/2/100,.01)
            g=bsg(price,s,T_,.05,siv); gex_s[s]=g["gamma"]*(coi.get(s,0)-poi.get(s,0))*50*price**2*.01; gex_t+=gex_s[s]
        gv=[gex_s[s] for s in all_s]; zgamma=all_s[min(range(len(gv)),key=lambda i:abs(gv[i]))]
        cbd=sum(1 for s in all_s if coi.get(s,0) and cvol.get(s,0)/(coi[s]+1)>.3 and abs(s-price)<300)
        pbd=sum(1 for s in all_s if poi.get(s,0) and pvol.get(s,0)/(poi[s]+1)>.3 and abs(s-price)<300)
        oisig="Fresh CE(Bear)" if cbd>pbd else "Fresh PE(Bull)" if pbd>cbd else "Neutral"
gex_reg="Pos(Pin)" if gex_t>0 else "Neg(Trend)"
atm=round(price/50)*50; ga=bsg(price,atm,T_,.05,sigma)
gdc=round(ga["dc"],3); gtht=round(ga["theta"],2); gveg=round(ga["vega"],2)
cep=round(float(clp.get(atm-50) or clp.get(atm) or bsp(price,atm,T_,.05,sigma,"C")),2)
pep=round(float(plp.get(atm+50) or plp.get(atm) or bsp(price,atm,T_,.05,sigma,"P")),2)
pop_c=round(pop_fn(price,atm+100,T_,sigma,"C"),1); pop_p=round(pop_fn(price,atm-100,T_,sigma,"P"),1)
fii_d=get_fii(); fn_=dn_="N/A"
if fii_d:
    try:
        for i in fii_d:
            cat=str(i.get("category","")).upper()
            if "FII" in cat: fn_=i.get("netValue","N/A")
            if "DII" in cat: dn_=i.get("netValue","N/A")
    except: pass

# AI Score
ai=0; af=[]
if trend=="Bullish": ai+=18; af.append("✅ Above VWAP")
else:                ai+=18; af.append("✅ Below VWAP")
if etrend==trend:    ai+=14; af.append("✅ EMA Aligned")
else:                        af.append("⚠️ EMA Diverging")
if trend=="Bullish":
    if rsi>52:   ai+=12; af.append(f"✅ RSI Bullish ({rsi})")
    elif rsi>44: ai+=6;  af.append(f"🔸 RSI Weak ({rsi})")
    else:                af.append(f"❌ RSI Bearish ({rsi})")
else:
    if rsi<48:   ai+=12; af.append(f"✅ RSI Bearish ({rsi})")
    elif rsi<56: ai+=6;  af.append(f"🔸 RSI Neutral ({rsi})")
    else:                af.append(f"❌ RSI Bullish ({rsi})")
if macd_bx and trend=="Bullish":   ai+=16; af.append("🔥 MACD Bull Cross!")
elif macd_sx and trend=="Bearish": ai+=16; af.append("🔥 MACD Bear Cross!")
elif macd>ms and trend=="Bullish": ai+=10; af.append("✅ MACD Bull")
elif macd<ms and trend=="Bearish": ai+=10; af.append("✅ MACD Bear")
else:                                      af.append("❌ MACD Against")
if pcr<.85 and trend=="Bullish":    ai+=12; af.append(f"✅ PCR Bull ({pcr:.2f})")
elif pcr>1.15 and trend=="Bearish": ai+=12; af.append(f"✅ PCR Bear ({pcr:.2f})")
elif .85<=pcr<=1.15:                ai+=5;  af.append(f"🔸 PCR Neutral ({pcr:.2f})")
else:                                       af.append(f"❌ PCR Against ({pcr:.2f})")
if cum_d>0 and trend=="Bullish":   ai+=8; af.append("✅ Delta Bull")
elif cum_d<0 and trend=="Bearish": ai+=8; af.append("✅ Delta Bear")
else:                                     af.append("🔸 Delta Neutral")
if gex_t<0: ai+=8; af.append("✅ Neg GEX (Trending)")
else:        ai+=4; af.append("🔸 Pos GEX (Pinning)")
if price>or_hi and trend=="Bullish":   ai+=10; af.append("🔥 OR Breakout Bull")
elif price<or_lo and trend=="Bearish": ai+=10; af.append("🔥 OR Breakout Bear")
else:                                          af.append("🔸 Inside OR")
if ivix<14: ai+=6; af.append(f"✅ VIX Low ({ivix})")
elif ivix<18:ai+=3; af.append(f"🔸 VIX OK ({ivix})")
else:              af.append(f"⚠️ VIX High ({ivix})")
ai_prob=min(ai,100)
pcr_z="X-Bull" if pcr<.7 else "Bull" if pcr<.9 else "Ntrl" if pcr<1.1 else "Bear" if pcr<1.3 else "X-Bear"

# Signal
SIG="NO ENTRY"; STK="—"; LOTS=0; RR_="—"; BEV="—"; POP_S="—"; HLD="—"; SPR_="—"; T1_=price; T2_=price; sl_=price
bull_ok=trend=="Bullish" and etrend=="Bullish" and rsi>45 and ai_prob>=conf_thr
bear_ok=trend=="Bearish" and etrend=="Bearish" and rsi<55 and ai_prob>=conf_thr
if bull_ok:
    otce=atm+100; sl_=max(or_lo,vwap-atr*.3,price-atr*.8); T1_=price+atr*1.2; T2_=price+atr*2.5
    risk=max(price-sl_,.1); LOTS=max(1,int((account*risk_pct)/risk/50))
    SIG="BUY CE 🟢"; STK=f"{otce} CE"; RR_=f"1:{round((T1_-price)/risk,1)}"
    HLD="15-30m" if ai_prob<70 else "30-60m"; BEV=f"{otce+cep:.0f}"; POP_S=f"{pop_c}%"
    SPR_=f"Bull Put Credit — Sell {atm}PE / Buy {atm-100}PE"
elif bear_ok:
    otpe=atm-100; sl_=min(or_hi,vwap+atr*.3,price+atr*.8); T1_=price-atr*1.2; T2_=price-atr*2.5
    risk=max(sl_-price,.1); LOTS=max(1,int((account*risk_pct)/risk/50))
    SIG="BUY PE 🔴"; STK=f"{otpe} PE"; RR_=f"1:{round((price-T1_)/risk,1)}"
    HLD="15-30m" if ai_prob<70 else "30-60m"; BEV=f"{otpe-pep:.0f}"; POP_S=f"{pop_p}%"
    SPR_=f"Bear Call Credit — Sell {atm}CE / Buy {atm+100}CE"

now_t=time.time(); lk=st.session_state.lk
elapsed=now_t-lk["locked_at"] if lk["locked_at"] else LOCK_DUR+1
remaining=max(0,LOCK_DUR-elapsed); lock_on=lk["locked_at"] is not None and elapsed<LOCK_DUR
try: sl_hit=("CE" in (lk["signal"] or "") and price<float(lk["sl"] or 0)-atr*.05) or             ("PE" in (lk["signal"] or "") and price>float(lk["sl"] or 0)+atr*.05)
except: sl_hit=False
emergency=(lk["conf"]-ai_prob>25) or sl_hit
if SIG!="NO ENTRY":
    if not lock_on or emergency or lk["signal"]!=SIG:
        lk.update({"signal":SIG,"strike":STK,"sl":f"{sl_:.0f}","t1":f"{T1_:.0f}","t2":f"{T2_:.0f}",
                   "lots":LOTS,"rr":RR_,"pop":POP_S,"conf":ai_prob,"locked_at":now_t,
                   "hold":HLD,"bev":BEV,"spread":SPR_,"entry":f"{price:.0f}"})
        alert(f"{SIG}|{STK}|Entry:{price:.0f}|SL:{sl_:.0f}|T1:{T1_:.0f}|Lots:{LOTS}")
elif emergency and lock_on:
    lk.update({"signal":None,"locked_at":None})
st.session_state.lk=lk

# ══════════════════════════════════════════════════════════════════════════════
# PAGE RENDER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"<div style='font-size:13px;font-weight:700;color:#dde3ee;padding:1px 0 5px 0'>"
    f"🏛️ NIFTY Institutional Terminal &nbsp;"
    f"<span style='font-size:9px;color:#4a6080;font-weight:500'>"
    f"{datetime.now().strftime('%d %b %Y  %H:%M:%S')}</span></div>",
    unsafe_allow_html=True)

main_l, main_r = st.columns([0.80, 0.20], gap="medium")

# ── RIGHT RAIL ─────────────────────────────────────────────────────────────────
with main_r:
    with ThreadPoolExecutor(max_workers=3) as ex:
        fi=ex.submit(fetch_india,15); fw=ex.submit(fetch_world,25); fn=ex.submit(fetch_news,90)
        id_=fi.result(); wd=fw.result(); nws=fn.result()

    def idx_row(n,d):
        if not d["price"]:
            return f'<div class="idx idx-n"><span class="inm">{n}</span><span class="ivl">—</span></div>'
        p,pct=d["price"],d["pct"]
        cls="idx-u" if pct>0 else "idx-d" if pct<0 else "idx-n"
        arr="▲" if pct>0 else "▼" if pct<0 else "●"
        ps=f"{p:,.0f}" if p>500 else f"{p:,.2f}" if p>10 else f"{p:.3f}"
        return f'<div class="idx {cls}"><span class="inm">{n}</span><span class="ivl"><b>{ps}</b><br>{arr}{pct:+.2f}%</span></div>'

    st.markdown('<div class="ph">🇮🇳 India Indices</div>', unsafe_allow_html=True)
    st.markdown("".join(idx_row(n,d) for n,d in id_.items()), unsafe_allow_html=True)
    st.markdown('<div class="ph">🌍 Global</div>', unsafe_allow_html=True)
    st.markdown("".join(idx_row(n,d) for n,d in wd.items()), unsafe_allow_html=True)

    hot=[i for i in nws if any(k in i["title"].lower() for k in HOT_KW)]
    reg=[i for i in nws if i not in hot]

    if hot:
        st.markdown('<div class="ph">🔥 High Impact</div>', unsafe_allow_html=True)
        st.markdown("".join(
            f'<div class="hot"><span class="stg" style="background:{SRC_COL.get(i["src"],"#555")}22;color:{SRC_COL.get(i["src"],"#ccc")}">{i["src"]}</span>'
            f'<a href="{i["link"]}" target="_blank" style="color:#f59e0b;text-decoration:none;font-weight:600">{i["title"]}</a>'
            f'<br><span style="font-size:8.5px;color:#4a6080">{i["time"]}</span></div>'
            for i in hot[:5]), unsafe_allow_html=True)

    st.markdown('<div class="ph">📰 News</div>', unsafe_allow_html=True)
    st.markdown("".join(
        f'<div class="reg"><span class="stg" style="background:{SRC_COL.get(i["src"],"#555")}18;color:{SRC_COL.get(i["src"],"#bbb")}">{i["src"]}</span>'
        f'<a href="{i["link"]}" target="_blank" style="color:#8fa3bc;text-decoration:none">{i["title"]}</a>'
        f'<br><span style="font-size:8px;color:#2d3f58">{i["time"]}</span></div>'
        for i in reg[:10]), unsafe_allow_html=True)

# ── LEFT MAIN ─────────────────────────────────────────────────────────────────
with main_l:

    # Control strip
    st.markdown(
        f'<div class="ctl">'
        f'<div class="ctl-item"><span class="ctl-lbl">TF</span><span class="ctl-val">{tf}</span></div>'
        f'<div class="ctl-item"><span class="ctl-lbl">Candles</span><span class="ctl-val">{candles}</span></div>'
        f'<div class="ctl-item"><span class="ctl-lbl">Threshold</span><span class="ctl-val">{conf_thr}%</span></div>'
        f'<div class="ctl-item"><span class="ctl-lbl">Lock</span><span class="ctl-val">{lock_min}m</span></div>'
        f'<div class="ctl-item"><span class="ctl-lbl">Sound</span><span class="ctl-val">{"OFF" if mute else "ON"}</span></div>'
        f'<div class="ctl-item"><span class="ctl-lbl">Telegram</span><span class="ctl-val">{"ON" if tg_on else "OFF"}</span></div>'
        f'<div class="ctl-item"><span class="ctl-lbl">BB</span><span class="ctl-val">{"ON" if show_bb else "OFF"}</span></div>'
        f'<div class="ctl-item"><span class="ctl-lbl">EMA50</span><span class="ctl-val">{"ON" if show_e50 else "OFF"}</span></div>'
        f'</div>', unsafe_allow_html=True)

    # Signal banner
    if lk["signal"] and lock_on:
        bull="CE" in lk["signal"]
        col="#10b981" if bull else "#ef4444"; cls="sig-bull" if bull else "sig-bear"
        m2,s2=int(remaining//60),int(remaining%60)
        st.markdown(f"""<div class="sig {cls}">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span class="sig-title" style="color:{col}">{lk["signal"]}</span>
            <span style="background:#0b0f19;border:1px solid {col}33;padding:2px 10px;border-radius:20px;font-size:10px;color:{col}">
              🔒 {m2:02d}:{s2:02d} &nbsp;·&nbsp; Conf {lk["conf"]}%
            </span>
          </div>
          <div class="sig-meta">Fired {datetime.fromtimestamp(lk["locked_at"]).strftime("%H:%M:%S")} · Hold {lk["hold"]} · {lk["spread"]}</div>
          <div class="sig-grid">
            <div class="sig-box"><span class="sig-lbl">Strike</span><span class="sig-val" style="color:{col}">{lk["strike"]}</span></div>
            <div class="sig-box"><span class="sig-lbl">Entry</span><span class="sig-val">{lk["entry"]}</span></div>
            <div class="sig-box"><span class="sig-lbl">SL</span><span class="sig-val" style="color:#ef4444">{lk["sl"]}</span></div>
            <div class="sig-box"><span class="sig-lbl">T1</span><span class="sig-val" style="color:#10b981">{lk["t1"]}</span></div>
            <div class="sig-box"><span class="sig-lbl">T2</span><span class="sig-val" style="color:#10b981">{lk["t2"]}</span></div>
            <div class="sig-box"><span class="sig-lbl">Lots</span><span class="sig-val" style="color:#f59e0b">{lk["lots"]}</span></div>
            <div class="sig-box"><span class="sig-lbl">R:R</span><span class="sig-val">{lk["rr"]}</span></div>
            <div class="sig-box"><span class="sig-lbl">PoP</span><span class="sig-val">{lk["pop"]}</span></div>
          </div>
        </div>""", unsafe_allow_html=True)
    elif lk["signal"] and not lock_on:
        bull="CE" in lk["signal"]; col="#10b981" if bull else "#ef4444"
        sl_hit_now=False
        try:
            if not bull and price>float(lk["sl"] or 0): sl_hit_now=True
            if bull  and price<float(lk["sl"] or 0):    sl_hit_now=True
        except: pass
        icon="⛔ SL HIT" if sl_hit_now else "⏰ Lock Expired"
        bdr="#ef4444" if sl_hit_now else "#2d3f58"
        label_col="#ef4444" if sl_hit_now else "#8fa3bc"
        html_exp=(
            f"<div class='sig sig-wait' style='border-color:{bdr};'>"
            f"<span style='color:{label_col};font-weight:800;font-size:11px'>{icon} &nbsp;|&nbsp; </span>"
            f"<b style='color:{col};font-size:12px'>{lk['signal']}</b>"
            f"<span style='color:#8fa3bc;font-size:11px'>"
            f" &nbsp;·&nbsp; Strike: <b>{lk['strike']}</b>"
            f" &nbsp;·&nbsp; Entry: <b>{lk['entry']}</b>"
            f" &nbsp;·&nbsp; SL: <b style='color:#ef4444'>{lk['sl']}</b>"
            f" &nbsp;·&nbsp; T1: <b style='color:#10b981'>{lk['t1']}</b>"
            f"</span></div>"
        )
        st.markdown(html_exp, unsafe_allow_html=True)
    else:
        bar=min(100,int(ai_prob/conf_thr*100)) if conf_thr else 0
        col="#10b981" if bar>80 else "#f59e0b" if bar>55 else "#ef4444"
        st.markdown(f"""<div class="sig sig-wait">
          <div style="display:flex;justify-content:space-between;font-size:11px">
            <span>⏳ <b>No Trade Setup</b> — Confluence <b style="color:{col}">{ai_prob}%</b> / {conf_thr}% · Bias <b>{trend}</b></span>
            <span style="font-size:9px;color:#4a6080">Adjust threshold ↗ sidebar</span>
          </div>
          <div style="background:#1a2640;border-radius:3px;height:3px;margin-top:5px">
            <div style="background:{col};width:{bar}%;height:3px;border-radius:3px"></div>
          </div>
        </div>""", unsafe_allow_html=True)

    # Metrics — custom HTML, values never truncated
    st.markdown('<div class="sec">Key Metrics</div>', unsafe_allow_html=True)
    try:
        fi2=yf.Ticker("^NSEI").fast_info
        rtp=float(fi2.last_price or price); rtp_p=float(fi2.previous_close or price)
        rtc=round(((rtp-rtp_p)/rtp_p)*100,2) if rtp_p else 0
    except: rtp,rtc=price,0

    def _mc(lbl,val,dlt=None,col=None):
        dc=""
        if dlt is not None:
            dc_c="#10b981" if dlt>=0 else "#ef4444"; arr="▲" if dlt>=0 else "▼"
            dc=f"<span style='font-size:9px;color:{dc_c}'>{arr} {abs(dlt):.2f}</span>"
        vc=f"color:{col}" if col else "color:#dde3ee"
        return (f"<div style='background:#141928;border:1px solid #1f2d45;border-radius:7px;"
                f"padding:6px 8px;min-width:0;overflow:hidden'>"
                f"<div style='font-size:8px;color:#4a6080;letter-spacing:.5px;"
                f"text-transform:uppercase;white-space:nowrap'>{lbl}</div>"
                f"<div style='font-size:12px;font-weight:700;{vc};white-space:nowrap'>{val}</div>{dc}</div>")

    r1=st.columns(8)
    r1[0].markdown(_mc("NIFTY",    f"{rtp:,.1f}", dlt=rtc), unsafe_allow_html=True)
    r1[1].markdown(_mc("VWAP",     f"{vwap:,.0f}"), unsafe_allow_html=True)
    r1[2].markdown(_mc("VIX",      f"{ivix:.2f}", dlt=round(ivix-pvix,2)), unsafe_allow_html=True)
    r1[3].markdown(_mc("PCR",      f"{pcr:.2f} {pcr_z}"), unsafe_allow_html=True)
    r1[4].markdown(_mc("AI Score", f"{ai_prob}%",
        col="#10b981" if (ai_prob>=conf_thr and trend=="Bullish")
            else "#ef4444" if (ai_prob>=conf_thr and trend=="Bearish")
            else "#f59e0b"), unsafe_allow_html=True)
    r1[5].markdown(_mc("ATR",      f"{atr:.0f}"), unsafe_allow_html=True)
    r1[6].markdown(_mc("FII Net",  str(fn_)), unsafe_allow_html=True)
    r1[7].markdown(_mc("DII Net",  str(dn_)), unsafe_allow_html=True)

    r2=st.columns(8)
    r2[0].markdown(_mc("RSI",      f"{rsi:.1f}",
        col="#10b981" if rsi>55 else "#ef4444" if rsi<45 else "#f59e0b"), unsafe_allow_html=True)
    r2[1].markdown(_mc("MACD",     f"{macd:.2f}",
        col="#10b981" if macd>ms else "#ef4444"), unsafe_allow_html=True)
    r2[2].markdown(_mc("Cum Delta",f"{cum_d:+,}",
        col="#10b981" if cum_d>0 else "#ef4444"), unsafe_allow_html=True)
    r2[3].markdown(_mc("Max Pain", f"{mpain:.0f}"), unsafe_allow_html=True)
    r2[4].markdown(_mc("ZeroGamma",f"{zgamma:.0f}"), unsafe_allow_html=True)
    r2[5].markdown(_mc("CE Delta", f"{gdc:.3f}"), unsafe_allow_html=True)
    r2[6].markdown(_mc("Theta/day",f"-{abs(gtht):.2f}"), unsafe_allow_html=True)
    r2[7].markdown(_mc("Vega",     f"{gveg:.2f}"), unsafe_allow_html=True)

    # ── CHART ─────────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec">Price Action</div>', unsafe_allow_html=True)
    dv = data.iloc[max(0, len(data)-candles):].copy()

    # Market Profile
    def _mp(df, rows=30):
        lo, hi = float(df["Low"].min()), float(df["High"].max())
        if hi == lo: return price, hi, lo
        bs = (hi-lo)/rows; pf = {}
        for _, r in df.iterrows():
            lv = lo
            while lv <= r["High"]:
                k = round(round(lv/bs)*bs, 2); pf[k] = pf.get(k,0)+r["Volume"]; lv += bs
        prof = pd.DataFrame(list(pf.items()), columns=["Price","Volume"]).sort_values("Price")
        poc  = float(prof.loc[prof["Volume"].idxmax(), "Price"])
        cv   = prof["Volume"].sum(); run = 0; va = []
        for _, r in prof.sort_values("Volume", ascending=False).iterrows():
            if run >= cv*.7: break
            va.append(r["Price"]); run += r["Volume"]
        return poc, max(va) if va else hi, min(va) if va else lo
    poc, vah, val = _mp(dv)

    # Volume scaled into price panel (bottom 12% of price range — no secondary axis)
    pr_lo = float(dv["Low"].min()); pr_hi = float(dv["High"].max())
    pr_range = pr_hi - pr_lo
    vol_max  = float(dv["Vol"].max()) or 1
    vol_base = pr_lo - pr_range * 0.04
    vol_top  = pr_lo + pr_range * 0.10
    dv["vol_y"] = vol_base + (dv["Vol"] / vol_max) * (vol_top - vol_base)

    # Buy/Sell signal zones
    dv["bz"] = (dv["EMA9"]>dv["EMA21"]) & (dv["Close"]>dv["VWAP"]) & (dv["RSI"]>50) & (dv["MACD"]>dv["MS"])
    dv["sz"] = (dv["EMA9"]<dv["EMA21"]) & (dv["Close"]<dv["VWAP"]) & (dv["RSI"]<50) & (dv["MACD"]<dv["MS"])
    dv["be"] = dv["bz"] & ~dv["bz"].shift(1).fillna(False)
    dv["se"] = dv["sz"] & ~dv["sz"].shift(1).fillna(False)

    # ── Single figure, 3 rows, shared x ──────────────────────────────────────────
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.60, 0.22, 0.18],
        vertical_spacing=0.06
    )

    # ── Row 1: Price ──────────────────────────────────────────────────────────────
    # Volume bars (scaled into price space — no yaxis4 needed)
    vcols = ["rgba(16,185,129,0.25)" if c>=o else "rgba(239,68,68,0.25)"
             for c,o in zip(dv["Close"], dv["Open"])]
    fig.add_trace(go.Bar(
        x=dv.index, y=dv["vol_y"]-vol_base,
        base=vol_base,
        marker_color=vcols, marker_line_width=0,
        name="Vol", showlegend=False, hoverinfo="skip"
    ), row=1, col=1)

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=dv.index, open=dv["Open"], high=dv["High"], low=dv["Low"], close=dv["Close"],
        increasing=dict(line=dict(color="#10b981", width=1), fillcolor="#10b981"),
        decreasing=dict(line=dict(color="#ef4444", width=1), fillcolor="#ef4444"),
        whiskerwidth=0.4, name="NIFTY"
    ), row=1, col=1)

    # EMAs + VWAP
    fig.add_trace(go.Scatter(x=dv.index, y=dv["EMA9"],  line=dict(color="#3b82f6",width=1),   name="EMA9"),  row=1, col=1)
    fig.add_trace(go.Scatter(x=dv.index, y=dv["EMA21"], line=dict(color="#8b5cf6",width=1),   name="EMA21"), row=1, col=1)
    if show_e50:
        fig.add_trace(go.Scatter(x=dv.index, y=dv["EMA50"], line=dict(color="#f59e0b",width=1,dash="dot"), name="EMA50"), row=1, col=1)
    if show_bb:
        fig.add_trace(go.Scatter(x=dv.index, y=dv["BB_U"], line=dict(color="#475569",width=1,dash="dot"), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=dv.index, y=dv["BB_D"], line=dict(color="#475569",width=1,dash="dot"),
            showlegend=False, fill="tonexty", fillcolor="rgba(71,85,105,0.04)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=dv.index, y=dv["VWAP"], line=dict(color="#f59e0b",width=1.5,dash="dot"), name="VWAP"), row=1, col=1)

    # Key levels
    for lv,c,d,lb in [
        (vwap,  "#f59e0b","dot",      "VWAP"),
        (poc,   "#facc15","solid",    "POC"),
        (or_hi, "#10b981","dash",     "OR Hi"),
        (or_lo, "#ef4444","dash",     "OR Lo"),
        (pdh,   "#38bdf8","longdash", "PDH"),
        (pdl,   "#f87171","longdash", "PDL"),
        (mpain, "#a78bfa","dot",      "Pain"),
    ]:
        fig.add_hline(y=lv, line_color=c, line_dash=d, line_width=1,
            annotation_text=lb, annotation_font_size=8,
            annotation_font_color=c, annotation_position="right", row=1, col=1)

    # Active SL / T1
    if lk["signal"] and lock_on:
        try: fig.add_hline(y=float(lk["sl"]), line_color="#ef4444", line_dash="dash", line_width=1.5,
                annotation_text="SL", annotation_font_color="#ef4444", annotation_font_size=8,
                annotation_position="right", row=1, col=1)
        except: pass
        try: fig.add_hline(y=float(lk["t1"]), line_color="#10b981", line_dash="dash", line_width=1.5,
                annotation_text="T1", annotation_font_color="#10b981", annotation_font_size=8,
                annotation_position="right", row=1, col=1)
        except: pass

    # Buy / Sell arrows
    bp = dv[dv["be"]]; sp = dv[dv["se"]]
    if len(bp):
        fig.add_trace(go.Scatter(x=bp.index, y=bp["Low"]*0.9988, mode="markers",
            marker=dict(symbol="triangle-up", size=9, color="#10b981",
            line=dict(color="#fff",width=0.8)), name="▲ Buy"), row=1, col=1)
    if len(sp):
        fig.add_trace(go.Scatter(x=sp.index, y=sp["High"]*1.0012, mode="markers",
            marker=dict(symbol="triangle-down", size=9, color="#ef4444",
            line=dict(color="#fff",width=0.8)), name="▼ Sell"), row=1, col=1)

    # ── Row 2: RSI ────────────────────────────────────────────────────────────────
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.05)",   line_width=0, row=2, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(16,185,129,0.05)",  line_width=0, row=2, col=1)
    fig.add_trace(go.Scatter(x=dv.index, y=dv["RSI"],
        line=dict(color="#38bdf8",width=1.3), name="RSI",
        fill="tozeroy", fillcolor="rgba(56,189,248,0.04)"), row=2, col=1)
    for yy, c in [(70,"#ef4444"),(50,"#334155"),(30,"#10b981")]:
        fig.add_hline(y=yy, line_color=c, line_dash="dash", line_width=1,
            annotation_text=str(yy), annotation_font_size=7,
            annotation_font_color=c, annotation_position="right", row=2, col=1)

    # ── Row 3: MACD ───────────────────────────────────────────────────────────────
    fig.add_trace(go.Bar(x=dv.index, y=dv["MH"],
        marker_color=["rgba(16,185,129,0.75)" if v>=0 else "rgba(239,68,68,0.75)" for v in dv["MH"]],
        name="Hist"), row=3, col=1)
    fig.add_trace(go.Scatter(x=dv.index, y=dv["MACD"], line=dict(color="#3b82f6",width=1.2), name="MACD"), row=3, col=1)
    fig.add_trace(go.Scatter(x=dv.index, y=dv["MS"],   line=dict(color="#f59e0b",width=1.2), name="Sig"),  row=3, col=1)
    fig.add_hline(y=0, line_color="#1e293b", line_width=1, row=3, col=1)

    # ── Layout ────────────────────────────────────────────────────────────────────
    _ax = dict(gridcolor="#111827", gridwidth=1, tickfont=dict(size=8, color="#4a6080"), zeroline=False)
    fig.update_layout(
        height=price_h,
        template="plotly_dark",
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#0b0f19",
        margin=dict(t=6, b=4, l=0, r=48),
        showlegend=True,
        legend=dict(orientation="h", y=1.01, x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(size=8, color="#4a6080"), itemwidth=40),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#0f141f", bordercolor="#1f2d45",
                        font=dict(size=10, color="#dde3ee")),
        dragmode="pan",
        # x-axes
        xaxis  = dict(**_ax, showticklabels=False),
        xaxis2 = dict(**_ax, showticklabels=False),
        xaxis3 = dict(**_ax,
            rangeslider=dict(visible=False),
            rangeselector=dict(
                bgcolor="#0f141f", activecolor="#1e293b",
                font=dict(size=8, color="#6e7f9c"),
                buttons=[
                    dict(count=1, label="1H", step="hour", stepmode="backward"),
                    dict(count=4, label="4H", step="hour", stepmode="backward"),
                    dict(count=1, label="1D", step="day",  stepmode="backward"),
                    dict(step="all", label="All")
                ]
            )
        ),
        # y-axes (let subplots assign domains automatically)
        yaxis  = dict(**_ax, side="right"),
        yaxis2 = dict(**_ax, side="right", range=[15,85]),
        yaxis3 = dict(**_ax, side="right"),
    )
    fig.update_xaxes(showspikes=True, spikecolor="#334155", spikethickness=1, spikesnap="cursor")
    fig.update_yaxes(showspikes=True, spikecolor="#334155", spikethickness=1)

    st.plotly_chart(fig, use_container_width=True,
        config={"scrollZoom":True, "displayModeBar":True, "displaylogo":False,
                "modeBarButtonsToAdd":["pan2d","zoom2d","autoScale2d","resetScale2d"],
                "modeBarButtonsToRemove":["toImage"]})

    # ── AI Prediction ───────────────────────────────────────────────────────────
    st.markdown('<div class="sec">AI Confluence</div>', unsafe_allow_html=True)
    ai_c=st.columns(4)
    ai_c[0].metric("Score",f"{ai_prob}%"); ai_c[1].metric("Bias",trend)
    ai_c[2].metric("GEX",gex_reg);        ai_c[3].metric("OI Signal",oisig)
    if ai_prob>=75 and trend=="Bullish":   st.success(f"🟢 Very High Bullish Confluence ({ai_prob}%) — Strong Buy Setup")
    elif ai_prob>=75 and trend=="Bearish": st.error(  f"🔴 Very High Bearish Confluence ({ai_prob}%) — Strong Sell Setup")
    elif ai_prob>=55 and trend=="Bullish": st.warning(f"🟡 Moderate Bullish Confluence ({ai_prob}%) — {trend} bias, await trigger")
    elif ai_prob>=55 and trend=="Bearish": st.warning(f"🟡 Moderate Bearish Confluence ({ai_prob}%) — {trend} bias, await trigger")
    else:             st.info(   f"ℹ️ Low Confluence ({ai_prob}%) — Stand aside")
    fa,fb=af[:len(af)//2+1],af[len(af)//2+1:]
    ca,cb=st.columns(2)
    with ca: st.markdown("".join(f"<div style='font-size:10px;color:#8fa3bc;padding:1px 0'>{x}</div>" for x in fa),unsafe_allow_html=True)
    with cb: st.markdown("".join(f"<div style='font-size:10px;color:#8fa3bc;padding:1px 0'>{x}</div>" for x in fb),unsafe_allow_html=True)

    # ── OI Ladder + GEX ─────────────────────────────────────────────────────────
    if coi and poi:
        st.markdown('<div class="sec">OI Ladder  &  GEX</div>', unsafe_allow_html=True)
        oc1,oc2=st.columns(2)
        chart_bg="#0b0f19"; chart_grid="#111827"
        with oc1:
            as2=sorted(set(coi)|set(poi))
            df_oi=pd.DataFrame({"S":as2,"CO":[coi.get(s,0) for s in as2],"PO":[poi.get(s,0) for s in as2]})
            foi=go.Figure()
            foi.add_trace(go.Bar(x=df_oi["S"],y=df_oi["CO"],name="CE OI",marker_color="rgba(16,185,129,0.75)"))
            foi.add_trace(go.Bar(x=df_oi["S"],y=-df_oi["PO"],name="PE OI",marker_color="rgba(239,68,68,0.75)"))
            for xv,c,lb in [(price,"#f59e0b","Spot"),(mpain,"#a78bfa","Pain"),(zgamma,"#38bdf8","ZG")]:
                foi.add_vline(x=xv,line_color=c,line_dash="dash",annotation_text=lb,annotation_font_size=8,annotation_font_color=c)
            foi.update_layout(height=220,template="plotly_dark",paper_bgcolor=chart_bg,plot_bgcolor=chart_bg,
                barmode="relative",margin=dict(t=4,b=4,l=0,r=0),
                legend=dict(font=dict(size=8,color="#4a6080"),bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(gridcolor=chart_grid,tickfont=dict(size=7,color="#4a6080")),
                yaxis=dict(gridcolor=chart_grid,tickfont=dict(size=7,color="#4a6080"),side="right"))
            st.plotly_chart(foi,use_container_width=True,config={"displayModeBar":False})
        with oc2:
            if gex_s:
                gdf=pd.DataFrame({"S":list(gex_s.keys()),"G":list(gex_s.values())}).sort_values("S")
                fg=go.Figure()
                fg.add_trace(go.Bar(x=gdf["S"],y=gdf["G"],
                    marker_color=["rgba(16,185,129,0.75)" if v>0 else "rgba(239,68,68,0.75)" for v in gdf["G"]]))
                fg.add_vline(x=price, line_color="#f59e0b",line_dash="dash",annotation_text="Spot",annotation_font_size=8,annotation_font_color="#f59e0b")
                fg.add_vline(x=zgamma,line_color="#38bdf8",line_width=2,annotation_text="ZG",annotation_font_size=8,annotation_font_color="#38bdf8")
                col_g="#10b981" if gex_t>0 else "#ef4444"
                fg.update_layout(height=220,template="plotly_dark",paper_bgcolor=chart_bg,plot_bgcolor=chart_bg,
                    margin=dict(t=4,b=4,l=0,r=0),
                    title=dict(text=f"{gex_reg}  ({gex_t:+,.0f})",font=dict(size=9,color=col_g)),
                    xaxis=dict(gridcolor=chart_grid,tickfont=dict(size=7,color="#4a6080")),
                    yaxis=dict(gridcolor=chart_grid,tickfont=dict(size=7,color="#4a6080"),side="right"))
                st.plotly_chart(fg,use_container_width=True,config={"displayModeBar":False})
        ow=st.columns(4)
        ow[0].metric("Call Wall",str(cwall or "—")); ow[1].metric("Put Wall",str(pwall or "—"))
        ow[2].metric("Max Pain",f"{mpain:.0f}");     ow[3].metric("OI Signal",oisig)

    # ── Spreads ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec">Quick Spreads</div>', unsafe_allow_html=True)
    def _cp(K,opt): return float(clp.get(K) or plp.get(K) or bsp(price,K,T_,.05,sigma,opt))
    try:
        bcs_c=round(_cp(atm,"C")-_cp(atm+50,"C"),1); bcs_p=round(50-bcs_c,1)
        bps_c=round(_cp(atm,"P")-_cp(atm-50,"P"),1); bps_p=round(50-bps_c,1)
        ic_c =round(_cp(atm+50,"P")+_cp(atm-50,"C")-_cp(atm+100,"C")-_cp(atm-100,"P"),1)
        strd =round(_cp(atm,"C")+_cp(atm,"P"),1)
        sp1,sp2,sp3,sp4=st.columns(4)
        sp1.markdown(f"""<div class="spr">
            <div class="spr-title" style="color:#10b981">Bull Call Spread</div>
            <div style="font-size:9px;color:#4a6080;margin-bottom:3px">Buy {atm}CE · Sell {atm+50}CE</div>
            <div class="spr-row"><span>Cost</span><b>{bcs_c}</b></div>
            <div class="spr-row"><span>Max Profit</span><b>{bcs_p}</b></div>
            <div class="spr-row"><span>BEven</span><b>{atm+bcs_c:.0f}</b></div>
        </div>""",unsafe_allow_html=True)
        sp2.markdown(f"""<div class="spr">
            <div class="spr-title" style="color:#ef4444">Bear Put Spread</div>
            <div style="font-size:9px;color:#4a6080;margin-bottom:3px">Buy {atm}PE · Sell {atm-50}PE</div>
            <div class="spr-row"><span>Cost</span><b>{bps_c}</b></div>
            <div class="spr-row"><span>Max Profit</span><b>{bps_p}</b></div>
            <div class="spr-row"><span>BEven</span><b>{atm-bps_c:.0f}</b></div>
        </div>""",unsafe_allow_html=True)
        sp3.markdown(f"""<div class="spr">
            <div class="spr-title" style="color:#8b5cf6">Iron Condor</div>
            <div style="font-size:9px;color:#4a6080;margin-bottom:3px">S{atm-50}CE+S{atm+50}PE+B{atm+100}CE+B{atm-100}PE</div>
            <div class="spr-row"><span>Credit</span><b>{ic_c}</b></div>
            <div class="spr-row"><span>Range</span><b>{atm-50}–{atm+50}</b></div>
        </div>""",unsafe_allow_html=True)
        sp4.markdown(f"""<div class="spr">
            <div class="spr-title" style="color:#f59e0b">ATM Straddle</div>
            <div style="font-size:9px;color:#4a6080;margin-bottom:3px">Buy {atm}CE + Buy {atm}PE</div>
            <div class="spr-row"><span>Cost</span><b>{strd}</b></div>
            <div class="spr-row"><span>BEven</span><b>{atm-strd:.0f}–{atm+strd:.0f}</b></div>
        </div>""",unsafe_allow_html=True)
    except Exception as e:
        st.info(f"Spread calc loading... ({e})")

st.caption("v5.1 · Institutional terminal · Interactive pan/zoom chart · Signal lock · NSE live data")


# v6 marker

# Replace your Zerodha block with this (handles all errors):
try:
    from kiteconnect import KiteConnect
    api_key = st.sidebar.text_input("API Key", type="password")
    access_token_input = st.sidebar.text_input("Access Token", type="password")
    
    if api_key and access_token_input:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token_input)
        
        # Test buttons (no crashes)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Holdings", key="hold"):
                try:
                    holdings = kite.holdings()
                    st.success(f"Holdings: {len(holdings) if isinstance(holdings, list) else holdings.get('net_positions', [])}")
                except:
                    st.error("Holdings fetch failed")
        
        with col2:
            if st.button("💰 PnL", key="pnl"):
                try:
                    pnl_data = kite.profit_loss()
                    st.success(f"PnL: ₹{pnl_data.get('daily_pl', 0):.0f}")
                except:
                    st.error("PnL fetch failed")
                    
        st.success("✅ Connected!")
        
except Exception as e:
    st.info(f"Install: `pip install kiteconnect==5.0.1`\nError: {e}")
            

# ── AUTO REFRESH (CORRECT ORDER) ────────────────────────────────────────────────
st.sidebar.markdown("---")
#refresh_sec = st.sidebar.slider("Refresh (seconds)", 10, 60, 25)
refresh_sec = st.sidebar.slider("Refresh (sec)", 10, 60, 30)
auto_refresh(refresh_sec)
auto_on = st.sidebar.toggle("Auto Refresh", True)

if st.sidebar.button("🔄 Refresh Now") or st.button("🔄 Refresh Now", key="manual"):
    st.rerun()

# This MUST be after the slider — it reads refresh_sec
#if auto_on:
    st_autorefresh(interval=refresh_sec * 1000, key="nifty_auto")
    
    
    
# ADD this function (anywhere in script):
def auto_refresh(interval=30):
    """Native Streamlit auto-refresh"""
    placeholder = st.empty()
    with placeholder.container():
        st.button("🔄 Refresh Now", on_click=st.rerun)
    if st.sidebar.checkbox("Auto Refresh", True):
        st.rerun()  # Triggers every page load