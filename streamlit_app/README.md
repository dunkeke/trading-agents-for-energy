# Streamlit 部署版本（保留多智能体讨论 + 报告导出）

该版本已保留原程序核心讨论链路，并可直接部署到 Streamlit Cloud：

- Technical Analysis
- Macro Analysis
- Geopolitical Risk
- Research Manager Plan
- Trader Proposal
- Final Portfolio Decision

同时增加可视化指标与图表：

- 1日收益、区间收益、20日年化波动率、最大回撤、20/60日均线
- 价格/均线图、成交量图、收益率与回撤图

并支持**报告导出**：

- Markdown 报告下载
- JSON 报告下载

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
