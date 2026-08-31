from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd


PRICE_ALIASES = {
    "date": ["date", "datetime", "time", "trade_date", "日期", "交易日期", "时间"],
    "open": ["open", "开盘", "开盘价"],
    "high": ["high", "最高", "最高价"],
    "low": ["low", "最低", "最低价"],
    "close": ["close", "last", "settle", "结算", "收盘", "收盘价", "最新价"],
    "volume": ["volume", "vol", "成交量"],
}


def _clean_col(name) -> str:
    return str(name).strip().lower().replace(" ", "").replace("_", "")


def _find_column(columns, aliases: list[str]) -> str | None:
    normalized = {_clean_col(col): col for col in columns}
    for alias in aliases:
        key = _clean_col(alias)
        if key in normalized:
            return normalized[key]
    for key, original in normalized.items():
        if any(_clean_col(alias) in key for alias in aliases):
            return original
    return None


def load_price_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        raw = pd.read_csv(BytesIO(file_bytes))
    else:
        raw = pd.read_excel(BytesIO(file_bytes))

    mapping = {}
    for target, aliases in PRICE_ALIASES.items():
        source = _find_column(raw.columns, aliases)
        if source:
            mapping[source] = target.capitalize()

    if "Close" not in mapping.values():
        raise ValueError("本地行情文件至少需要包含 Close/收盘价/结算价 列。")

    out = raw.rename(columns=mapping)
    if "Date" not in out.columns:
        out["Date"] = range(1, len(out) + 1)
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    out = out.dropna(subset=["Date"]).sort_values("Date")

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in out.columns:
            out[col] = out["Close"] if col != "Volume" else 0
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["Close"])
    return out.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]


def add_price_analytics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret_1d"] = out["Close"].pct_change()
    out["ret_20d"] = out["Close"].pct_change(20)
    out["sma_20"] = out["Close"].rolling(20).mean()
    out["sma_60"] = out["Close"].rolling(60).mean()
    out["vol_20_annual"] = out["ret_1d"].rolling(20).std() * (252**0.5)
    out["drawdown"] = out["Close"] / out["Close"].cummax() - 1
    return out


