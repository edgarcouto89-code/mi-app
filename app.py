import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh

# 🔄 refresh seguro (NO agresivo)
st_autorefresh(interval=15 * 1000, key="refresh")

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

# ---------------- BINANCE ROBUSTO ---------------- #

def fetch_binance(symbol, interval, limit=200):

    url = "https://api.binance.com/api/v3/klines"

    for attempt in range(3):  # 🔥 retry automático
        try:
            r = requests.get(
                url,
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                },
                timeout=8
            )

            if r.status_code != 200:
                time.sleep(1)
                continue

            data = r.json()

            if isinstance(data, list) and len(data) >= 30:
                return data

        except:
            time.sleep(1)

    return []


# ---------------- DATA ---------------- #

@st.cache_data(ttl=10)
def get_data(symbol, interval):

    data = fetch_binance(symbol, interval)

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","trades","taker_base","taker_quote","ignore"
    ])

    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df.set_index("time", inplace=True)

    for col in ["open","high","low","close","volume"]:
        df[col] = df[col].astype(float)

    # indicadores seguros
    df["EMA50"] = EMAIndicator(df["close"], 50).ema_indicator()
    df["EMA200"] = EMAIndicator(df["close"], 200).ema_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()

    df["Support"] = df["low"].rolling(20).min()
    df["Resistance"] = df["high"].rolling(20).max()

    return df.dropna()


# ---------------- DECISIÓN ---------------- #

def decision(row):
    try:
        if row["EMA50"] > row["EMA200"] and row["RSI"] < 65:
            return "BUY"
        if row["EMA50"] < row["EMA200"] and row["RSI"] > 70:
            return "SELL"
        return "HOLD"
    except:
        return "HOLD"


# ---------------- GRÁFICO ---------------- #

def plot(df):

    df_plot = df.tail(50)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3]
    )

    fig.add_trace(go.Candlestick(
        x=df_plot.index,
        open=df_plot["open"],
        high=df_plot["high"],
        low=df_plot["low"],
        close=df_plot["close"],
        name="Precio"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df_plot.index, y=df_plot["EMA50"],
        name="EMA 50",
        line=dict(color="cyan")
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df_plot.index, y=df_plot["EMA200"],
        name="EMA 200",
        line=dict(color="yellow")
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df_plot.index, y=df_plot["Support"],
        name="Soporte",
        line=dict(color="blue", dash="dot")
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df_plot.index, y=df_plot["Resistance"],
        name="Resistencia",
        line=dict(color="orange", dash="dot")
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df_plot.index, y=df_plot["RSI"],
        name="RSI",
        line=dict(color="white")
    ), row=2, col=1)

    fig.add_hline(y=70, line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_color="green", row=2, col=1)

    fig.update_layout(
        height=850,
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(color="white"),
        xaxis_rangeslider_visible=False
    )

    return fig


# ---------------- UI ---------------- #

st.title("🚀 TRADING PRO ULTRA ESTABLE (BINANCE FIXED)")

asset = st.selectbox("📊 Crypto", list(ASSETS.keys()))
tf = st.selectbox("⏱ Timeframe", list(TIMEFRAMES.keys()))

symbol = ASSETS[asset]

df = get_data(symbol, TIMEFRAMES[tf])

# 🚨 FIX FINAL
if df is None or df.empty:
    st.warning("⏳ Binance no respondió, reintentando automáticamente...")
    st.stop()

if len(df) < 30:
    st.warning(f"⏳ Esperando más datos... ({len(df)} velas)")
    st.stop()

last = df.iloc[-1]
sig = decision(last)

# ---------------- MÉTRICAS ---------------- #

col1, col2, col3, col4 = st.columns(4)

col1.metric("💰 Precio", round(last["close"], 2))
col2.metric("🔺 Máx", round(last["high"], 2))
col3.metric("🔻 Mín", round(last["low"], 2))
col4.metric("📊 RSI", round(last["RSI"], 2))

# ---------------- SEÑAL ---------------- #

if sig == "BUY":
    st.success("🟢 COMPRA")
elif sig == "SELL":
    st.error("🔴 VENTA")
else:
    st.info("⚪ ESPERAR")

# ---------------- GRÁFICO ---------------- #

st.plotly_chart(plot(df), use_container_width=True)
