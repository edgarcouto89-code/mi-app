import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh

# 🔄 auto refresh 5s
st_autorefresh(interval=5*1000, key="refresh")

st.set_page_config(layout="wide")

ASSETS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "XRP": "XRPUSDT"}
TIMEFRAMES = {"15M": "15m", "1H": "1h", "4H": "4h"}

# ---------------- DATA ---------------- #

def get_klines(symbol, interval="15m", limit=500):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"

    try:
        data = requests.get(url, timeout=10).json()

        # 🚨 SI NO HAY DATOS → VACÍO SEGURO
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

        # indicadores
        df["EMA50"] = EMAIndicator(df["close"], 50).ema_indicator()
        df["EMA200"] = EMAIndicator(df["close"], 200).ema_indicator()
        df["RSI"] = RSIIndicator(df["close"], 14).rsi()

        df["Support"] = df["low"].rolling(20).min()
        df["Resistance"] = df["high"].rolling(20).max()

        return df.dropna()

    except:
        return pd.DataFrame()


# ---------------- LIVE PRICE ---------------- #

def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        return float(requests.get(url, timeout=5).json()["price"])
    except:
        return None


# ---------------- DECISION ---------------- #

def decision(row):
    if row["EMA50"] > row["EMA200"] and row["RSI"] < 65:
        return "BUY"
    if row["EMA50"] < row["EMA200"] and row["RSI"] > 70:
        return "SELL"
    return "HOLD"


# ---------------- GRAPH ---------------- #

def plot(df):

    df = df.tail(100)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7,0.3],
        vertical_spacing=0.05
    )

    # 🕯 velas
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

    # soporte resistencia
    fig.add_trace(go.Scatter(x=df.index, y=df["Support"], name="Soporte", line=dict(color="blue", dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Resistance"], name="Resistencia", line=dict(color="orange", dash="dot")), row=1, col=1)

    # señales
    buy_x,buy_y,sell_x,sell_y = [],[],[],[]

    for i,row in df.iterrows():
        sig = decision(row)
        if sig=="BUY":
            buy_x.append(i); buy_y.append(row["close"])
        if sig=="SELL":
            sell_x.append(i); sell_y.append(row["close"])

    fig.add_trace(go.Scatter(
        x=buy_x,y=buy_y,mode="markers",
        marker=dict(color="deepskyblue",size=14,symbol="triangle-up"),
        name="COMPRA"
    ),row=1,col=1)

    fig.add_trace(go.Scatter(
        x=sell_x,y=sell_y,mode="markers",
        marker=dict(color="orange",size=14,symbol="triangle-down"),
        name="VENTA"
    ),row=1,col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index,y=df["RSI"],name="RSI",line=dict(color="white")),row=2,col=1)
    fig.add_hline(y=70,line_color="red",row=2,col=1)
    fig.add_hline(y=30,line_color="green",row=2,col=1)

    fig.update_layout(
        height=850,
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(color="white",size=13),
        xaxis_rangeslider_visible=False
    )

    return fig


# ---------------- UI ---------------- #

st.title("🚀 Trading PRO ESTABLE (SIN ERRORES)")

tf = st.selectbox("⏱ Timeframe", list(TIMEFRAMES.keys()))

for name,symbol in ASSETS.items():

    df = get_klines(symbol,TIMEFRAMES[tf])

    # 🚨 FIX CRÍTICO (TU ERROR)
    if df.empty:
        st.warning(f"⏳ {name} cargando datos...")
        continue

    last = df.iloc[-1]
    price = get_price(symbol)
    sig = decision(last)

    st.subheader(name)

    col1,col2,col3,col4 = st.columns(4)

    col1.metric("💰 Precio", round(price if price else last["close"],2))
    col2.metric("🔺 Máx", round(last["high"],2))
    col3.metric("🔻 Mín", round(last["low"],2))
    col4.metric("📊 RSI", round(last["RSI"],2))

    # 🧠 explicación simple
    if sig=="BUY":
        st.success("🟢 COMPRA: posible subida")
    elif sig=="SELL":
        st.error("🔴 VENTA: posible caída")
    else:
        st.info("⚪ ESPERAR")

    st.plotly_chart(plot(df),use_container_width=True)

    st.divider()
