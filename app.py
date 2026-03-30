import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh

# 🔄 refresh estable (NO agresivo)
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

# ---------------- DATA (ROBUSTO) ---------------- #

@st.cache_data(ttl=20)
def get_data(symbol, interval="15m", limit=200):

    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = requests.get(url, timeout=5).json()

        # 🚨 FIX CLAVE: Binance a veces devuelve pocos datos
        if not isinstance(data, list) or len(data) < 30:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=[
            "time","open","high","low","close","volume",
            "close_time","qav","trades","taker_base","taker_quote","ignore"
        ])

        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df.set_index("time", inplace=True)

        for col in ["open","high","low","close","volume"]:
            df[col] = df[col].astype(float)

        # indicadores (solo si hay suficiente data)
        if len(df) >= 50:
            df["EMA50"] = EMAIndicator(df["close"], 50).ema_indicator()
        if len(df) >= 200:
            df["EMA200"] = EMAIndicator(df["close"], 200).ema_indicator()

        if len(df) >= 14:
            df["RSI"] = RSIIndicator(df["close"], 14).rsi()
        else:
            df["RSI"] = 50

        df["Support"] = df["low"].rolling(20).min()
        df["Resistance"] = df["high"].rolling(20).max()

        return df.dropna()

    except:
        return pd.DataFrame()


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

    df_plot = df.tail(50)  # 👈 VISUAL MÁS LIMPIO

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.05
    )

    # 🕯 velas
    fig.add_trace(go.Candlestick(
        x=df_plot.index,
        open=df_plot["open"],
        high=df_plot["high"],
        low=df_plot["low"],
        close=df_plot["close"],
        name="Precio"
    ), row=1, col=1)

    # 📈 EMAs (solo si existen)
    if "EMA50" in df_plot:
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["EMA50"], name="EMA 50", line=dict(color="cyan")), row=1, col=1)

    if "EMA200" in df_plot:
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["EMA200"], name="EMA 200", line=dict(color="yellow")), row=1, col=1)

    # 📊 soporte / resistencia
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["Support"], name="Soporte", line=dict(color="blue", dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["Resistance"], name="Resistencia", line=dict(color="orange", dash="dot")), row=1, col=1)

    # 📊 RSI
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["RSI"], name="RSI", line=dict(color="white")), row=2, col=1)

    fig.add_hline(y=70, line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_color="green", row=2, col=1)

    # 🎨 estilo pro
    fig.update_layout(
        height=850,
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(color="white", size=13),
        legend=dict(font=dict(color="white")),
        xaxis_rangeslider_visible=False
    )

    return fig


# ---------------- UI ---------------- #

st.title("🚀 TRADING PRO ESTABLE (ANTI ERROR)")

asset = st.selectbox("📊 Crypto", list(ASSETS.keys()))
tf = st.selectbox("⏱ Timeframe", list(TIMEFRAMES.keys()))

symbol = ASSETS[asset]

df = get_data(symbol, TIMEFRAMES[tf])

# 🚨 FIX FINAL (ESTO EVITA TU ERROR)
if df is None or df.empty:
    st.warning("⏳ Binance no devolvió datos, reintentando...")
    st.stop()

if len(df) < 30:
    st.warning(f"⏳ Esperando datos... ({len(df)} velas recibidas)")
    st.stop()

# ✅ SEGURO
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
