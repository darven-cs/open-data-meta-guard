# Phase 0：基础设施

**目标**：搭建前后端骨架，让前后端都能启动并看到 5 个菜单入口（View 是占位）。

> 上一阶段：[00_总体路线图.md](./00_总体路线图.md)
> 下一阶段：[02_Phase1_元数据采集.md](./02_Phase1_元数据采集.md)

---

## Phase 0 后端任务

### 0.1 创建目录结构

```
v2.0/backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/__init__.py
│   ├── api/routes/__init__.py
│   ├── core/__init__.py
│   ├── model/__init__.py
│   ├── dao/__init__.py
│   ├── service/__init__.py
│   ├── agents/__init__.py
│   ├── agents/tools/__init__.py
│   ├── agents/web_scrap/__init__.py
│   ├── agents/meta_evaluate/__init__.py
│   ├── agents/data_quality_assess/__init__.py
│   ├── agents/chat/__init__.py
│   ├── nodes/__init__.py
│   └── schemas/__init__.py
├── alembic/
│   ├── env.py
│   └── versions/__init__.py
├── data/uploads/
├── logs/
└── tests/
```

### 0.2 配置文件（4 文件）

- `v2.0/backend/pyproject.toml`：参考 v1.0，**删除 neo4j 依赖**
- `v2.0/backend/.env.example`：复制 v1.0（无 neo4j_* 变量）
- `v2.0/backend/alembic.ini`：参考 v1.0
- `v2.0/backend/alembic/env.py`：参考 v1.0 模板

### 0.3 Docker（1 文件 + 启动命令）

- `v2.0/backend/docker-compose.yml`：**只保留 postgres 服务**，去掉 neo4j 服务和卷
- 执行：`docker-compose down -v && docker-compose up -d`
- 验证：`docker ps` 看到 postgres healthy

### 0.4 Core 层（7 文件从 v1.0 搬）

| v2.0 文件 | 来源 v1.0 | 改造点 |
|-----------|----------|--------|
| `app/core/config.py` | `v1.0/app/core/config.py` (91 行) | 删 neo4j_host/uri/user/password 配置项 |
| `app/core/db.py` | `v1.0/app/core/db.py` (125 行) | 原样搬 |
| `app/core/llm.py` | `v1.0/app/core/llm.py` (137 行) | 原样搬（DeepSeek 双工厂函数） |
| `app/core/browser.py` | `v1.0/app/core/browser.py` (490 行) | 原样搬 |
| `app/core/log.py` | `v1.0/app/core/log.py` (129 行) | 原样搬 |
| `app/core/lifespan.py` | `v1.0/app/core/lifespan.py` (81 行) | **删** neo4j_client.connect/init_schema/close 调用 |
| `app/core/file_storage.py` | `v1.0/app/core/file_storage.py` (81 行) | 原样搬 |

### 0.5 API 基础（3 文件）

- `app/main.py`：uvicorn 入口
- `app/api/app.py`：create_app() + lifespan，**先只注册 health router**
- `app/api/resp.py`：ResponseModel 统一响应（搬自 v1.0）
- `app/api/routes/health.py`：搬自 v1.0 **去掉 neo4j 检查**

---

## Phase 0 前端任务

### 0.6 项目基础（6 文件）

- `web/package.json`：复用 v1.0 完整依赖
- `web/vite.config.ts`：端口 8001 代理
- `web/tsconfig.{json,app.json,node.json}`
- `web/index.html` + `web/public/favicon.svg`
- `web/src/main.ts`：createApp + pinia + router + font 导入

### 0.7 全局 + Router（3 文件）

- `web/src/App.vue`：根组件（meta.layout 条件包裹 AdminLayout）
- `web/src/router/index.ts`：5 路由（meta-collect/meta-evaluate/data-collect/data-quality/chat）
- `web/src/data/features.ts`：**5 个功能卡**（去掉 meta-report/quality-report/data-story，新增 meta-evaluate/data-quality）

### 0.8 样式系统（1 文件）

- `web/src/styles/base.css`：**完全复用** v1.0（478 行设计 token + Markdown 渲染）

### 0.9 AdminLayout 体系（3 文件搬自 v1.0）

- `web/src/components/admin/AdminLayout.vue` (137 行)
- `web/src/components/admin/AdminSidebar.vue` (317 行)
- `web/src/components/admin/AdminTopbar.vue` (155 行)

### 0.10 Home 组件（2 文件 + 1 View）

- `web/src/components/home/FeatureCard.vue` (198 行)
- `web/src/components/home/FeatureGrid.vue` (42 行)
- `web/src/views/HomeView.vue`：**简化版**（欢迎语 + 5 个 FeatureCard 网格）

### 0.11 Chat 通用组件（提前搬过来，Phase 5 直接用）

- `web/src/types/chat.ts` (26 行)
- `web/src/stores/chat.ts` (131 行) - Pinia 会话管理
- `web/src/composables/useChat.ts` (60 行)
- `web/src/composables/useChatScroll.ts` (150 行)
- `web/src/api/chat.ts` (51 行)
- `web/src/utils/markdown.ts` (185 行)
- `web/src/components/chat/` 6 文件（ChatLayout/ConversationSidebar/MessageList/MessageItem/ChatInput/MarkdownView）

### 0.12 其他 4 个 View 占位（4 文件）

- `web/src/views/MetaCollectView.vue` - 占位（"建设中"）
- `web/src/views/MetaEvaluateView.vue` - 占位
- `web/src/views/DataCollectView.vue` - 占位
- `web/src/views/DataQualityView.vue` - 占位
- `web/src/views/ChatView.vue` - 占位（仅 `<ChatLayout />` 引用）

---

## Phase 0 验收标准

- [ ] `docker-compose up -d` 后 `docker ps` 显示 postgres healthy
- [ ] `uvicorn app.main:app --reload --port 8001` 启动成功
- [ ] `curl http://localhost:8001/health` 返回 `{"status": "ok", "components": {"api": {...}, "postgres": {...}}}`
- [ ] `cd v2.0/web && npm install && npm run dev` 启动
- [ ] 浏览器访问 `http://localhost:5173` 看到 HomeView（欢迎语 + 5 个功能卡）
- [ ] 侧栏 5 个菜单（总览/元数据采集/元数据评估/数据采集/数据质量评估/数据小D）都可点，点击其他 View 显示「建设中」

---

✅ **本 Phase 验收清单全勾完成后，进入 Phase 1。**
