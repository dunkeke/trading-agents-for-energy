# 部署评估：是否可以直接部署在前端

结论：**不可以直接只部署前端**。当前项目是一个「前后端一体」应用，前端只是 UI 层，核心交易分析逻辑在服务端运行。

## 关键依据

1. 前端通过 tRPC 调用 `/api/trpc`，说明依赖服务端 API。
2. 服务端 `analysis.run` mutation 会：
   - 读取数据库中的 API 配置；
   - 调用 `runAnalysis` 执行多阶段 LLM 与行情计算；
   - 写回数据库分析结果。
3. `runAnalysis` 使用 `openai`、`yahoo-finance2`，需要服务端网络访问和密钥管理，不适合暴露在浏览器。
4. 生产启动流程使用 Node 进程启动 Hono 服务器（`node dist/boot.js`），不是纯静态站点。
5. 服务端读取 `DATABASE_URL`、`APP_SECRET` 等环境变量，说明必须有后端运行环境。

## 如果你想“前端可直接部署”需要改造

可选方案：

- 方案 A（推荐）：保留当前架构
  - 前端部署在静态托管/CDN；
  - 后端（Hono+tRPC）单独部署在 Node 容器/函数平台；
  - 数据库与 API Key 保持在后端。

- 方案 B：改为 BFF/Serverless API
  - 把 `analysis.run` 迁到 Serverless Function（Vercel/Cloudflare Workers/AWS Lambda）；
  - 前端只调用该 API。

- 方案 C：纯前端（不推荐）
  - 需把 API Key 暴露给浏览器，存在严重安全风险；
  - DB 写入逻辑也无法安全落地。

## 最小可行部署建议

- 前端：Vite build 后静态部署。
- 后端：部署 `dist/boot.js`（或直接 Node 运行 API 目录）。
- 数据库：准备 MySQL，配置 `DATABASE_URL`。
- 环境变量：至少配置 `APP_ID`、`APP_SECRET`、`DATABASE_URL`。
