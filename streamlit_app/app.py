import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf
from openai import OpenAI

COMMODITY_MAP = {
    "BRENT": "BZ=F",
    "WTI": "CL=F",
    "HH": "NG=F",
    "TTF": "TTF=F",
    "JKM": "JKM=F",
    "LPG": "LPG=F",
}

SYSTEM_PROMPT = (
    "You are a senior energy trading analyst. Based on market data and macro context, "
    "provide: technical view, supply-demand view, macro view, and final trading decision. "
    "Use concise markdown with bullets and one summary table."
)


def fetch_price_data(symbol: str, trade_date: str, lookback_days: int = 180) -> pd.DataFrame:
    end = datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=1)
    start = end - timedelta(days=lookback_days)
    df = yf.download(symbol, start=start, end=end, interval="1d", progress=False)
    if df.empty:
        return df
    df = df.rename(columns=str.title)
    return df[["Open", "High", "Low", "Close", "Volume"]].copy()


def add_analytics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret_1d"] = out["Close"].pct_change()
    out["sma_20"] = out["Close"].rolling(20).mean()
    out["sma_60"] = out["Close"].rolling(60).mean()
    out["vol_20_annual"] = out["ret_1d"].rolling(20).std() * (252 ** 0.5)
    rolling_max = out["Close"].cummax()
    out["drawdown"] = out["Close"] / rolling_max - 1
    return out


def summarize_metrics(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    start_price = df["Close"].iloc[0]
    period_return = latest["Close"] / start_price - 1
    return {
        "latest_close": float(latest["Close"]),
        "latest_ret_1d": float(latest["ret_1d"]) if pd.notna(latest["ret_1d"]) else 0.0,
        "period_return": float(period_return),
        "latest_vol_20": float(latest["vol_20_annual"]) if pd.notna(latest["vol_20_annual"]) else 0.0,
        "max_drawdown": float(df["drawdown"].min()) if "drawdown" in df else 0.0,
        "avg_volume": float(df["Volume"].tail(20).mean()),
    }


def build_context(commodity: str, trade_date: str, px: pd.DataFrame, macro_text: str) -> str:
    if px.empty:
        return (
            f"Commodity: {commodity}\n"
            f"Trade Date: {trade_date}\n"
            "No price data available\n"
            f"Macro: {macro_text}"
        )

    px60 = px.tail(60)
    latest = px60.iloc[-1]
    metrics = summarize_metrics(px)

    ohlcv_lines = []
    for idx, row in px60.iterrows():
        ohlcv_lines.append(
            f"{idx.strftime('%Y-%m-%d')}, O={row['Open']:.2f}, H={row['High']:.2f}, L={row['Low']:.2f}, C={row['Close']:.2f}, V={int(row['Volume'])}"
        )

    quant_summary = (
        f"1D Return={metrics['latest_ret_1d']:.2%}, "
        f"60D Return={metrics['period_return']:.2%}, "
        f"20D Annualized Vol={metrics['latest_vol_20']:.2%}, "
        f"Max Drawdown={metrics['max_drawdown']:.2%}, "
        f"20D Avg Volume={metrics['avg_volume']:.0f}"
    )

    return (
        f"Commodity: {commodity}\n"
        f"Trade Date: {trade_date}\n"
        f"Latest: O={latest['Open']:.2f}, H={latest['High']:.2f}, L={latest['Low']:.2f}, C={latest['Close']:.2f}, V={int(latest['Volume'])}\n"
        f"Quant Summary: {quant_summary}\n"
        f"Macro: {macro_text}\n"
        "Recent OHLCV:\n"
        + "\n".join(ohlcv_lines)
    )


def run_llm_analysis(api_key: str, base_url: str, model: str, context: str) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        temperature=0.3,
        max_tokens=2500,
    )
    return resp.choices[0].message.content if resp.choices else "No response"


st.set_page_config(page_title="Energy Trading Agent (Streamlit)", layout="wide")
st.title("⚡ Energy Trading Agent - Streamlit 版本")
st.caption("增强版：增加收益、波动率、回撤、均线与成交量可视化分析。")

with st.sidebar:
    st.header("模型配置")
    api_key = st.text_input("API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    base_url = st.text_input("Base URL", value=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"))
    model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "deepseek-chat"))

col1, col2 = st.columns(2)
with col1:
    commodity = st.selectbox("Commodity", list(COMMODITY_MAP.keys()), index=0)
with col2:
    trade_date = st.date_input(
        "Trade Date", value=datetime.utcnow().date() - timedelta(days=1)
    ).strftime("%Y-%m-%d")

macro_context = st.text_area(
    "宏观补充信息（可选）", value="DXY, US10Y, SPX, VIX trend notes...", height=100
)

if st.button("运行分析", type="primary"):
    if not api_key:
        st.error("请先填写 API Key")
    else:
        symbol = COMMODITY_MAP[commodity]
        with st.spinner("拉取行情并生成分析中..."):
            px = fetch_price_data(symbol, trade_date)
            if px.empty:
                st.error("未拉取到价格数据，请检查品种或日期。")
                st.stop()
            px = add_analytics(px)
            context = build_context(commodity, trade_date, px, macro_context)
            report = run_llm_analysis(api_key, base_url, model, context)

        metrics = summarize_metrics(px)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("最新收盘", f"{metrics['latest_close']:.2f}")
        m2.metric("1日收益", f"{metrics['latest_ret_1d']:.2%}")
        m3.metric("区间收益", f"{metrics['period_return']:.2%}")
        m4.metric("20日年化波动", f"{metrics['latest_vol_20']:.2%}")
        m5.metric("最大回撤", f"{metrics['max_drawdown']:.2%}")

        st.subheader("分析报告")
        st.markdown(report)

        st.subheader("价格与均线")
        st.line_chart(px[["Close", "sma_20", "sma_60"]].tail(120))

        st.subheader("成交量")
        st.bar_chart(px[["Volume"]].tail(120))

        st.subheader("收益率与回撤")
        st.line_chart(px[["ret_1d", "drawdown"]].tail(120))

        with st.expander("查看输入上下文"):
            st.text(context)
        with st.expander("查看明细数据"):
            st.dataframe(px.tail(120))
