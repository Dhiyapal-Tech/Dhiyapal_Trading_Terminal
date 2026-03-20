import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import requests
import winsound
from streamlit_autorefresh import st_autorefresh
import mibian
from scipy.stats import norm
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(layout="wide", page_title="NIFTY Institutional Terminal")
st.markdown("""
<style>
body,.stApp{background:#0a0a0a;}
.idx-card{border-radius:6px;padding:6px 10px;margin:3px 0;font-size:13px;font-weight:600;display:flex;justify-content:space-between;}
.up-card {background:#002200;color:#00ff88;border-left:3px solid #00ff88;}
.dn-card {background:#220000;color:#ff4444;border-left:3px solid #ff4444;}
.fl-card {background:#111;   color:#aaaaaa;border-left:3px solid #555;}
.news-card{border-radius:6px;padding:7px 10px;margin:4px 0;background:#0f0f1a;
           border-left:3px solid #4488ff;font-size:12px;color:#ccccff;}
.news-hot {border-left:3px solid #ff4444;background:#1a0000;}
.news-tag {font-size:10px;font-weight:700;padding:2px 6px;border-radius:3px;margin-right:5px;}
.blk-head{font-size:15px;font-weight:800;color:#ffffff;padding:5px 0;border-bottom:1px solid #333;margin-bottom:6px;}
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=30000)

# ================================================================
# WORLD & INDIA INDICES DATA
# ================================================================
WORLD_INDICES = {
    "S&P 500":   "^GSPC", "Dow Jones":  "^DJI",   "NASDAQ":    "^IXIC",
    "VIX (US)":  "^VIX",  "FTSE 100":  "^FTSE",   "DAX":       "^GDAXI",
    "CAC 40":    "^FCHI",  "Nikkei 225":"^N225",   "Hang Seng": "^HSI",
    "Shanghai":  "000001.SS","Kospi":   "^KS11",   "ASX 200":   "^AXJO",
    "SGX":       "^STI",   "Taiwan":    "^TWII",   "Crude Oil": "CL=F",
    "Gold":      "GC=F",   "Silver":    "SI=F",    "USD/INR":   "INR=X",
    "DXY":       "DX-Y.NYB","US 10Y":   "^TNX",
}

INDIA_INDICES = {
    "NIFTY 50":    "^NSEI",      "SENSEX":      "^BSESN",
    "Bank NIFTY":  "^NSEBANK",   "NIFTY IT":    "^CNXIT",
    "NIFTY Pharma":"^CNXPHARMA", "NIFTY Auto":  "^CNXAUTO",
    "NIFTY FMCG":  "^CNXFMCG",  "NIFTY Metal": "^CNXMETAL",
    "NIFTY Midcap":"^NSMIDCP",   "NIFTY Energy":"^CNXENERGY",
    "NIFTY Realty":"^CNXREALTY", "India VIX":   "^INDIAVIX",
}

@st.cache_data(ttl=30)
def fetch_indices(tickers_dict):
    results = {}
    for name, sym in tickers_dict.items():
        try:
            t    = yf.Ticker(sym)
            hist = t.history(period="2d", interval="1d")
            if len(hist) >= 2:
                prev  = float(hist["Close"].iloc[-2])
                curr  = float(hist["Close"].iloc[-1])
                chg   = curr - prev
                chgp  = (chg / prev) * 100 if prev else 0
                results[name] = {"price": curr, "change": chg, "pct": chgp, "sym": sym}
            elif len(hist) == 1:
                curr  = float(hist["Close"].iloc[-1])
                results[name] = {"price": curr, "change": 0, "pct": 0, "sym": sym}
        except:
            results[name] = {"price": None, "change": 0, "pct": 0, "sym": sym}
    return results

@st.cache_data(ttl=120)
def fetch_market_news():
    news_items = []
    # Pull news from multiple major tickers
    sources = {
        "^NSEI":  "NIFTY",
        "^BSESN": "SENSEX",
        "^GSPC":  "S&P500",
        "GC=F":   "GOLD",
        "CL=F":   "OIL",
        "INR=X":  "USD/INR",
    }
    seen_titles = set()
    for sym, label in sources.items():
        try:
            ticker = yf.Ticker(sym)
            for item in (ticker.news or [])[:4]:
                title = item.get("title","")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    ts    = item.get("providerPublishTime", 0)
                    pub   = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else ""
                    link  = item.get("link","#")
                    pub_name = item.get("publisher","")
                    news_items.append({
                        "title":  title,
                        "label":  label,
                        "time":   pub,
                        "link":   link,
                        "pub":    pub_name,
                        "ts":     ts,
                    })
        except:
            pass
    # Sort by timestamp descending
    news_items.sort(key=lambda x: x["ts"], reverse=True)
    return news_items[:25]

def render_index_card(name, d):
    if d["price"] is None:
        st.markdown(f'<div class="idx-card fl-card"><span>{name}</span><span>N/A</span></div>', unsafe_allow_html=True)
        return
    pct   = d["pct"]
    price = d["price"]
    cls   = "up-card" if pct > 0 else "dn-card" if pct < 0 else "fl-card"
    arrow = "▲" if pct > 0 else "▼" if pct < 0 else "●"
    # format price nicely
    if price > 1000:  p_str = f"{price:,.0f}"
    elif price > 10:  p_str = f"{price:,.2f}"
    else:             p_str = f"{price:.4f}"
    st.markdown(
        f'<div class="idx-card {cls}">'
        f'<span>{name}</span>'
        f'<span>{p_str} &nbsp; {arrow} {pct:+.2f}%</span>'
        f'</div>',
        unsafe_allow_html=True
    )

# Hot keywords that indicate major market moving news
HOT_KEYWORDS = ["crash","surge","rally","plunge","war","fed","rbi","rate","inflation",
                 "recession","ban","halt","circuit","breakout","gdp","budget","election",
                 "sanctions","oil","gold","dollar","rupee","nifty","sensex","banks"]

def is_hot(title):
    tl = title.lower()
    return any(k in tl for k in HOT_KEYWORDS)

def render_news_card(item):
    cls   = "news-hot" if is_hot(item["title"]) else "news-card"
    label = item["label"]
    lclr  = {"NIFTY":"#ff9900","SENSEX":"#ff6600","S&P500":"#00aaff",
              "GOLD":"#ffd700","OIL":"#aaaaaa","USD/INR":"#88ff88"}.get(label,"#ffffff")
    st.markdown(
        f'<div class="{cls}">'
        f'<span class="news-tag" style="background:{lclr}22;color:{lclr}">{label}</span>'
        f'<a href="{item["link"]}" target="_blank" style="color:inherit;text-decoration:none;">'
        f'{item["title"]}</a>'
        f'<span style="float:right;color:#666;font-size:10px">{item["time"]} · {item["pub"]}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

# ================================================================
# ▓▓▓ RENDER TOP DASHBOARD ▓▓▓
# ================================================================
st.markdown("## 🏛️ NIFTY Institutional Terminal — 3% Trader Edition")
st.markdown("---")

# Fetch all data
with st.spinner("Loading live indices & news..."):
    world_data = fetch_indices(WORLD_INDICES)
    india_data = fetch_indices(INDIA_INDICES)
    news_items = fetch_market_news()

col_world, col_india, col_news = st.columns([1.1, 1, 1.4])

with col_world:
    st.markdown('<div class="blk-head">🌍 WORLD INDICES (Live)</div>', unsafe_allow_html=True)
    for name, d in world_data.items():
        render_index_card(name, d)

with col_india:
    st.markdown('<div class="blk-head">🇮🇳 INDIA INDICES (Live)</div>', unsafe_allow_html=True)
    for name, d in india_data.items():
        render_index_card(name, d)

with col_news:
    st.markdown('<div class="blk-head">📰 MARKET MOVING NEWS</div>', unsafe_allow_html=True)
    if news_items:
        for item in news_items:
            render_news_card(item)
    else:
        st.info("Fetching news...")

st.markdown("---")

# ================================================================
# SIGNAL PANEL
# ================================================================
top_cols   = st.columns(6)
sig_box    = top_cols[0].empty()
strike_box = top_cols[1].empty()
target_box = top_cols[2].empty()
sl_box     = top_cols[3].empty()
lot_box    = top_cols[4].empty()
conf_box   = top_cols[5].empty()
hold_box   = st.empty()
st.markdown("---")

# ================================================================
# SIDEBAR
# ================================================================
with st.sidebar:
    st.header("Settings")
    mute_sound      = st.toggle("Mute Sound", False)
    enable_telegram = st.toggle("Telegram Alerts", False)
    BOT_TOKEN       = st.text_input("Bot Token", type="password")
    CHAT_ID         = st.text_input("Chat ID",   type="password")
    risk_pct        = st.slider("Risk per Trade (%)", 0.5, 2.0, 1.0) / 100
    account_size    = st.number_input("Account Size (Rs)", 100000, 10000000, 500000)
    timeframe       = st.selectbox("Timeframe", ["1m","5m","15m","30m","1h"], index=1)
    period          = st.selectbox("Period",    ["1d","5d","1mo","3mo"], index=1)
    candles_view    = st.slider("Candles in View", 20, 300, 100)
    chart_height    = st.slider("Chart Height", 500, 1200, 850)
    iv_manual       = st.slider("IV Assumption (%)", 5, 50, 15)
    st.markdown("---")
    st.caption("v3.2 — World + India Indices + News")

def alert(msg):
    if not mute_sound:
        try: winsound.Beep(2000, 700)
        except: pass
    if enable_telegram and BOT_TOKEN and CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                         data={"chat_id": CHAT_ID, "text": msg})
        except: pass

# ================================================================
# BLACK-SCHOLES HELPERS
# ================================================================
def bs_price(S, K, T, r, sigma, opt="C"):
    if T<=0: T=0.0001
    d1=(np.log(S/K)+(r+0.5*sigma**2)*T)/(sigma*np.sqrt(T)); d2=d1-sigma*np.sqrt(T)
    if opt=="C": return S*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d2)
    return K*np.exp(-r*T)*norm.cdf(-d2)-S*norm.cdf(-d1)

def bs_greeks(S, K, T, r, sigma):
    if T<=0: T=0.0001
    d1=(np.log(S/K)+(r+0.5*sigma**2)*T)/(sigma*np.sqrt(T)); d2=d1-sigma*np.sqrt(T)
    gamma=norm.pdf(d1)/(S*sigma*np.sqrt(T))
    return {"delta_c":norm.cdf(d1),"delta_p":-norm.cdf(-d1),"gamma":gamma,
            "theta_c":(-(S*norm.pdf(d1)*sigma)/(2*np.sqrt(T))-r*K*np.exp(-r*T)*norm.cdf(d2))/365,
            "vega":S*norm.pdf(d1)*np.sqrt(T)/100,
            "vanna":-norm.pdf(d1)*d2/sigma,
            "charm":-norm.pdf(d1)*(2*0.05*T-d2*sigma*np.sqrt(T))/(2*T*sigma*np.sqrt(T))}

def prob_profit(S,K,T,sigma,opt="C"):
    if T<=0: T=0.0001
    d2=(np.log(S/K)+(0.05-0.5*sigma**2)*T)/(sigma*np.sqrt(T))
    return norm.cdf(d2)*100 if opt=="C" else norm.cdf(-d2)*100

def expected_move(S,sigma,T): return S*sigma*np.sqrt(T)

# ================================================================
# NSE SESSION
# ================================================================
@st.cache_data(ttl=60)
def get_nse_session():
    s=requests.Session()
    s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                       "Referer":"https://www.nseindia.com/option-chain"})
    try: s.get("https://www.nseindia.com")
    except: pass
    return s

@st.cache_data(ttl=30)
def get_option_chain():
    try:
        s=get_nse_session()
        r=s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY")
        if r.status_code!=200: return [],None
        js=r.json(); records=js["records"]["data"]
        nearest=min(set(d["expiryDate"] for d in records),
                    key=lambda x:datetime.strptime(x,"%d-%b-%Y"))
        return [d for d in records if d["expiryDate"]==nearest],nearest
    except: return [],None

@st.cache_data(ttl=300)
def get_fii_dii():
    try:
        s=get_nse_session()
        r=s.get("https://www.nseindia.com/api/fiidiiTradeReact")
        if r.status_code==200: return r.json()
    except: pass
    return None

@st.cache_data(ttl=60)
def get_india_vix_history(period="5d",interval="5m"):
    try: return yf.Ticker("^INDIAVIX").history(period=period,interval=interval).dropna()
    except: return pd.DataFrame()

@st.cache_data(ttl=30)
def get_market_data(period,interval):
    t=yf.Ticker("^NSEI")
    return t.history(period=period,interval=interval).dropna(), \
           t.history(period="60d",interval="1d").dropna()

# ================================================================
# MARKET DATA
# ================================================================
data,daily=get_market_data(period,timeframe)
if data.empty:
    st.error("No data. Change timeframe/period."); st.stop()

price=float(data["Close"].iloc[-1])
pdh=float(daily["High"].iloc[-2]); pdl=float(daily["Low"].iloc[-2])

vix_hist=get_india_vix_history(period,timeframe)
india_vix=round(float(vix_hist["Close"].iloc[-1]),2) if not vix_hist.empty else None
prev_vix =round(float(vix_hist["Close"].iloc[-2]),2) if len(vix_hist)>1 else None
vix_signal="Fear Rising" if (india_vix and prev_vix and india_vix>prev_vix) else "Fear Subsiding"
vix_regime="Low Vol (<15)" if india_vix and india_vix<15 else \
           "Normal (15-20)" if india_vix and india_vix<20 else "High Vol (>20)"

# ================================================================
# INDICATORS
# ================================================================
data["TP"]=( data["High"]+data["Low"]+data["Close"])/3
data["Volume"]=data["Volume"].replace(0,1)
data["CumVol"]=data["Volume"].cumsum()
data["CumTPV"]=(data["TP"]*data["Volume"]).cumsum()
data["VWAP"]=data["CumTPV"]/data["CumVol"]
vwap=float(data["VWAP"].iloc[-1])

data["TR"]=data["High"]-data["Low"]
atr_s=data["TR"].rolling(14).mean()
atr=float(atr_s.iloc[-1]) if not np.isnan(float(atr_s.iloc[-1])) else float(data["TR"].mean())

data["EMA9"] =data["Close"].ewm(span=9, adjust=False).mean()
data["EMA21"]=data["Close"].ewm(span=21,adjust=False).mean()
data["EMA50"]=data["Close"].ewm(span=50,adjust=False).mean()

dr=data["Close"].diff()
data["RSI"]=100-(100/(1+(dr.clip(lower=0).rolling(14).mean()/(-dr.clip(upper=0)).rolling(14).mean())))
rsi_val=round(float(data["RSI"].iloc[-1]),1)

data["MACD"]    =data["Close"].ewm(span=12,adjust=False).mean()-data["Close"].ewm(span=26,adjust=False).mean()
data["MACD_Sig"]=data["MACD"].ewm(span=9,adjust=False).mean()
data["MACD_Hist"]=data["MACD"]-data["MACD_Sig"]
macd_val=round(float(data["MACD"].iloc[-1]),2); macd_sig=round(float(data["MACD_Sig"].iloc[-1]),2)

data["BB_Mid"] =data["Close"].rolling(20).mean()
data["BB_Std"] =data["Close"].rolling(20).std()
data["BB_Upper"]=data["BB_Mid"]+2*data["BB_Std"]
data["BB_Lower"]=data["BB_Mid"]-2*data["BB_Std"]

data["Delta"]   =np.where(data["Close"]>=data["Open"],data["Volume"],-data["Volume"])
data["CumDelta"]=data["Delta"].cumsum()
cum_delta=int(data["CumDelta"].iloc[-1])

vwap_upper1=vwap+atr*0.5; vwap_lower1=vwap-atr*0.5
opening=data.iloc[:max(1,int(len(data)*0.05))]
or_high=float(opening["High"].max()); or_low=float(opening["Low"].min()); or_mid=(or_high+or_low)/2

trend    ="Bullish" if price>vwap else ("Bearish" if price<vwap else "Neutral")
ema_trend="Bullish" if float(data["EMA9"].iloc[-1])>float(data["EMA21"].iloc[-1]) else "Bearish"

sweep_high =float(data["High"].max())>or_high and price<or_high
sweep_low  =float(data["Low"].min()) <or_low  and price>or_low
trap_signal=None
if sweep_high and trend=="Bearish": trap_signal="Bull Trap"
if sweep_low  and trend=="Bullish": trap_signal="Bear Trap"

liquidity_above=round(float(data["High"].rolling(20).max().iloc[-1]),2)
liquidity_below=round(float(data["Low"].rolling(20).min().iloc[-1]),2)

iv_rank=0
if len(daily)>=30:
    hv=float(daily["Close"].pct_change().dropna().rolling(30).std().iloc[-1])*np.sqrt(252)*100
    iv_rank=min(100,max(0,round((iv_manual-hv/2)/(hv/2)*100,1)))

# ================================================================
# OPTIONS CHAIN
# ================================================================
records,nearest_expiry=get_option_chain()
call_oi={};put_oi={};call_iv={};put_iv={}
call_vol={};put_vol={};call_lp={};put_lp={}
pcr_num=1.0;call_wall=put_wall=None;max_pain=price
gex_by_strike={};gex_total=0;zero_gamma_level=price
vanna_signal="N/A";oi_buildup_signal="N/A";all_s=[]
T_years=7/365
if nearest_expiry:
    try:
        days_to=max(1,(datetime.strptime(nearest_expiry,"%d-%b-%Y")-datetime.now()).days)
        T_years=days_to/365
    except: pass

if records:
    for r in records:
        s=r["strikePrice"];ce=r.get("CE",{});pe=r.get("PE",{})
        call_oi[s] =ce.get("openInterest",0)     or 0
        put_oi[s]  =pe.get("openInterest",0)     or 0
        call_iv[s] =ce.get("impliedVolatility",iv_manual) or iv_manual
        put_iv[s]  =pe.get("impliedVolatility",iv_manual) or iv_manual
        call_vol[s]=ce.get("totalTradedVolume",0) or 0
        put_vol[s] =pe.get("totalTradedVolume",0) or 0
        call_lp[s] =ce.get("lastPrice",0)        or 0
        put_lp[s]  =pe.get("lastPrice",0)        or 0

    tc,tp=sum(call_oi.values()),sum(put_oi.values())
    pcr_num=tp/tc if tc else 1.0
    if call_oi: call_wall=max(call_oi,key=call_oi.get)
    if put_oi:  put_wall =max(put_oi, key=put_oi.get)
    all_s=sorted(set(call_oi)|set(put_oi))
    if all_s:
        pain={s:sum(max(0,s-k)*v for k,v in call_oi.items())+sum(max(0,k-s)*v for k,v in put_oi.items()) for s in all_s}
        max_pain=min(pain,key=pain.get)
        for s in all_s:
            s_iv=max((call_iv.get(s,iv_manual)+put_iv.get(s,iv_manual))/2/100,0.01)
            g=bs_greeks(price,s,T_years,0.05,s_iv)
            gex_by_strike[s]=g["gamma"]*call_oi.get(s,0)*50*price*price*0.01 - \
                              g["gamma"]*put_oi.get(s,0)*50*price*price*0.01
            gex_total+=gex_by_strike[s]
        gvals=[gex_by_strike[s] for s in all_s]
        zero_gamma_level=all_s[min(range(len(gvals)),key=lambda i:abs(gvals[i]))]
        vt=sum(bs_greeks(price,s,T_years,0.05,max(call_iv.get(s,iv_manual)/100,0.01))["vanna"]*
               (call_oi.get(s,0)-put_oi.get(s,0))*50 for s in all_s)
        vanna_signal="Bullish" if vt>0 else "Bearish"
        ce_bd=sum(1 for s in all_s if call_oi.get(s,0) and call_vol.get(s,0)/call_oi[s]>0.3 and abs(s-price)<300)
        pe_bd=sum(1 for s in all_s if put_oi.get(s,0)  and put_vol.get(s,0)/put_oi[s]>0.3  and abs(s-price)<300)
        oi_buildup_signal="Fresh CE Buildup (Bearish)" if ce_bd>pe_bd else \
                          "Fresh PE Buildup (Bullish)" if pe_bd>ce_bd else "Neutral"

gex_regime="Positive GEX (Pinning)" if gex_total>0 else "Negative GEX (Trending)"
sigma=iv_manual/100
atm=round(price/50)*50
g_atm=bs_greeks(price,atm,T_years,0.05,sigma)
delta_call=round(g_atm["delta_c"],3); delta_put=round(g_atm["delta_p"],3)
gamma_atm=round(g_atm["gamma"],6); theta_atm=round(g_atm["theta_c"],2)
vega_atm=round(g_atm["vega"],2); vanna_atm=round(g_atm["vanna"],4)

itm_call=atm-50; itm_put=atm+50
ce_price=call_lp.get(itm_call,None) or call_lp.get(atm,None)
pe_price=put_lp.get(itm_put, None) or put_lp.get(atm,None)
if ce_price: ce_price=round(float(ce_price),2)
if pe_price: pe_price=round(float(pe_price),2)

ce_breakeven=atm+100+(ce_price or 0); pe_breakeven=atm-100-(pe_price or 0)
pop_call=round(prob_profit(price,atm+100,T_years,sigma,"C"),1)
pop_put =round(prob_profit(price,atm-100,T_years,sigma,"P"),1)
em_daily=expected_move(price,sigma,1/365); em_weekly=expected_move(price,sigma,5/365)
upper_em=price+em_daily; lower_em=price-em_daily

pcr_display=round(float(pcr_num),2)
pcr_zone="Extreme Bull" if pcr_num<0.7 else "Bullish" if pcr_num<0.9 else \
         "Neutral" if pcr_num<1.1 else "Bearish" if pcr_num<1.3 else "Extreme Bear"

fii_data=get_fii_dii(); fii_net=dii_net="N/A"
if fii_data:
    try:
        for item in fii_data:
            cat=str(item.get("category","")).upper()
            if "FII" in cat: fii_net=item.get("netValue","N/A")
            if "DII" in cat: dii_net=item.get("netValue","N/A")
    except: pass

# Rolling Greeks for chart
data["Greeks_Delta"]=data["Close"].apply(lambda s:round(bs_greeks(s,round(s/50)*50,T_years,0.05,sigma)["delta_c"],3))
data["Greeks_Gamma"]=data["Close"].apply(lambda s:round(bs_greeks(s,round(s/50)*50,T_years,0.05,sigma)["gamma"]*1e6,3))

# Market Profile
def build_market_profile(df,rows=30):
    lo,hi=float(df["Low"].min()),float(df["High"].max())
    if hi==lo: return pd.DataFrame({"Price":[lo],"Volume":[0]})
    bin_size=(hi-lo)/rows; profile={}
    for _,row in df.iterrows():
        lv=lo
        while lv<=row["High"]:
            k=round(round(lv/bin_size)*bin_size,2); profile[k]=profile.get(k,0)+row["Volume"]; lv+=bin_size
    return pd.DataFrame(list(profile.items()),columns=["Price","Volume"]).sort_values("Price")

profile=build_market_profile(data); poc=vah=val=price
if not profile.empty:
    poc=float(profile.loc[profile["Volume"].idxmax(),"Price"])
    cv=profile["Volume"].sum(); t70=cv*0.70
    ps=profile.sort_values("Volume",ascending=False); va,run=[],0
    for _,row in ps.iterrows():
        if run>=t70: break
        va.append(row["Price"]); run+=row["Volume"]
    if va: vah,val=max(va),min(va)

# ================================================================
# AI CONFLUENCE
# ================================================================
ai_score=0; ai_factors=[]
if trend=="Bullish":     ai_score+=15;ai_factors.append("VWAP Bullish")
elif trend=="Bearish":   ai_score+=15;ai_factors.append("VWAP Bearish")
if ema_trend==trend:     ai_score+=10;ai_factors.append("EMA Confirms")
if price>or_high or price<or_low: ai_score+=15;ai_factors.append("OR Break")
if sweep_high or sweep_low: ai_score+=8;ai_factors.append("Liquidity Sweep")
if trap_signal:          ai_score+=7; ai_factors.append(f"Trap:{trap_signal}")
if pcr_num<0.8:          ai_score+=15;ai_factors.append("PCR Bullish")
elif pcr_num>1.2:        ai_score+=15;ai_factors.append("PCR Bearish")
if abs(price-max_pain)<atr: ai_score+=10;ai_factors.append("Near Max Pain")
if gex_total<0:          ai_score+=12;ai_factors.append("Negative GEX (Trending)")
else:                    ai_score+=5; ai_factors.append("Positive GEX (Pinning)")
if vanna_signal==trend:  ai_score+=8; ai_factors.append("Vanna Confirms")
if india_vix and india_vix>18: ai_score+=5;ai_factors.append("High VIX")
if rsi_val>60 and trend=="Bullish":   ai_score+=8;ai_factors.append("RSI Bullish")
elif rsi_val<40 and trend=="Bearish": ai_score+=8;ai_factors.append("RSI Bearish")
if macd_val>macd_sig and trend=="Bullish":   ai_score+=7;ai_factors.append("MACD Bull Cross")
elif macd_val<macd_sig and trend=="Bearish": ai_score+=7;ai_factors.append("MACD Bear Cross")
if cum_delta>0 and trend=="Bullish":  ai_score+=5;ai_factors.append("CumDelta Bullish")
elif cum_delta<0 and trend=="Bearish":ai_score+=5;ai_factors.append("CumDelta Bearish")
ai_probability=min(ai_score,100)
bull_bias=(trend=="Bullish")and(price>or_high)and(pcr_num<1.1)and(rsi_val>50)
bear_bias=(trend=="Bearish")and(price<or_low) and(pcr_num>0.9)and(rsi_val<50)

# ================================================================
# TRADE SIGNAL
# ================================================================
TRADE_SIGNAL="NO ENTRY — Wait";STRIKE="---";TARGET="---";STOPLOSS="---"
HOLDING_TIME="---";LOT_SIZE=0;SPREAD_STRAT="";RR_RATIO="---";BREAKEVEN="---";POP="---"

if ai_probability>=65 and bull_bias:
    otm_ce=atm+100;sl_p=max(or_low,price-atr*0.7);t1=price+atr*1.5;t2=price+atr*3.0
    risk=max(price-sl_p,1); LOT_SIZE=max(1,int((account_size*risk_pct)/risk/50))
    TRADE_SIGNAL="ENTER LONG — BUY CE"; STRIKE=f"{otm_ce} CE"
    TARGET=f"T1:{t1:.0f}|T2:{t2:.0f}"; STOPLOSS=f"{sl_p:.0f}"
    RR_RATIO=f"1:{round((t1-price)/risk,1)}"
    HOLDING_TIME="15-30 min Scalp" if ai_probability<80 else "30-60 min Swing"
    SPREAD_STRAT=f"Credit: Sell {atm-50}PE/Buy {atm-150}PE"
    BREAKEVEN=f"{ce_breakeven:.0f}"; POP=f"{pop_call}%"
elif ai_probability>=65 and bear_bias:
    otm_pe=atm-100;sl_p=min(or_high,price+atr*0.7);t1=price-atr*1.5;t2=price-atr*3.0
    risk=max(sl_p-price,1); LOT_SIZE=max(1,int((account_size*risk_pct)/risk/50))
    TRADE_SIGNAL="ENTER SHORT — BUY PE"; STRIKE=f"{otm_pe} PE"
    TARGET=f"T1:{t1:.0f}|T2:{t2:.0f}"; STOPLOSS=f"{sl_p:.0f}"
    RR_RATIO=f"1:{round((price-t1)/risk,1)}"
    HOLDING_TIME="15-30 min Scalp" if ai_probability<80 else "30-60 min Swing"
    SPREAD_STRAT=f"Credit: Sell {atm+50}CE/Buy {atm+150}CE"
    BREAKEVEN=f"{pe_breakeven:.0f}"; POP=f"{pop_put}%"

sig_box.metric("Signal",    TRADE_SIGNAL); strike_box.metric("Strike",STRIKE)
target_box.metric("Target", TARGET);       sl_box.metric("Stop Loss",STOPLOSS)
lot_box.metric("Lots",      LOT_SIZE);     conf_box.metric("Confluence",f"{ai_probability}%")
hold_box.markdown(f"**Hold:** {HOLDING_TIME} | **R:R:** {RR_RATIO} | **BEven:** {BREAKEVEN} | **PoP:** {POP} | **Spread:** {SPREAD_STRAT}")
if TRADE_SIGNAL!="NO ENTRY — Wait":
    alert(f"{TRADE_SIGNAL}|{STRIKE}|SL:{STOPLOSS}|Tgt:{TARGET}|{LOT_SIZE}lots|PoP:{POP}")

# ================================================================
# KEY METRICS ROWS
# ================================================================
r1=st.columns(6)
r1[0].metric("NIFTY",     f"{price:.2f}")
r1[1].metric("VWAP",      f"{vwap:.2f}")
r1[2].metric("India VIX", f"{india_vix or 'N/A'}",delta=f"Prev:{prev_vix or 'N/A'}")
r1[3].metric("PCR",       f"{pcr_display} ({pcr_zone})")
r1[4].metric("Max Pain",  f"{max_pain:.0f}")
r1[5].metric("Zero Gamma",f"{zero_gamma_level:.0f}")

r2=st.columns(6)
r2[0].metric("RSI",       f"{rsi_val}")
r2[1].metric("MACD",      f"{macd_val}")
r2[2].metric("Cum Delta", f"{cum_delta:+,}")
r2[3].metric("Exp Move ±",f"{em_daily:.0f}")
r2[4].metric("FII Net",   f"{fii_net}")
r2[5].metric("DII Net",   f"{dii_net}")
st.divider()

st.subheader("Opening Range & Key Levels")
c1,c2,c3,c4,c5,c6=st.columns(6)
c1.metric("OR High",f"{or_high:.2f}"); c2.metric("OR Low",f"{or_low:.2f}")
c3.metric("ATR",    f"{atr:.1f}");     c4.metric("+1σ EM",f"{upper_em:.0f}")
c5.metric("-1σ EM", f"{lower_em:.0f}");c6.metric("PDH/PDL",f"{pdh:.0f}/{pdl:.0f}")
st.divider()

# ================================================================
# GEX PANEL
# ================================================================
st.subheader("GAMMA EXPOSURE (GEX) — Dealer Positioning")
g1,g2,g3,g4=st.columns(4)
g1.metric("Total GEX",  f"{gex_total:,.0f}")
g2.metric("GEX Regime", gex_regime)
g3.metric("Zero Gamma", f"{zero_gamma_level:.0f}")
g4.metric("Vanna Signal",vanna_signal)
if gex_total<0: st.error("NEGATIVE GEX: Market will TREND. Trade breakouts. Buy options.")
else:           st.success("POSITIVE GEX: Market will PIN/REVERT. Sell premium. Fade extremes.")
if gex_by_strike:
    gex_df=pd.DataFrame({"Strike":list(gex_by_strike.keys()),"GEX":list(gex_by_strike.values())}).sort_values("Strike")
    fig_gex=go.Figure()
    fig_gex.add_trace(go.Bar(x=gex_df["Strike"],y=gex_df["GEX"],
        marker_color=["#00ff88" if v>0 else "#ff4444" for v in gex_df["GEX"]],name="GEX"))
    fig_gex.add_vline(x=price,           line_color="yellow",line_dash="dash",annotation_text="Spot")
    fig_gex.add_vline(x=zero_gamma_level,line_color="violet",line_width=3,   annotation_text="ZeroGamma")
    fig_gex.update_layout(height=280,template="plotly_dark",
        title="GEX — Green=Dealers Long(Stabilise)|Red=Dealers Short(Volatile)")
    st.plotly_chart(fig_gex,width="stretch")
st.divider()

# ================================================================
# PRO CHART — 6 panels
# ================================================================
st.subheader("Pro Chart — NIFTY + RSI + MACD + CumDelta + India VIX + Greeks")
dv=data.iloc[max(0,len(data)-candles_view):]
vix_dv=vix_hist.iloc[max(0,len(vix_hist)-candles_view):] if not vix_hist.empty else pd.DataFrame()

fig=make_subplots(rows=6,cols=1,shared_xaxes=True,
    row_heights=[0.38,0.12,0.12,0.12,0.13,0.13],vertical_spacing=0.02,
    subplot_titles=("NIFTY Price","RSI","MACD","Cumulative Delta","India VIX","ATM Delta & Gamma"))

fig.add_trace(go.Candlestick(x=dv.index,open=dv["Open"],high=dv["High"],low=dv["Low"],close=dv["Close"],
    increasing=dict(line=dict(color="#00ff88",width=1),fillcolor="#00ff88"),
    decreasing=dict(line=dict(color="#ff4444",width=1),fillcolor="#ff4444"),
    whiskerwidth=0.5,name="NIFTY"),row=1,col=1)
for y,col,w,nm in [(dv["EMA9"],"cyan",1,"EMA9"),(dv["EMA21"],"magenta",1,"EMA21"),
                   (dv["EMA50"],"yellow",1,"EMA50"),(dv["VWAP"],"blue",2,"VWAP")]:
    fig.add_trace(go.Scatter(x=dv.index,y=y,line=dict(color=col,width=w),name=nm),row=1,col=1)
fig.add_trace(go.Scatter(x=dv.index,y=dv["BB_Upper"],line=dict(color="gray",width=1,dash="dot"),name="BB+"),row=1,col=1)
fig.add_trace(go.Scatter(x=dv.index,y=dv["BB_Lower"],line=dict(color="gray",width=1,dash="dot"),name="BB-",
    fill="tonexty",fillcolor="rgba(100,100,100,0.05)"),row=1,col=1)
for lvl,col,dash,lw,lbl,pos in [
    (or_high,"red","dot",1,"OR High","left"),(or_low,"lime","dot",1,"OR Low","left"),
    (poc,"yellow","solid",3,"POC","right"),(vah,"orange","dash",1,"VAH","right"),
    (val,"orange","dash",1,"VAL","right"),(pdh,"salmon","longdash",1,"PDH","right"),
    (pdl,"palegreen","longdash",1,"PDL","right"),(max_pain,"purple","solid",2,"MaxPain","right"),
    (zero_gamma_level,"violet","dot",2,"ZeroGamma","right"),
    (upper_em,"white","dot",1,"+1σ","right"),(lower_em,"white","dot",1,"-1σ","right")]:
    fig.add_hline(y=lvl,line_color=col,line_dash=dash,line_width=lw,
                  annotation_text=lbl,annotation_position=pos,row=1,col=1)

fig.add_trace(go.Scatter(x=dv.index,y=dv["RSI"],line=dict(color="cyan",width=1.5),name="RSI"),row=2,col=1)
for yy,c,d in [(70,"red","dash"),(30,"lime","dash"),(50,"gray","dot")]:
    fig.add_hline(y=yy,line_color=c,line_dash=d,row=2,col=1)

fig.add_trace(go.Scatter(x=dv.index,y=dv["MACD"],    line=dict(color="blue",  width=1.5),name="MACD"),  row=3,col=1)
fig.add_trace(go.Scatter(x=dv.index,y=dv["MACD_Sig"],line=dict(color="orange",width=1.5),name="Signal"),row=3,col=1)
fig.add_trace(go.Bar(x=dv.index,y=dv["MACD_Hist"],
    marker_color=["#00ff88" if v>=0 else "#ff4444" for v in dv["MACD_Hist"]],name="Hist"),row=3,col=1)

fig.add_trace(go.Scatter(x=dv.index,y=dv["CumDelta"],fill="tozeroy",
    line=dict(color="#00ff88" if cum_delta>=0 else "#ff4444",width=1.5),
    fillcolor="rgba(0,255,136,0.08)" if cum_delta>=0 else "rgba(255,68,68,0.08)",name="CumDelta"),row=4,col=1)
fig.add_hline(y=0,line_color="white",line_dash="dash",row=4,col=1)

if not vix_dv.empty:
    vix_colors=["#ff4444" if float(v)>20 else "#ffa500" if float(v)>15 else "#00ff88" for v in vix_dv["Close"]]
    fig.add_trace(go.Bar(x=vix_dv.index,y=vix_dv["Close"],marker_color=vix_colors,name="India VIX"),row=5,col=1)
    fig.add_hline(y=20,line_color="red", line_dash="dash",annotation_text="High(20)",row=5,col=1)
    fig.add_hline(y=15,line_color="lime",line_dash="dash",annotation_text="Low(15)", row=5,col=1)
else:
    fig.add_trace(go.Scatter(x=dv.index,y=[india_vix or 15]*len(dv),
        line=dict(color="orange",width=1),name="VIX(static)"),row=5,col=1)

fig.add_trace(go.Scatter(x=dv.index,y=dv["Greeks_Delta"],
    line=dict(color="#00aaff",width=1.5),name="ATM Delta"),row=6,col=1)
fig.add_trace(go.Scatter(x=dv.index,y=dv["Greeks_Gamma"],
    line=dict(color="#ff9900",width=1.5,dash="dash"),name="Gamma×1M"),row=6,col=1)
fig.add_hline(y=0.5,line_color="gray",line_dash="dot",annotation_text="Delta 0.5",row=6,col=1)

fig.update_layout(height=chart_height,template="plotly_dark",
    title=f"NIFTY {timeframe}|{period} | Confluence:{ai_probability}% | Trend:{trend} | VIX:{india_vix or 'N/A'} | GEX:{gex_regime[:20]}",
    showlegend=True,hovermode="x unified",
    xaxis6=dict(rangeselector=dict(bgcolor="#222",activecolor="#444",buttons=[
        dict(count=1,label="1H",step="hour",stepmode="backward"),
        dict(count=6,label="6H",step="hour",stepmode="backward"),
        dict(count=1,label="1D",step="day", stepmode="backward"),
        dict(count=5,label="5D",step="day", stepmode="backward"),
        dict(step="all",label="All")]),
        rangeslider=dict(visible=True,thickness=0.03),type="date"),
    yaxis=dict(autorange=True,fixedrange=False,side="right"),
    yaxis2=dict(title="RSI",  fixedrange=False),yaxis3=dict(title="MACD",  fixedrange=False),
    yaxis4=dict(title="Delta",fixedrange=False),yaxis5=dict(title="VIX",   fixedrange=False),
    yaxis6=dict(title="Greeks",fixedrange=False),dragmode="pan")
st.plotly_chart(fig,width="stretch",
    config={"scrollZoom":True,"modeBarButtonsToAdd":["pan2d","zoom2d","autoScale2d","resetScale2d"],
            "displayModeBar":True,"displaylogo":False})
st.caption("Row1=NIFTY|Row2=RSI|Row3=MACD|Row4=CumDelta|Row5=India VIX|Row6=ATM Greeks")
st.divider()

# Market Profile
st.subheader("Market Profile (TPO / Volume)")
if not profile.empty:
    colors=["#ff4444" if p==poc else "#ffa500" if val<=p<=vah else "#4488cc" for p in profile["Price"]]
    fig_mp=go.Figure()
    fig_mp.add_trace(go.Bar(x=profile["Volume"],y=profile["Price"],orientation="h",marker_color=colors,name="Profile"))
    fig_mp.add_hline(y=poc,line_color="red",line_width=3,annotation_text="POC")
    fig_mp.add_hline(y=vah,line_color="orange",line_dash="dash",annotation_text="VAH")
    fig_mp.add_hline(y=val,line_color="orange",line_dash="dash",annotation_text="VAL")
    fig_mp.update_layout(height=360,template="plotly_dark",title="Market Profile — Red=POC|Orange=VA|Blue=Outside")
    st.plotly_chart(fig_mp,width="stretch")
mp1,mp2,mp3=st.columns(3)
mp1.metric("POC",f"{poc:.1f}");mp2.metric("VAH",f"{vah:.1f}");mp3.metric("VAL",f"{val:.1f}")
st.divider()

# OI Ladder
if call_oi and put_oi:
    st.subheader("OI Ladder + Volume Buildup")
    all_s2=sorted(set(call_oi)|set(put_oi))
    df_oi=pd.DataFrame({"Strike":all_s2,"CE_OI":[call_oi.get(s,0) for s in all_s2],
        "PE_OI":[put_oi.get(s,0) for s in all_s2],"CE_Vol":[call_vol.get(s,0) for s in all_s2],
        "PE_Vol":[put_vol.get(s,0) for s in all_s2]})
    fig_oi=go.Figure()
    fig_oi.add_trace(go.Bar(x=df_oi["Strike"],y=df_oi["CE_OI"],name="CE OI",marker_color="green"))
    fig_oi.add_trace(go.Bar(x=df_oi["Strike"],y=-df_oi["PE_OI"],name="PE OI",marker_color="red"))
    fig_oi.add_trace(go.Scatter(x=df_oi["Strike"],y=df_oi["CE_Vol"],mode="lines",
        line=dict(color="lightgreen",dash="dash"),name="CE Vol"))
    fig_oi.add_trace(go.Scatter(x=df_oi["Strike"],y=-df_oi["PE_Vol"],mode="lines",
        line=dict(color="salmon",dash="dash"),name="PE Vol"))
    fig_oi.add_vline(x=price,           line_color="yellow",line_dash="dash",annotation_text="Spot")
    fig_oi.add_vline(x=max_pain,        line_color="purple",line_dash="dot", annotation_text="MaxPain")
    fig_oi.add_vline(x=zero_gamma_level,line_color="violet",line_width=2,    annotation_text="ZeroGamma")
    fig_oi.update_layout(height=360,template="plotly_dark",barmode="relative",
        title="OI+Volume — Dashed=Today Volume (fresh money)")
    st.plotly_chart(fig_oi,width="stretch")
    ob1,ob2,ob3=st.columns(3)
    ob1.metric("OI Buildup",oi_buildup_signal)
    ob2.metric("Call Wall (Resistance)",call_wall or "N/A")
    ob3.metric("Put Wall (Support)",    put_wall  or "N/A")
st.divider()

# Greeks Dashboard
st.subheader("Options Greeks & Risk")
gr1,gr2,gr3,gr4,gr5,gr6=st.columns(6)
gr1.metric("Delta CE",  delta_call);gr2.metric("Delta PE",  delta_put)
gr3.metric("Gamma ATM", gamma_atm); gr4.metric("Theta/day", f"-{abs(theta_atm)}")
gr5.metric("Vega",      vega_atm);  gr6.metric("Vanna",     vanna_atm)
pk1,pk2,pk3,pk4=st.columns(4)
pk1.metric("ITM Call Premium",ce_price or "N/A"); pk2.metric("ITM Put Premium",pe_price or "N/A")
pk3.metric("CE Breakeven",f"{ce_breakeven:.0f}"); pk4.metric("PE Breakeven",f"{pe_breakeven:.0f}")
pf1,pf2,pf3,pf4=st.columns(4)
pf1.metric("PoP CE+100",f"{pop_call}%"); pf2.metric("PoP PE-100",f"{pop_put}%")
pf3.metric("EM Daily ±",f"{em_daily:.0f}"); pf4.metric("EM Weekly±",f"{em_weekly:.0f}")
st.divider()

# VIX Intelligence
st.subheader("Volatility Intelligence")
v1,v2,v3,v4=st.columns(4)
v1.metric("India VIX",f"{india_vix or 'N/A'}"); v2.metric("VIX Regime",vix_regime)
v3.metric("VIX Signal",vix_signal);             v4.metric("IV Rank",   f"{iv_rank}%")
if india_vix:
    if india_vix>20: st.error("HIGH VIX: Premium expensive. Use SPREADS. Avoid naked buying.")
    elif india_vix<14: st.success("LOW VIX: Cheap premium. Good for directional BUYING.")
    else: st.info("NORMAL VIX: Use confluence score to decide direction.")
st.divider()

# FII/DII
st.subheader("FII / DII Smart Money")
f1,f2=st.columns(2)
f1.metric("FII Net",fii_net); f2.metric("DII Net",dii_net)
try:
    fv=float(str(fii_net).replace(",",""))
    if fv>0: st.success("FII BUYING — Smart money BULLISH on India")
    elif fv<0: st.error("FII SELLING — Smart money EXITING")
except: st.info("FII data loading...")
st.divider()

# AI Panel
st.subheader("AI Confluence Engine")
a1,a2,a3=st.columns(3)
a1.metric("Confluence",f"{ai_probability}%"); a2.metric("Bias",trend); a3.metric("GEX",gex_regime[:25])
if ai_probability>=75:   st.success("VERY HIGH CONFIDENCE — Strong edge")
elif ai_probability>=65: st.warning("HIGH CONFIDENCE — Valid setup")
elif ai_probability>=50: st.info("MODERATE — Wait for more confirmation")
else:                     st.error("LOW — NO TRADE. Protect capital.")
for f in ai_factors: st.write("✔",f)
if trap_signal: st.warning(f"TRAP: {trap_signal}!")
st.divider()

# Trade Plan
st.subheader("Institutional Trade Plan")
tp1,tp2=st.columns(2)
with tp1:
    st.write("**Trend:**",trend); st.write("**EMA:**",ema_trend); st.write("**RSI:**",rsi_val)
    st.write("**MACD:**",f"{macd_val} vs {macd_sig}"); st.write("**CumDelta:**",f"{cum_delta:+,}")
    st.write("**PCR:**",f"{pcr_display} ({pcr_zone})"); st.write("**GEX:**",f"{gex_total:,.0f}|{gex_regime[:20]}")
    st.write("**Vanna:**",vanna_signal); st.write("**OI:**",oi_buildup_signal)
    st.write("**VIX:**",f"{india_vix or 'N/A'} ({vix_regime})")
with tp2:
    if TRADE_SIGNAL!="NO ENTRY — Wait":
        if "LONG" in TRADE_SIGNAL: st.success(f"BUY: {TRADE_SIGNAL}")
        else:                       st.error(f"SELL: {TRADE_SIGNAL}")
        st.info(f"Strike: {STRIKE}"); st.write(f"Entry: ~{price:.0f}")
        st.write(f"SL: {STOPLOSS}"); st.write(f"Target: {TARGET}")
        st.write(f"Lots: {LOT_SIZE}"); st.write(f"R:R: {RR_RATIO}")
        st.write(f"Breakeven: {BREAKEVEN}"); st.write(f"PoP: {POP}")
        st.write(f"Hold: {HOLDING_TIME}")
        if SPREAD_STRAT: st.info(f"Spread: {SPREAD_STRAT}")
    else:
        st.warning("NO TRADE — Wait for setup. Confluence < 65%.")

st.caption("v3.2 | World Indices + India Indices + News + GEX + Greeks Chart + All institutional features")
