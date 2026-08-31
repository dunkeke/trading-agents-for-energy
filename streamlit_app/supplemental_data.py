import re
import unicodedata
from io import BytesIO

import pandas as pd


SUPPLEMENTAL_SHEET_MAP = {
    "BRENT": "原油",
    "WTI": "原油",
    "LPG": "液化石油气",
    "JKM": "液化石油气",
}

SUPPLEMENTAL_DATA_ROW_LIMIT = 20000
SUPPLEMENTAL_ROWS_PER_METRIC = 260


def clean_cell_text(value) -> str:
    if value is None:
        return ""
    text = "".join(ch for ch in str(value) if unicodedata.category(ch)[0] != "C")
    return " ".join(text.replace("\n", " ").split())


def parse_numeric(value):
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.replace(",", "").replace("%", "").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_block_title(title: str) -> str:
    return re.sub(r"^\d+[）.)]\s*", "", title).strip()


def is_year_label(text: str) -> bool:
    return bool(re.fullmatch(r"20\d{2}", text.strip()))


def parse_supplemental_workbook(file_bytes: bytes, commodity: str) -> tuple[pd.DataFrame, dict]:
    """Convert report-style Excel sheets into a normalized long table."""
    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    target_sheet = SUPPLEMENTAL_SHEET_MAP.get(commodity)
    sheet_names = [target_sheet] if target_sheet in wb.sheetnames else wb.sheetnames
    records = []
    parsed_blocks = []

    for sheet_name in sheet_names:
        if sheet_name in {"数据概览", "目录概览", "承诺及声明"}:
            continue
        ws = wb[sheet_name]
        values = list(ws.iter_rows(values_only=True))
        if not values:
            continue

        def value_at(row_idx: int, col_idx: int):
            if row_idx < 1 or col_idx < 1 or row_idx > len(values):
                return None
            row_values = values[row_idx - 1]
            if col_idx > len(row_values):
                return None
            return row_values[col_idx - 1]

        def nearest_above(row_idx: int, col_idx: int, prefix: str | None = None) -> str:
            for r in range(row_idx - 1, 0, -1):
                text = clean_cell_text(value_at(r, col_idx))
                if not text:
                    continue
                if prefix is None or text.startswith(prefix):
                    return text
            return ""

        def block_title(row_idx: int, col_idx: int) -> str:
            for r in range(row_idx - 1, 0, -1):
                text = clean_cell_text(value_at(r, col_idx))
                if not text or text.startswith("数据来源") or text in {"指标名称", "单位"}:
                    continue
                return text
            return ""

        header_rows = []
        max_cols = max((len(row) for row in values), default=0)
        for row_idx in range(1, min(len(values), 45) + 1):
            markers = [
                col_idx
                for col_idx in range(1, max_cols + 1)
                if clean_cell_text(value_at(row_idx, col_idx)) == "指标名称"
            ]
            if markers:
                header_rows.append((row_idx, markers))

        for header_row, starts in header_rows:
            unit_row = header_row + 1
            data_start = unit_row + 1
            for idx, start_col in enumerate(starts):
                end_col = starts[idx + 1] - 1 if idx + 1 < len(starts) else max_cols
                block_title_text = normalize_block_title(block_title(header_row, start_col))
                source = nearest_above(header_row, start_col, "数据来源")
                metrics = []

                for metric_col in range(start_col + 1, end_col + 1):
                    metric_label = clean_cell_text(value_at(header_row, metric_col))
                    unit = clean_cell_text(value_at(unit_row, metric_col))
                    if not metric_label:
                        continue
                    metrics.append(metric_label)
                    metric_records = 0

                    for row_idx in range(data_start, len(values) + 1):
                        period_value = value_at(row_idx, start_col)
                        raw_value = value_at(row_idx, metric_col)
                        numeric_value = parse_numeric(raw_value)
                        if period_value in (None, "") or numeric_value is None:
                            continue

                        period_text = clean_cell_text(period_value)
                        period_type = "date"
                        date_text = ""
                        week = None
                        year = None
                        metric_name = metric_label

                        if is_year_label(metric_label) and period_text.isdigit():
                            period_type = "week"
                            year = int(metric_label)
                            week = int(period_text)
                            metric_name = block_title_text or metric_label
                        elif hasattr(period_value, "strftime"):
                            date_text = period_value.strftime("%Y-%m-%d")
                        else:
                            date_text = period_text

                        records.append(
                            {
                                "commodity": commodity,
                                "sheet": sheet_name,
                                "metric_group": block_title_text,
                                "metric_name": metric_name,
                                "period_type": period_type,
                                "date": date_text,
                                "year": year,
                                "week": week,
                                "value": numeric_value,
                                "unit": unit,
                                "source": source.replace("数据来源：", ""),
                            }
                        )
                        metric_records += 1
                        if metric_records >= SUPPLEMENTAL_ROWS_PER_METRIC or len(records) >= SUPPLEMENTAL_DATA_ROW_LIMIT:
                            break
                    if len(records) >= SUPPLEMENTAL_DATA_ROW_LIMIT:
                        break
                if metrics:
                    parsed_blocks.append(
                        {
                            "sheet": sheet_name,
                            "group": block_title_text,
                            "source": source.replace("数据来源：", ""),
                            "metrics": metrics[:12],
                        }
                    )
                if len(records) >= SUPPLEMENTAL_DATA_ROW_LIMIT:
                    break
            if len(records) >= SUPPLEMENTAL_DATA_ROW_LIMIT:
                break

    df = pd.DataFrame.from_records(records)
    metadata = {
        "workbook_sheets": wb.sheetnames,
        "parsed_sheets": sheet_names,
        "parsed_blocks": parsed_blocks,
        "row_limit_hit": len(records) >= SUPPLEMENTAL_DATA_ROW_LIMIT,
    }
    return df, metadata


