import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh

# 🔄 refresh
st_autorefresh(interval=5*1000, key="refresh")

st.set_page_config(layout="wide")

ASSETS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "XRP": "XRPUSDT"}
TIMEFRAMES = {"15M": "15m", "1H": "1h", "4H": "4h"}

# ---------------- DATA ---------------- #

def get_klines(symbol, interval="15m", limit=500):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url, timeout=10).json()

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

# 🔴 precio live
def get_price(symbol):
    try:
        return float(requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        ).json()["price"])
    except:
        return None

# 🧠 lógica simple
def decision(row):
    if row["EMA50"] > row["EMA200"] and row["RSI"] < 65:
        return "BUY"
    if row["EMA50"] < row["EMA200"] and row["RSI"] > 70:
        return "SELL"
    return "HOLD"

# ---------------- GRAFICO ---------------- #

def plot(df):
    df = df.tail(100)

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.6,0.2,0.2],
        vertical_spacing=0.03
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

    # 📈 EMAs (EXPLICADAS)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA 50 (tendencia corta)", line=dict(color="cyan")), row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA200"], name="EMA 200 (tendencia larga)", line=dict(color="yellow")), row=1,col=1)

    # 📊 soporte resistencia
    fig.add_trace(go.Scatter(x=df.index, y=df["Support"], name="Soporte (zona compra)", line=dict(color="blue", dash="dot")), row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Resistance"], name="Resistencia (zona venta)", line=dict(color="orange", dash="dot")), row=1,col=1)

    # 🟦🟧 señales
    buy_x,buy_y,sell_x,sell_y = [],[],[],[]

    for i,r in df.iterrows():
        sig = decision(r)
        if sig=="BUY":
            buy_x.append(i); buy_y.append(r["close"])
        if sig=="SELL":
            sell_x.append(i); sell_y.append(r["close"])

    fig.add_trace(go.Scatter(
        x=buy_x,y=buy_y,mode="markers",
        marker=dict(color="deepskyblue",size=14,symbol="triangle-up"),
        name="🟦 COMPRA"
    ),row=1,col=1)

    fig.add_trace(go.Scatter(
        x=sell_x,y=sell_y,mode="markers",
        marker=dict(color="orange",size=14,symbol="triangle-down"),
        name="🟧 VENTA"
    ),row=1,col=1)

    # 📊 RSI
    fig.add_trace(go.Scatter(x=df.index,y=df["RSI"],name="RSI (fuerza)",line=dict(color="white")),row=2,col=1)
    fig.add_hline(y=70,line_color="red",row=2,col=1)
    fig.add_hline(y=30,line_color="green",row=2,col=1)

    # 📊 VOLUMEN (verde compra / rojo venta)
    colors = ["green" if df["close"].iloc[i] > df["open"].iloc[i] else "red" for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index,y=df["volume"],marker_color=colors,name="Volumen (compra/venta)"),row=3,col=1)

    # 📍 precio actual
    price = df["close"].iloc[-1]
    fig.add_hline(y=price,line_dash="dash",line_color="white",annotation_text=f"Precio: {price:.2f}",row=1,col=1)

    fig.update_layout(
        height=900,
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(color="white",size=14),
        legend=dict(font=dict(size=12)),
        xaxis_rangeslider_visible=False
    )

    return fig

# ---------------- UI ---------------- #

st.title("🚀 Trading PRO FÁCIL (para principiantes)")

tf = st.selectbox("⏱ Timeframe", list(TIMEFRAMES.keys()))

for name,symbol in ASSETS.items():

    df = get_klines(symbol,TIMEFRAMES[tf])
    price = get_price(symbol)

    last = df.iloc[-1]
    sig = decision(last)

    st.subheader(f"{name}")

    col1,col2,col3,col4 = st.columns(4)

    col1.metric("💰 Precio", round(price if price else last["close"],2))
    col2.metric("🔺 Máximo", round(last["high"],2))
    col3.metric("🔻 Mínimo", round(last["low"],2))
    col4.metric("📊 RSI", round(last["RSI"],2))

    # 🧠 explicación simple
    if sig=="BUY":
        st.success("🟢 COMPRA: tendencia alcista + oportunidad de entrada")
    elif sig=="SELL":
        st.error("🔴 VENTA: posible caída o corrección")
    else:
        st.info("⚪ ESPERAR: mercado sin dirección clara")

    st.plotly_chart(plot(df),use_container_width=True)

    st.divider()
