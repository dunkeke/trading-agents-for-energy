# Streamlit 部署版本（保留多智能体讨论 + 报告导出）

该版本保留原程序核心讨论链路：

- Technical Analysis
- Macro Analysis
- Geopolitical Risk
- Research Manager Plan
- Trader Proposal
- Final Portfolio Decision

并新增：

- **一键导出 PDF**（基于当前完整报告）
- **历史报告本地存档列表**（自动落盘 JSON/Markdown，可回看与下载）
- **原始 Excel 数据增强**：支持上传每周更新的能源数据周报类 `.xlsx` 文件，自动识别指标区块、单位、数据源、日频/周频结构，并将清洗后的摘要交给 Supplemental Data Analysis Agent。

同时支持可视化指标与图表：

- 1日收益、区间收益、20日年化波动率、最大回撤、20/60日均线
- 价格/均线图、成交量图、收益率与回撤图

## 补充数据 Agent

对 LPG、JKM 等公开历史行情不完整的品种，可以在页面的 **Supplemental Fundamental Data / 原始数据增强** 区域上传原始 Excel 模板。应用会先在本地解析复杂宽表，将研报式区块标准化为指标画像，再由 Supplemental Data Analysis Agent 总结：

- 基差、月差、内外盘价差、进口利润、库存、开工率、供需压力与季节性位置；
- 异常变化、数据缺口和质量提示；
- 对策略、仓位、止损和风控的影响。

不上传文件或取消注入时，原有 yfinance + 多智能体分析流程保持不变。

## 本地运行

```bash
cd streamlit_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 部署

1. 将仓库连接到 Streamlit Cloud。
2. Main file path 选择：`streamlit_app/app.py`。
3. 在 Secrets 中配置（推荐）：
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL`（可选，默认 `https://api.deepseek.com`）
   - `OPENAI_MODEL`（可选，默认 `deepseek-chat`）

## 注意

- 该版本不依赖原 Node/tRPC/MySQL 后端。
- 多智能体流程会触发多次 LLM 调用，建议关注 token 成本与响应时间。
- Streamlit Cloud 的本地存档位于应用容器文件系统，实例重建后历史文件可能丢失；如需长期保存，建议接入对象存储或数据库。