def build_supplemental_profile(df: pd.DataFrame, max_metrics: int = 35) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    rows = []
    for (group, metric, unit), sub in df.groupby(["metric_group", "metric_name", "unit"], dropna=False):
        daily = sub[sub["period_type"] == "date"].copy()
        weekly = sub[sub["period_type"] == "week"].copy()
        source = clean_cell_text(sub["source"].dropna().iloc[0]) if not sub["source"].dropna().empty else ""

        if not daily.empty:
            daily = daily.sort_values("date")
            latest = daily.iloc[-1]
            previous = daily.iloc[-2] if len(daily) > 1 else None
            delta = latest["value"] - previous["value"] if previous is not None else None
            pct = delta / abs(previous["value"]) if previous is not None and previous["value"] else None
            percentile = (daily["value"] <= latest["value"]).mean()
            rows.append(
                {
                    "group": group,
                    "metric": metric,
                    "latest_period": latest["date"],
                    "latest_value": latest["value"],
                    "change": delta,
                    "change_pct": pct,
                    "percentile": percentile,
                    "unit": unit,
                    "source": source,
                }
            )
        elif not weekly.empty:
            weekly = weekly.sort_values(["year", "week"])
            latest_year = int(weekly["year"].max())
            latest = weekly[weekly["year"] == latest_year].iloc[-1]
            same_week_history = weekly[weekly["week"] == latest["week"]]
            percentile = (same_week_history["value"] <= latest["value"]).mean()
            rows.append(
                {
                    "group": group,
                    "metric": metric,
                    "latest_period": f"{latest_year}W{int(latest['week']):02d}",
                    "latest_value": latest["value"],
                    "change": None,
                    "change_pct": None,
                    "percentile": percentile,
                    "unit": unit,
                    "source": source,
                }
            )

    profile = pd.DataFrame(rows)
    if profile.empty:
        return profile
    profile["abs_change"] = profile["change"].abs().fillna(0)
    return profile.sort_values(["abs_change", "latest_period"], ascending=[False, False]).head(max_metrics).drop(columns=["abs_change"])


def supplemental_profile_to_text(profile: pd.DataFrame, metadata: dict) -> str:
    if profile.empty:
        return ""
    lines = [
        "Supplemental Data Profile",
        f"Parsed sheets: {', '.join(metadata.get('parsed_sheets', []))}",
        f"Parsed indicator groups: {len(metadata.get('parsed_blocks', []))}",
    ]
    if metadata.get("row_limit_hit"):
        lines.append(f"Note: normalized records were capped at {SUPPLEMENTAL_DATA_ROW_LIMIT} rows.")
    for row in profile.itertuples(index=False):
        pct_text = "N/A" if pd.isna(row.change_pct) else f"{row.change_pct:.2%}"
        change_text = "N/A" if pd.isna(row.change) else f"{row.change:.2f}"
        percentile_text = "N/A" if pd.isna(row.percentile) else f"{row.percentile:.0%}"
        lines.append(
            f"- {row.group} | {row.metric}: latest={row.latest_value:.4g} {row.unit} "
            f"({row.latest_period}), change={change_text}, pct_change={pct_text}, "
            f"sample_percentile={percentile_text}, source={row.source}"
        )
    return "\n".join(lines)