def summarize_price(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    latest = df.iloc[-1]
    close = float(latest["Close"])
    start = float(df["Close"].iloc[0])
    return {
        "latest_close": close,
        "ret_1d": float(latest.get("ret_1d", 0) or 0),
        "ret_20d": float(latest.get("ret_20d", 0) or 0),
        "period_return": close / start - 1 if start else 0,
        "sma_20": float(latest.get("sma_20", 0) or 0),
        "sma_60": float(latest.get("sma_60", 0) or 0),
        "vol_20_annual": float(latest.get("vol_20_annual", 0) or 0),
        "max_drawdown": float(df["drawdown"].min() or 0),
        "avg_volume": float(df["Volume"].tail(20).mean() or 0),
    }


def _fmt_pct(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2%}"


def _fmt_num(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.2f}"


def _direction(score: float) -> str:
    if score >= 2.0:
        return "偏多"
    if score <= -2.0:
        return "偏空"
    return "震荡/中性"


def _confidence(score: float, signal_count: int, has_price: bool, has_supplemental: bool) -> int:
    base = 48 + min(abs(score) * 6, 28)
    base += min(signal_count, 8)
    if has_price and has_supplemental:
        base += 8
    elif has_price or has_supplemental:
        base += 3
    return int(max(35, min(88, round(base))))


def extract_fundamental_signals(profile: pd.DataFrame) -> list[dict]:
    signals = []
    if profile.empty:
        return signals

    for row in profile.itertuples(index=False):
        text = f"{row.group} {row.metric}".lower()
        change = 0 if pd.isna(row.change) else float(row.change)
        pct = None if pd.isna(row.change_pct) else float(row.change_pct)
        percentile = None if pd.isna(row.percentile) else float(row.percentile)
        score = 0.0
        label = ""

        if any(k in text for k in ["库存", "inventory", "仓单"]):
            if percentile is not None and percentile >= 0.75:
                score -= 0.8
                label = "库存处于样本偏高位置，供应压力或仓单压力偏强"
            elif percentile is not None and percentile <= 0.25:
                score += 0.8
                label = "库存处于样本偏低位置，低库存对价格形成支撑"
            if change > 0:
                score -= 0.4
            elif change < 0:
                score += 0.4

        elif any(k in text for k in ["进口利润", "进口成本", "import"]):
            if change < 0:
                score += 0.6
                label = "进口利润/进口经济性走弱，后续进口补充压力可能下降"
            elif change > 0:
                score -= 0.4
                label = "进口经济性改善，需警惕外盘货源补充压力"

        elif any(k in text for k in ["基差", "价差", "月差", "spread"]):
            if change > 0:
                score += 0.6
                label = "基差或价差走强，近端现实支撑增强"
            elif change < 0:
                score -= 0.6
                label = "基差或价差走弱，现货支撑边际降温"

        elif any(k in text for k in ["开工", "负荷", "利用率", "需求"]):
            if any(k in text for k in ["下游", "pdh", "mtbe", "烷基化", "需求"]):
                if change > 0:
                    score += 0.5
                    label = "下游开工或需求指标改善"
                elif change < 0:
                    score -= 0.5
                    label = "下游开工或需求指标走弱"
            else:
                if change > 0:
                    score -= 0.3
                    label = "供应端开工或负荷抬升"
                elif change < 0:
                    score += 0.3
                    label = "供应端开工或负荷下降"

        elif any(k in text for k in ["毛利润", "利润", "margin"]):
            if change > 0:
                score += 0.4
                label = "产业利润改善，需求承接能力边际增强"
            elif change < 0:
                score -= 0.4
                label = "产业利润压缩，需求承接能力边际走弱"

        if score:
            signals.append(
                {
                    "name": f"{row.group} | {row.metric}",
                    "latest": f"{_fmt_num(row.latest_value)} {row.unit}".strip(),
                    "period": row.latest_period,
                    "change": _fmt_num(change),
                    "change_pct": _fmt_pct(pct),
                    "percentile": _fmt_pct(percentile),
                    "score": score,
                    "label": label or "指标变化对基本面产生边际影响",
                }
            )

    return sorted(signals, key=lambda item: abs(item["score"]), reverse=True)[:12]


def extract_technical_signals(price: pd.DataFrame) -> list[dict]:
    if price.empty:
        return []
    latest = price.iloc[-1]
    signals = []
    score = 0.0

    sma20 = latest.get("sma_20")
    sma60 = latest.get("sma_60")
    close = latest.get("Close")
    ret20 = latest.get("ret_20d")
    drawdown = latest.get("drawdown")
    vol = latest.get("vol_20_annual")

    if pd.notna(sma20) and pd.notna(sma60) and sma60:
        if sma20 > sma60:
            score += 1
            signals.append({"label": "20日均线高于60日均线，趋势结构偏多", "score": 1})
        else:
            score -= 1
            signals.append({"label": "20日均线低于60日均线，趋势结构偏弱", "score": -1})

    if pd.notna(ret20):
        if ret20 > 0.03:
            score += 0.8
            signals.append({"label": f"20日动量为 {_fmt_pct(ret20)}，短中期动量偏强", "score": 0.8})
        elif ret20 < -0.03:
            score -= 0.8
            signals.append({"label": f"20日动量为 {_fmt_pct(ret20)}，短中期动量偏弱", "score": -0.8})

    if pd.notna(close) and pd.notna(sma20) and sma20:
        distance = close / sma20 - 1
        if abs(distance) > 0.08:
            signals.append({"label": f"价格偏离20日均线 {_fmt_pct(distance)}，追价风险上升", "score": -0.2 if distance > 0 else 0.2})

    if pd.notna(vol) and vol > 0.45:
        signals.append({"label": f"20日年化波动率 {_fmt_pct(vol)}，仓位需要折减", "score": 0})

    if pd.notna(drawdown) and drawdown < -0.12:
        signals.append({"label": f"当前回撤 {_fmt_pct(drawdown)}，趋势修复前保持防守", "score": -0.5})

    return signals


def generate_offline_report(
    commodity: str,
    trade_date: str,
    price: pd.DataFrame,
    supplemental_profile: pd.DataFrame,
    macro_note: str,
    geopolitical_note: str,
    analyst_note: str,
) -> dict:
    price = add_price_analytics(price) if not price.empty else price
    price_metrics = summarize_price(price)
    technical_signals = extract_technical_signals(price)
    fundamental_signals = extract_fundamental_signals(supplemental_profile)
    total_score = sum(item["score"] for item in technical_signals + fundamental_signals)
    direction = _direction(total_score)
    confidence = _confidence(total_score, len(technical_signals) + len(fundamental_signals), not price.empty, not supplemental_profile.empty)

    strongest = fundamental_signals[:5]
    technical_text = _technical_section(price_metrics, technical_signals)
    supplemental_text = _supplemental_section(supplemental_profile, strongest)
    macro_text = _macro_section(macro_note, geopolitical_note)
    research_text = _research_section(commodity, direction, confidence, technical_signals, fundamental_signals, analyst_note)
    trader_text = _trader_section(direction, confidence, price_metrics, total_score)
    final_text = _final_section(commodity, trade_date, direction, confidence, total_score, fundamental_signals)

    sections = {
        "supplemental_data_analysis": supplemental_text,
        "technical_analysis": technical_text,
        "macro_analysis": macro_text,
        "geopolitical_risk": _geopolitical_section(geopolitical_note),
        "research_manager_plan": research_text,
        "trader_proposal": trader_text,
        "final_portfolio_decision": final_text,
    }
    return sections


def _technical_section(metrics: dict, signals: list[dict]) -> str:
    if not metrics:
        return "未上传本地行情文件，离线版跳过价格技术模型；后续判断以自有基本面数据和人工事件备注为主。"
    lines = [
        f"最新收盘价为 {_fmt_num(metrics['latest_close'])}，区间收益 {_fmt_pct(metrics['period_return'])}，20日动量 {_fmt_pct(metrics['ret_20d'])}。",
        f"20日年化波动率 {_fmt_pct(metrics['vol_20_annual'])}，最大回撤 {_fmt_pct(metrics['max_drawdown'])}，近20日平均成交量 {_fmt_num(metrics['avg_volume'])}。",
    ]
    lines.extend(f"- {item['label']}" for item in signals[:6])
    return "\n".join(lines)


def _supplemental_section(profile: pd.DataFrame, signals: list[dict]) -> str:
    if profile.empty:
        return "未上传补充 Excel 数据，离线版未生成自有数据增强结论。"
    lines = [f"已从本地补充数据中形成 {len(profile)} 个核心指标画像，重点观察变化幅度、样本分位和产业含义。"]
    for item in signals:
        lines.append(
            f"- {item['name']}：最新 {item['latest']}（{item['period']}），变化 {item['change']}，"
            f"变化率 {item['change_pct']}，样本分位 {item['percentile']}。{item['label']}。"
        )
    if not signals:
        lines.append("当前核心指标没有触发明显方向性规则，建议以价差、库存、利润和开工率的连续变化作为下一轮复核重点。")
    return "\n".join(lines)


def _macro_section(macro_note: str, geopolitical_note: str) -> str:
    lines = ["离线模式不联网抓取宏观数据，宏观判断来自答辩人员或研究员手工输入。"]
    if macro_note.strip():
        lines.append(f"宏观/事件备注：{macro_note.strip()}")
    else:
        lines.append("宏观备注为空，报告默认不对利率、美元、风险偏好作额外方向性加权。")
    if geopolitical_note.strip():
        lines.append(f"地缘/政策备注：{geopolitical_note.strip()}")
    return "\n".join(lines)


def _geopolitical_section(note: str) -> str:
    if not note.strip():
        return "未录入地缘、政策、航运或制裁相关事件。离线模型将其视为中性，但保留人工复核要求。"
    return (
        f"已录入事件：{note.strip()}\n"
        "需要重点判断事件是否影响进口到港、运费、区域套利窗口、装置开停工和政策预期；若事件无法量化，仓位应低于纯数据模型给出的上限。"
    )


def _research_section(
    commodity: str,
    direction: str,
    confidence: int,
    technical_signals: list[dict],
    fundamental_signals: list[dict],
    analyst_note: str,
) -> str:
    lines = [
        f"研究经理综合判断：{commodity} 当前框架为 {direction}，模型置信度 {confidence}/100。",
        "场景树：",
        f"- Bull：库存下降、进口经济性走弱、基差/月差走强，且价格维持在关键均线之上。",
        "- Base：基本面信号分化，价格围绕均线震荡，等待下一周数据确认。",
        "- Bear：库存累积、进口利润修复、下游利润或开工走弱，价格跌破短期趋势支撑。",
    ]
    if fundamental_signals:
        lines.append("主导变量：" + "；".join(item["name"] for item in fundamental_signals[:4]) + "。")
    if technical_signals:
        lines.append("技术过滤：" + "；".join(item["label"] for item in technical_signals[:3]) + "。")
    if analyst_note.strip():
        lines.append(f"人工研究备注：{analyst_note.strip()}")
    lines.append("风险限制：单一品种方向性仓位不应只依赖单周数据变化；若价格与基本面结论背离，优先降低仓位并等待下一次周度数据验证。")
    return "\n".join(lines)


def _trader_section(direction: str, confidence: int, metrics: dict, score: float) -> str:
    risk_unit = "轻仓试探"
    if confidence >= 72 and abs(score) >= 3:
        risk_unit = "中等仓位"
    elif confidence < 58:
        risk_unit = "观察或轻仓"

    if direction == "偏多":
        action = "以回调做多或多头持有为主，避免在高波动急涨后追价。"
        invalidation = "若库存继续累积、基差转弱或价格跌破20日均线，降低多头敞口。"
    elif direction == "偏空":
        action = "以反弹试空或降低多头敞口为主，避免在低位急跌后追空。"
        invalidation = "若库存去化、进口经济性恶化且基差重新走强，停止空头加仓。"
    else:
        action = "以区间交易和等待确认为主，减少方向性押注。"
        invalidation = "若价格突破区间且基本面同向确认，再切换为趋势策略。"

    stop_hint = "使用最近20日价格区间或关键均线作为止损参考。" if metrics else "使用最近人工确认的现货/期货关键价位作为止损参考。"
    return "\n".join(
        [
            f"交易建议：{action}",
            f"仓位建议：{risk_unit}，置信度 {confidence}/100。",
            f"止损与风控：{stop_hint}",
            f"失效条件：{invalidation}",
            "监控触发器：下一周库存、进口利润、基差/月差、下游开工率、产业利润，以及人工录入的政策/航运事件。",
        ]
    )


def _final_section(
    commodity: str,
    trade_date: str,
    direction: str,
    confidence: int,
    score: float,
    signals: list[dict],
) -> str:
    allocation = "0%-10%"
    if confidence >= 72:
        allocation = "20%-35%"
    elif confidence >= 60:
        allocation = "10%-20%"

    drivers = "；".join(item["label"] for item in signals[:3]) if signals else "暂无强触发的基本面规则"
    return "\n".join(
        [
            f"最终组合决策：{commodity} 在 {trade_date} 的离线模型方向为 {direction}。",
            f"目标敞口：{allocation}，方向分数 {score:.2f}，置信度 {confidence}/100。",
            f"关键依据：{drivers}。",
            "核心风险：数据模板变更导致解析偏差、单周异常值扰动、人工事件备注缺失、价格与基本面背离。",
            "复核节奏：每周数据更新后重新运行；若出现重大政策、航运、装置或宏观事件，应即时重跑。",
        ]
    )


def report_to_markdown(commodity: str, trade_date: str, sections: dict, title: str) -> str:
    title_map = {
        "supplemental_data_analysis": "Supplemental Data Analysis",
        "technical_analysis": "Technical Analysis",
        "macro_analysis": "Macro Analysis",
        "geopolitical_risk": "Geopolitical Risk",
        "research_manager_plan": "Research Manager Plan",
        "trader_proposal": "Trader Proposal",
        "final_portfolio_decision": "Final Portfolio Decision",
    }
    blocks = [f"# {title}\n\n- Commodity: **{commodity}**\n- Trade Date: **{trade_date}**\n- Mode: **Single-machine Offline**\n"]
    for key, value in sections.items():
        blocks.append(f"## {title_map.get(key, key)}\n\n{value}\n")
    return "\n".join(blocks)


def markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for raw_line in markdown_text.splitlines():
        clean = raw_line.replace("**", "").replace("#", "").replace("\t", " ").strip()
        safe = clean.encode("latin-1", errors="replace").decode("latin-1")
        if not safe:
            safe = " "
        chunks = [safe[i : i + 120] for i in range(0, len(safe), 120)] or [" "]
        for chunk in chunks:
            pdf.multi_cell(190, 6, text=chunk)
    out = pdf.output(dest="S")
    if isinstance(out, bytearray):
        return bytes(out)
    if isinstance(out, str):
        return out.encode("latin-1", errors="replace")
    return bytes(out)


def save_offline_report(commodity: str, trade_date: str, sections: dict, markdown_text: str) -> tuple[Path, Path]:
    history_dir = Path("streamlit_app/offline_history")
    history_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    stem = f"{ts}_{commodity}_{trade_date}_offline"
    md_path = history_dir / f"{stem}.md"
    json_path = history_dir / f"{stem}.json"
    json_path.write_text(json.dumps({"commodity": commodity, "trade_date": trade_date, **sections}, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown_text, encoding="utf-8")
    return md_path, json_path
