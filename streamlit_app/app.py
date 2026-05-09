import json
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

MACRO_TICKERS = {"DXY": "DX-Y.NYB", "US10Y": "^TNX", "SPX": "^GSPC", "VIX": "^VIX"}


def fetch_price_data(symbol: str, trade_date: str, lookback_days: int = 180) -> pd.DataFrame:
    end = datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=1)
    start = end - timedelta(days=lookback_days)
    df = yf.download(symbol, start=start, end=end, interval="1d", progress=False)
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]).title() for c in df.columns]
    else:
        df = df.rename(columns=str.title)
    return df[["Open", "High", "Low", "Close", "Volume"]].copy()


def fetch_macro_snapshot(trade_date: str) -> str:
    end = datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=1)
    start = end - timedelta(days=20)
    parts = []
    for name, ticker in MACRO_TICKERS.items():
        try:
            df = yf.download(ticker, start=start, end=end, interval="1d", progress=False)
            if df.empty:
                parts.append(f"{name}: N/A")
                continue
            close = df["Close"]
            last = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) > 1 else last
            chg = ((last - prev) / prev * 100) if prev else 0
            parts.append(f"{name}: {last:.2f} ({chg:+.2f}%)")
        except Exception:
            parts.append(f"{name}: N/A")
    return " | ".join(parts)


def to_float(value) -> float:
    if isinstance(value, pd.Series):
        value = value.iloc[0] if not value.empty else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def add_analytics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret_1d"] = out["Close"].pct_change()
    out["sma_20"] = out["Close"].rolling(20).mean()
    out["sma_60"] = out["Close"].rolling(60).mean()
    out["vol_20_annual"] = out["ret_1d"].rolling(20).std() * (252**0.5)
    out["drawdown"] = out["Close"] / out["Close"].cummax() - 1
    return out


def summarize_metrics(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    latest_close = to_float(latest["Close"])
    start_price = to_float(df["Close"].iloc[0])
    return {
        "latest_close": latest_close,
        "latest_ret_1d": to_float(latest.get("ret_1d", 0.0)),
        "period_return": (latest_close / start_price - 1) if start_price else 0.0,
        "latest_vol_20": to_float(latest.get("vol_20_annual", 0.0)),
        "max_drawdown": to_float(df["drawdown"].min()),
        "avg_volume": to_float(df["Volume"].tail(20).mean()),
    }


def build_context(commodity: str, trade_date: str, px: pd.DataFrame, macro_note: str) -> str:
    px60 = px.tail(60)
    latest = px60.iloc[-1]
    m = summarize_metrics(px)
    ohlcv = "\n".join(
        f"{idx.strftime('%Y-%m-%d')}, O={r['Open']:.2f}, H={r['High']:.2f}, L={r['Low']:.2f}, C={r['Close']:.2f}, V={int(r['Volume'])}"
        for idx, r in px60.iterrows()
    )
    return (
        f"Commodity: {commodity}\nTrade Date: {trade_date}\n"
        f"Latest: O={latest['Open']:.2f}, H={latest['High']:.2f}, L={latest['Low']:.2f}, C={latest['Close']:.2f}, V={int(latest['Volume'])}\n"
        f"Metrics: 1D={m['latest_ret_1d']:.2%}, 60D={m['period_return']:.2%}, Vol20={m['latest_vol_20']:.2%}, MDD={m['max_drawdown']:.2%}, AvgVol={m['avg_volume']:.0f}\n"
        f"Macro Snapshot: {fetch_macro_snapshot(trade_date)}\n"
        f"User Macro Note: {macro_note}\n"
        f"Recent OHLCV:\n{ohlcv}"
    )


def ask(client: OpenAI, model: str, system: str, user: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
        max_tokens=2000,
    )
    return resp.choices[0].message.content if resp.choices else ""


def run_multi_agent_report(api_key: str, base_url: str, model: str, context: str) -> dict:
    client = OpenAI(api_key=api_key, base_url=base_url)
    technical = ask(client, model, "You are a technical analyst for energy commodities.", context)
    macro = ask(client, model, "You are a macro analyst. Focus on rates, DXY, risk sentiment, and growth.", context)
    geopolitical = ask(client, model, "You are a geopolitical risk analyst. Focus on sanctions, conflicts, shipping chokepoints, OPEC+ policy risk.", context)

    research_prompt = (
        f"Base context:\n{context}\n\nTechnical Analysis:\n{technical}\n\nMacro Analysis:\n{macro}\n\nGeopolitical Analysis:\n{geopolitical}\n\n"
        "You are the Research Manager. Produce: assumptions, scenario tree (bull/base/bear), risk limits, and action plan."
    )
    research_manager = ask(client, model, "You are the head research manager.", research_prompt)

    trader_prompt = (
        f"Context and manager plan:\n{research_manager}\n\nCreate trader proposal with entry/exit, stop loss, position sizing, and monitoring triggers."
    )
    trader_proposal = ask(client, model, "You are a senior discretionary trader.", trader_prompt)

    final_prompt = (
        f"Technical:\n{technical}\n\nMacro:\n{macro}\n\nGeopolitical:\n{geopolitical}\n\nResearch Manager:\n{research_manager}\n\nTrader Proposal:\n{trader_proposal}\n\n"
        "Provide Final Portfolio Decision: target allocation, confidence score (0-100), key risks, invalidation conditions, next review time."
    )
    final_decision = ask(client, model, "You are the CIO making final portfolio decisions.", final_prompt)

    return {
        "technical_analysis": technical,
        "macro_analysis": macro,
        "geopolitical_risk": geopolitical,
        "research_manager_plan": research_manager,
        "trader_proposal": trader_proposal,
        "final_portfolio_decision": final_decision,
    }


def report_to_markdown(commodity: str, trade_date: str, sections: dict) -> str:
    blocks = [f"# Energy Trading Multi-Agent Report\n\n- Commodity: **{commodity}**\n- Trade Date: **{trade_date}**\n"]
    title_map = {
        "technical_analysis": "Technical Analysis",
        "macro_analysis": "Macro Analysis",
        "geopolitical_risk": "Geopolitical Risk",
        "research_manager_plan": "Research Manager Plan",
        "trader_proposal": "Trader Proposal",
        "final_portfolio_decision": "Final Portfolio Decision",
    }
    for k, v in sections.items():
        blocks.append(f"## {title_map.get(k, k)}\n\n{v}\n")
    return "\n".join(blocks)


st.set_page_config(page_title="Energy Trading Agent (Streamlit)", layout="wide")
st.title("⚡ Energy Trading Agent - Multi-Agent Streamlit版")

with st.sidebar:
    st.header("模型配置")
    api_key = st.text_input("API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    base_url = st.text_input("Base URL", value=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"))
    model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "deepseek-chat"))

