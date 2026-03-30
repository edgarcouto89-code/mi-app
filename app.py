import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from binance.client import Client
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh


# ⚡ AUTO REFRESH 5 SEGUNDOS
st_autorefresh(interval=5 * 1000, key="refresh")

st.set_page_config(layout="wide")

client = Client("", "")

ASSETS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "XRP": "XRPUSDT"
}

TIMEFRAMES = {
    "15M": Client.KLINE_INTERVAL_15MINUTE,
    "1H": Client.KLINE_INTERVAL_1HOUR,
    "4H": Client.KLINE_INTERVAL_4HOUR
}


# 🔴 PRECIO EN VIVO
def get_live_price(symbol):
    try:
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    except:
        return None


# 📊 DATA
@st.cache_data(ttl=60)
def get_data(symbol, interval):

    limit = 1000 if interval == Client.KLINE_INTERVAL_15MINUTE else 500

    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","trades","taker_base","taker_quote","ignore"
    ])

    df["time"] = pd.to_datetime(df["time"], unit="ms")

    for col in ["open","high","low","close","volume"]:
        df[col] = df[col].astype(float)

    df.set_index("time", inplace=True)

    df["EMA50"] = EMAIndicator(df["close"], 50).ema_indicator()
    df["EMA200"] = EMAIndicator(df["close"], 200).ema_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()

    df["Support"] = df["low"].rolling(20).min()
    df["Resistance"] = df["high"].rolling(20).max()

    return df.dropna()


# 🧠 DECISIÓN
def decision(row):

    if row["EMA50"] > row["EMA200"] and row["RSI"] < 65 and row["close"] <= row["Support"] * 1.01:
        return "BUY"

    if row["EMA50"] < row["EMA200"] and row["RSI"] > 70 and row["close"] >= row["Resistance"] * 0.99:
        return "SELL"

    return "HOLD"


# 📊 GRÁFICO PRO FINAL
def plot(df, live_price=None):

    df = df.tail(80)  # 🔥 menos velas = más claro

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.6, 0.2, 0.2]
    )

    # 🕯 VELAS
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        increasing_line_color="#00FF00",
        decreasing_line_color="#FF0000",
        name="Precio"
    ), row=1, col=1)

    # 📈 EMAs
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], line=dict(color="cyan", width=2), name="EMA 50"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA200"], line=dict(color="yellow", width=2), name="EMA 200"), row=1, col=1)

    # 🔻 SOPORTE / RESISTENCIA
    fig.add_trace(go.Scatter(x=df.index, y=df["Support"], line=dict(color="blue", dash="dot"), name="Soporte"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Resistance"], line=dict(color="orange", dash="dot"), name="Resistencia"), row=1, col=1)

    # 🟦🟧 SEÑALES
    buy_x, buy_y, sell_x, sell_y = [], [], [], []

    for i in range(len(df)):
        row = df.iloc[i]
        sig = decision(row)

        if sig == "BUY":
            buy_x.append(df.index[i])
            buy_y.append(row["close"])
        elif sig == "SELL":
            sell_x.append(df.index[i])
            sell_y.append(row["close"])

    if buy_x:
        fig.add_trace(go.Scatter(
            x=buy_x, y=buy_y,
            mode="markers",
            marker=dict(size=16, symbol="triangle-up", color="#00BFFF"),
            name="🟦 Compra"
        ), row=1, col=1)

    if sell_x:
        fig.add_trace(go.Scatter(
            x=sell_x, y=sell_y,
            mode="markers",
            marker=dict(size=16, symbol="triangle-down", color="#FFA500"),
            name="🟧 Venta"
        ), row=1, col=1)

    # 📊 RSI
    fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"],
        line=dict(color="white", width=2),
        name="RSI"
    ), row=2, col=1)

    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # 📊 VOLUMEN
    colors = ["#00FF00" if df["close"].iloc[i] > df["open"].iloc[i] else "#FF0000" for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df.index,
        y=df["volume"],
        marker_color=colors,
        name="Volumen"
    ), row=3, col=1)

    # 📍 PRECIO EN VIVO
    if live_price:
        fig.add_hline(
            y=live_price,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Precio {round(live_price,2)}",
            annotation_position="right"
        )

    # 🎨 ESTILO FINAL
    fig.update_layout(
        height=1000,  # 🔥 MÁS GRANDE
        plot_bgcolor="black",
        paper_bgcolor="black",

        font=dict(color="white", size=14),

        legend=dict(
            orientation="h",
            y=1.05,
            x=1,
            xanchor="right",
            font=dict(size=13)
        ),

        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_rangeslider_visible=False
    )

    fig.update_xaxes(showgrid=False, tickfont=dict(size=12, color="white"))
    fig.update_yaxes(gridcolor="#333", tickfont=dict(size=12, color="white"))

    return fig


# UI
st.title("🚀 Trading PRO TIEMPO REAL (CLARO)")

tf = st.selectbox("⏱ Timeframe", list(TIMEFRAMES.keys()))

for name, symbol in ASSETS.items():

    df = get_data(symbol, TIMEFRAMES[tf])

    if df is None or df.empty:
        st.error(f"❌ {name} sin datos")
        continue

    last = df.iloc[-1]
    live_price = get_live_price(symbol)

    st.subheader(f"{name} ({tf})")

    col1, col2, col3, col4 = st.columns(4)

    if live_price:
        change = live_price - last["close"]
        col1.metric("💰 Precio EN VIVO", round(live_price, 2), delta=round(change, 2))
    else:
        col1.metric("💰 Precio", round(last["close"], 2))

    col2.metric("🔺 Máx", round(last["high"], 2))
    col3.metric("🔻 Mín", round(last["low"], 2))
    col4.metric("📊 RSI", round(last["RSI"], 2))

    now = decision(last)

    if now == "BUY":
        st.success("🟦 COMPRA")
    elif now == "SELL":
        st.error("🟧 VENTA")
    else:
        st.warning("⚪ ESPERAR")

    st.plotly_chart(plot(df, live_price), use_container_width=True)

    st.divider()
