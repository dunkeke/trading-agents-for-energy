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

同时支持可视化指标与图表：

- 1日收益、区间收益、20日年化波动率、最大回撤、20/60日均线
- 价格/均线图、成交量图、收益率与回撤图

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
