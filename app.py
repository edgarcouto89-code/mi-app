import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh

# ⚡ refresh más sano (10s en vez de 5s)
st_autorefresh(interval=10*1000, key="refresh")

st.set_page_config(layout="wide")

ASSETS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "XRP": "XRPUSDT"
}

TIMEFRAMES = {
    "15M": "15m",
    "1H": "1h",
    "4H": "4h"
}

# ---------------- DATA OPTIMIZADA ---------------- #

@st.cache_data(ttl=30)
def get_klines(symbol, interval="15m", limit=150):

    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"

    try:
        data = requests.get(url, timeout=5).json()

        if not data or isinstance(data, dict):
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=[
            "time","open","high","low","close","volume",
            "close_time","qav","trades","taker_base","taker_quote","ignore"
        ])

        df["time"] = pd.to_datetime(df["time"], unit="ms")

        for c in ["open","high","low","close","volume"]:
            df[c] = df[c].astype(float)

        df.set_index("time", inplace=True)

        # indicadores (liviano)
        df["EMA50"] = EMAIndicator(df["close"], 50).ema_indicator()
        df["EMA200"] = EMAIndicator(df["close"], 200).ema_indicator()
        df["RSI"] = RSIIndicator(df["close"], 14).rsi()

        df["Support"] = df["low"].rolling(20).min()
        df["Resistance"] = df["high"].rolling(20).max()

        return df.dropna()

    except:
        return pd.DataFrame()


# ---------------- PRECIO LIVE ---------------- #

def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        return float(requests.get(url, timeout=3).json()["price"])
    except:
        return None


# ---------------- DECISIÓN SIMPLE ---------------- #

def decision(row):
    if row["EMA50"] > row["EMA200"] and row["RSI"] < 65:
        return "BUY"
    if row["EMA50"] < row["EMA200"] and row["RSI"] > 70:
        return "SELL"
    return "HOLD"


# ---------------- GRÁFICO LIMPIO ---------------- #

def plot(df):

    df = df.tail(60)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.05
    )

    # velas
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Precio",
        increasing_line_color="lime",
        decreasing_line_color="red"
    ), row=1, col=1)

    # EMAs
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA50", line=dict(color="cyan")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA200"], name="EMA200", line=dict(color="yellow")), row=1, col=1)

    # soporte/resistencia
    fig.add_trace(go.Scatter(x=df.index, y=df["Support"], name="Soporte", line=dict(color="blue", dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Resistance"], name="Resistencia", line=dict(color="orange", dash="dot")), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="white")), row=2, col=1)
    fig.add_hline(y=70, line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_color="green", row=2, col=1)

    # estilo PRO
    fig.update_layout(
        height=800,
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(color="white", size=13),
        xaxis_rangeslider_visible=False,
        legend=dict(font=dict(color="white"))
    )

    return fig


# ---------------- UI MÁS RÁPIDA ---------------- #

st.title("⚡ Trading PRO ULTRA RÁPIDO")

# 🔥 SOLO 1 activo (clave del rendimiento)
asset = st.selectbox("📊 Crypto", list(ASSETS.keys()))
tf = st.selectbox("⏱ Timeframe", list(TIMEFRAMES.keys()))

symbol = ASSETS[asset]

df = get_klines(symbol, TIMEFRAMES[tf])

# 🚨 FIX CRÍTICO
if df.empty:
    st.warning("⏳ Cargando datos...")
    st.stop()

last = df.iloc[-1]
price = get_price(symbol)
sig = decision(last)

# métricas
col1, col2, col3, col4 = st.columns(4)

col1.metric("💰 Precio", round(price if price else last["close"], 2))
col2.metric("🔺 Máx", round(last["high"], 2))
col3.metric("🔻 Mín", round(last["low"], 2))
col4.metric("📊 RSI", round(last["RSI"], 2))

# señal simple
if sig == "BUY":
    st.success("🟢 COMPRA")
elif sig == "SELL":
    st.error("🔴 VENTA")
else:
    st.info("⚪ ESPERAR")

# gráfico
st.plotly_chart(plot(df), use_container_width=True)
