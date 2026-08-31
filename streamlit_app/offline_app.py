import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from offline_analysis import (
    add_price_analytics,
    generate_offline_report,
    load_price_file,
    markdown_to_pdf_bytes,
    report_to_markdown,
    save_offline_report,
    summarize_price,
)
from supplemental_data import (
    build_supplemental_profile,
    parse_supplemental_workbook,
    supplemental_profile_to_text,
)


COMMODITIES = ["LPG", "BRENT", "WTI", "JKM", "BU", "FU", "LU"]


def load_offline_history() -> list[Path]:
    history_dir = Path("streamlit_app/offline_history")
    if not history_dir.exists():
        return []
    return sorted(history_dir.glob("*.json"), reverse=True)


st.set_page_config(page_title="Energy Trading Agent Offline", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: #08111f;
        color: #e6edf7;
    }
    h1, h2, h3 {
        color: #8bd3ff !important;
        letter-spacing: 0;
    }
    div[data-testid="stMetric"] {
        background: rgba(14, 25, 42, 0.86);
        border: 1px solid rgba(139, 211, 255, 0.35);
        border-radius: 8px;
        padding: 10px;
    }
    .stButton > button {
        background: #0b72b9 !important;
        color: white !important;
        border: 0 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Energy Trading Agent Offline")
st.caption("Single-machine energy commodity research assistant for local files and competition demos.")

with st.sidebar:
    st.header("Offline Runtime")
    st.success("Network/API calls disabled by design.")
    st.write("Data source: local CSV/XLSX uploads")
    st.write("Model source: built-in report rules")

c1, c2 = st.columns(2)
with c1:
    commodity = st.selectbox("Commodity", COMMODITIES, index=0)
with c2:
    trade_date = st.date_input("Trade Date", value=datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")

macro_note = st.text_area("Macro / Event Notes", "输入利率、美元、OPEC+、国内政策、产业会议等离线人工备注。")
geopolitical_note = st.text_area("Geopolitical / Policy / Shipping Notes", "输入制裁、冲突、航运、港口、装置扰动等事件。")
analyst_note = st.text_area("Analyst Override Notes", "输入研究员对本周数据的人工判断、异常值说明或需要重点复核的指标。")

price_file = st.file_uploader("Local price history CSV/XLSX", type=["csv", "xlsx"])
supplemental_file = st.file_uploader("Supplemental weekly data workbook XLSX", type=["xlsx"])

price = pd.DataFrame()
supplemental_context = ""
supplemental_profile = pd.DataFrame()
supplemental_metadata = {}

if price_file is not None:
    try:
        price = load_price_file(price_file.getvalue(), price_file.name)
        price = add_price_analytics(price)
        st.success(f"Loaded {len(price):,} local price rows.")
        st.dataframe(price.tail(10), use_container_width=True)
    except Exception as exc:
        st.error(f"Local price file parsing failed: {type(exc).__name__}: {exc}")
        price = pd.DataFrame()

if supplemental_file is not None:
    try:
        supplemental_df, supplemental_metadata = parse_supplemental_workbook(supplemental_file.getvalue(), commodity)
        supplemental_profile = build_supplemental_profile(supplemental_df)
        supplemental_context = supplemental_profile_to_text(supplemental_profile, supplemental_metadata)
        if supplemental_profile.empty:
            st.warning("Workbook parsed, but no usable numeric indicator series were detected.")
        else:
            st.success(
                f"Parsed {len(supplemental_df):,} normalized records across "
                f"{len(supplemental_metadata.get('parsed_blocks', []))} indicator groups."
            )
            st.dataframe(supplemental_profile, use_container_width=True, hide_index=True)
            with st.expander("Parsed Indicator Groups"):
                st.json(supplemental_metadata.get("parsed_blocks", [])[:40])
    except Exception as exc:
        st.error(f"Supplemental workbook parsing failed: {type(exc).__name__}: {exc}")
        supplemental_profile = pd.DataFrame()

if st.button("Run Offline Multi-Agent Report", type="primary"):
    if price.empty and supplemental_profile.empty:
        st.error("Please upload local price history or supplemental weekly data first.")
        st.stop()

    sections = generate_offline_report(
        commodity=commodity,
        trade_date=trade_date,
        price=price,
        supplemental_profile=supplemental_profile,
        macro_note=macro_note,
        geopolitical_note=geopolitical_note,
        analyst_note=analyst_note,
    )
    md_report = report_to_markdown(
        commodity,
        trade_date,
        sections,
        title="Offline Energy Trading Multi-Agent Report",
    )

    if not price.empty:
        metrics = summarize_price(price)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Latest Close", f"{metrics['latest_close']:.2f}")
        m2.metric("1D Return", f"{metrics['ret_1d']:.2%}")
        m3.metric("20D Return", f"{metrics['ret_20d']:.2%}")
        m4.metric("20D Ann. Vol", f"{metrics['vol_20_annual']:.2%}")
        m5.metric("Max Drawdown", f"{metrics['max_drawdown']:.2%}")

        st.subheader("Local Quant Charts")
        st.line_chart(price[["Close", "sma_20", "sma_60"]].tail(120))
        st.bar_chart(price[["Volume"]].tail(120))
        st.line_chart(price[["ret_1d", "drawdown"]].tail(120))

    st.subheader("Offline Multi-Agent Report")
    for key, title in [
        ("supplemental_data_analysis", "Supplemental Data Analysis"),
        ("technical_analysis", "Technical Analysis"),
        ("macro_analysis", "Macro Analysis"),
        ("geopolitical_risk", "Geopolitical Risk"),
        ("research_manager_plan", "Research Manager Plan"),
        ("trader_proposal", "Trader Proposal"),
        ("final_portfolio_decision", "Final Portfolio Decision"),
    ]:
        with st.expander(title, expanded=(key == "final_portfolio_decision")):
            st.markdown(sections[key])

    pdf_bytes = markdown_to_pdf_bytes(md_report)
    md_path, json_path = save_offline_report(commodity, trade_date, sections, md_report)

    st.download_button(
        "Download Markdown",
        data=md_report,
        file_name=f"offline_energy_report_{commodity}_{trade_date}.md",
        mime="text/markdown",
    )
    st.download_button(
        "Download JSON",
        data=json.dumps({"commodity": commodity, "trade_date": trade_date, **sections}, ensure_ascii=False, indent=2),
        file_name=f"offline_energy_report_{commodity}_{trade_date}.json",
        mime="application/json",
    )
    st.download_button(
        "Export PDF",
        data=pdf_bytes,
        file_name=f"offline_energy_report_{commodity}_{trade_date}.pdf",
        mime="application/pdf",
    )
    st.success(f"Saved offline archive: {md_path.name} / {json_path.name}")

st.divider()
st.subheader("Offline Report Archive")
files = load_offline_history()
if not files:
    st.caption("No offline reports yet.")
else:
    selected = st.selectbox("Select Offline Historical Report", [f.name for f in files])
    target = next((f for f in files if f.name == selected), None)
    if target:
        data = json.loads(target.read_text(encoding="utf-8"))
        st.write({"commodity": data.get("commodity"), "trade_date": data.get("trade_date")})
        with st.expander("View Offline Report JSON"):
            st.json(data)
