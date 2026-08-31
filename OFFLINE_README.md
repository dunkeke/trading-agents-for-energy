# 能源商品多 Agent 投研助手：离线参赛版

该版本面向轻应用赛道的单机离线演示场景，保留线上版的多 Agent 报告结构，但不调用外部行情 API 或大模型 API。

## 运行方式

Windows:

```bat
run_offline_app.bat
```

或手动运行：

```bash
cd streamlit_app
pip install -r requirements-offline.txt
python -m streamlit run offline_app.py --server.address 127.0.0.1 --server.port 8501
```

## 离线边界

- 不导入 `openai`。
- 不导入 `yfinance`。
- 不抓取互联网行情。
- 本地页面只监听 `127.0.0.1`。
- 输入数据来自本地 CSV/XLSX、能源周报 Excel 和人工事件备注。
- 报告生成来自 `offline_analysis.py` 中的内置规则化分析模型。

## 输入文件

### 本地行情文件

支持 `.csv` 和 `.xlsx`，会自动识别以下列名：

- 日期：`date`、`trade_date`、`日期`、`交易日期`
- 开盘：`open`、`开盘`、`开盘价`
- 最高：`high`、`最高`、`最高价`
- 最低：`low`、`最低`、`最低价`
- 收盘/结算：`close`、`settle`、`收盘`、`收盘价`、`结算`
- 成交量：`volume`、`vol`、`成交量`

至少需要包含收盘/结算价。

### 补充周度数据

支持研报式复杂 Excel 模板。程序会自动识别：

- 指标区块；
- 指标名称；
- 单位；
- 数据来源；
- 日频时间序列；
- 按周序号排列的季节性表。

## 报告模型

离线版按照线上版报告规则提炼为七个模块：

- Supplemental Data Analysis
- Technical Analysis
- Macro Analysis
- Geopolitical Risk
- Research Manager Plan
- Trader Proposal
- Final Portfolio Decision

其中：

- 技术 Agent 使用本地行情计算收益率、均线、波动率和回撤；
- 补充数据 Agent 使用库存、进口利润、基差/月差、产业利润、开工率等规则判断基本面方向；
- 宏观和地缘 Agent 只使用人工输入备注；
- Research Manager 负责综合场景树、主导变量和风控约束；
- Trader Proposal 给出交易动作、仓位、止损和监控触发器；
- Final Portfolio Decision 输出方向、敞口、置信度、核心风险和复核节奏。

## 参赛材料建议

- 本仓库源码或离线压缩包；
- Demo 视频：展示断网后运行 `run_offline_app.bat`、上传本地数据、生成报告、导出 PDF/Markdown/JSON；
- 截图：本地上传、指标画像、多 Agent 报告、离线历史归档；
- 脱敏后的 LPG 周度数据模板；
- 原创性承诺书；
- 开发过程说明：需求背景、架构设计、核心代码、测试过程、离线合规边界。

## 原创性说明要点

本项目的原创部分主要包括：

- 针对能源商品自有数据的复杂 Excel 解析和标准化；
- 面向 LPG 等公开数据不足品种的补充数据 Agent；
- 按投研流程拆分的多 Agent 报告规则；
- 从数据画像到策略、仓位、止损、风控建议的离线闭环。

Streamlit、pandas、openpyxl、FPDF 等为开源基础工具，不属于外部成品软件应用。
