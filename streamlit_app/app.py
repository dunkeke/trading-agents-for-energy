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


def fetch_price_data(symbol: str, trade_date: str, lookback_days: int = 150) -> pd.DataFrame:
    end = datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=1)
    start = end - timedelta(days=lookback_days)
    df = yf.download(symbol, start=start, end=end, interval="1d", progress=False)
    if df.empty:
        return df
    df = df.rename(columns=str.title)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    return df.tail(60)


def build_context(commodity: str, trade_date: str, px: pd.DataFrame, macro_text: str) -> str:
    if px.empty:
        return f"Commodity: {commodity}\nTrade Date: {trade_date}\nNo price data available\nMacro: {macro_text}"
    latest = px.iloc[-1]
    ohlcv_lines = []
    for idx, row in px.iterrows():
        ohlcv_lines.append(
            f"{idx.strftime('%Y-%m-%d')}, O={row['Open']:.2f}, H={row['High']:.2f}, L={row['Low']:.2f}, C={row['Close']:.2f}, V={int(row['Volume'])}"
        )
    return (
        f"Commodity: {commodity}\n"
        f"Trade Date: {trade_date}\n"
        f"Latest: O={latest['Open']:.2f}, H={latest['High']:.2f}, L={latest['Low']:.2f}, C={latest['Close']:.2f}, V={int(latest['Volume'])}\n"
        f"Macro: {macro_text}\n"
        "Recent OHLCV:\n" + "\n".join(ohlcv_lines)
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
st.caption("前后端合并在一个 Streamlit 应用中，便于直接部署到 Streamlit Cloud。")

with st.sidebar:
    st.header("模型配置")
    api_key = st.text_input("API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    base_url = st.text_input("Base URL", value=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"))
    model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "deepseek-chat"))

col1, col2 = st.columns(2)
with col1:
    commodity = st.selectbox("Commodity", list(COMMODITY_MAP.keys()), index=0)
with col2:
    trade_date = st.date_input("Trade Date", value=datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")

macro_context = st.text_area(
    "宏观补充信息（可选）",
    value="DXY, US10Y, SPX, VIX trend notes...",
    height=100,
)

if st.button("运行分析", type="primary"):
    if not api_key:
        st.error("请先填写 API Key")
    else:
        symbol = COMMODITY_MAP[commodity]
        with st.spinner("拉取行情并生成分析中..."):
            px = fetch_price_data(symbol, trade_date)
            context = build_context(commodity, trade_date, px, macro_context)
            report = run_llm_analysis(api_key, base_url, model, context)

        st.subheader("分析报告")
        st.markdown(report)

        with st.expander("查看输入上下文"):
            st.text(context)

        if not px.empty:
            st.subheader("最近60日收盘价")
            st.line_chart(px["Close"])
            st.dataframe(px)
