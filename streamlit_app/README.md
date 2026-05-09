# Streamlit 部署版本

这是一个可直接部署到 Streamlit Cloud 的版本，把原项目核心流程改为单体 Python 应用：

- 通过 `yfinance` 拉取最近 150 天数据；
- 组装行情与宏观上下文；
- 调用兼容 OpenAI SDK 的聊天模型（默认 DeepSeek `https://api.deepseek.com`）；
- 在页面展示 Markdown 报告与价格图表。

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
- 为了保持简单，当前是单轮统一报告（不是原项目那种多 agent 分阶段入库流程）。