c1, c2 = st.columns(2)
with c1:
    commodity = st.selectbox("Commodity", list(COMMODITY_MAP.keys()), index=0)
with c2:
    trade_date = st.date_input("Trade Date", value=datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")

macro_note = st.text_area("宏观/事件补充（可选）", "OPEC+ meeting, shipping bottlenecks, sanctions headlines...")

if st.button("运行完整 Multi-Agent 分析", type="primary"):
    if not api_key:
        st.error("请先填写 API Key")
        st.stop()

    symbol = COMMODITY_MAP[commodity]
    with st.spinner("拉取数据并运行多智能体分析..."):
        px = fetch_price_data(symbol, trade_date)
        if px.empty:
            st.error("未拉取到价格数据，请检查参数。")
            st.stop()
        px = add_analytics(px)
        context = build_context(commodity, trade_date, px, macro_note)
        sections = run_multi_agent_report(api_key, base_url, model, context)
        md_report = report_to_markdown(commodity, trade_date, sections)

    metrics = summarize_metrics(px)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("最新收盘", f"{metrics['latest_close']:.2f}")
    m2.metric("1日收益", f"{metrics['latest_ret_1d']:.2%}")
    m3.metric("区间收益", f"{metrics['period_return']:.2%}")
    m4.metric("20日年化波动", f"{metrics['latest_vol_20']:.2%}")
    m5.metric("最大回撤", f"{metrics['max_drawdown']:.2%}")

    st.subheader("图表分析")
    st.line_chart(px[["Close", "sma_20", "sma_60"]].tail(120))
    st.bar_chart(px[["Volume"]].tail(120))
    st.line_chart(px[["ret_1d", "drawdown"]].tail(120))

    st.subheader("多智能体报告")
    for key, title in [
        ("technical_analysis", "Technical Analysis"),
        ("macro_analysis", "Macro Analysis"),
        ("geopolitical_risk", "Geopolitical Risk"),
        ("research_manager_plan", "Research Manager Plan"),
        ("trader_proposal", "Trader Proposal"),
        ("final_portfolio_decision", "Final Portfolio Decision"),
    ]:
        with st.expander(title, expanded=(key == "final_portfolio_decision")):
            st.markdown(sections[key])

    st.download_button(
        "下载 Markdown 报告",
        data=md_report,
        file_name=f"energy_report_{commodity}_{trade_date}.md",
        mime="text/markdown",
    )
    st.download_button(
        "下载 JSON 报告",
        data=json.dumps({"commodity": commodity, "trade_date": trade_date, **sections}, ensure_ascii=False, indent=2),
        file_name=f"energy_report_{commodity}_{trade_date}.json",
        mime="application/json",
    )
