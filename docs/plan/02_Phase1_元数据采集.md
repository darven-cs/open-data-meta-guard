# Phase 1：元数据采集

**目标**：实现「输入 URL 列表 → 后端用 web_scrap agent 抓元数据 → 列表展示 + 查看详情 + 修改 + 删除」全链路。

> 上一阶段：[01_Phase0_基础设施.md](./01_Phase0_基础设施.md)
> 下一阶段：[03_Phase2_元数据评估.md](./03_Phase2_元数据评估.md)

---

## Phase 1 后端任务

### 1.1 数据库迁移

- `app/alembic/versions/0001_v2_init_datasets.py`：

  ```python
  def upgrade():
      op.create_table(
          "datasets",
          sa.Column("id", sa.String(64), primary_key=True),  # sha256(url)
          sa.Column("url", sa.Text(), nullable=False, unique=True),
          sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=text("'{}'::jsonb")),
          sa.Column("status", sa.String(16), nullable=False, server_default=text("'pending'")),
          sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
          sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
      )
      op.create_index("idx_datasets_metadata", "datasets", ["metadata"], postgresql_using="gin")
      op.create_index("idx_datasets_status", "datasets", ["status"])
  ```

### 1.2 ORM 模型

- `app/model/dataset.py`：Dataset 类（5 字段 + 2 索引，继承 `app.core.db.Base`）

### 1.3 DAO（5 函数）

- `app/dao/dataset.py`：
  - `async def upsert_dataset(session, dataset_id, url, metadata, status) -> dict`
  - `async def get_dataset(session, dataset_id) -> dict`
  - `async def list_datasets(session, page, size, status) -> dict`
  - `async def update_dataset_metadata(session, dataset_id, metadata) -> dict`
  - `async def delete_dataset(session, dataset_id) -> dict`

### 1.4 Schemas

- `app/schemas/meta_collect.py`：
  - `IngestRequest(BaseModel): urls: list[str]`
  - `IngestItem(BaseModel): url, dataset_id, status, error_message?`
  - `IngestResponse(BaseModel): ok, items: list[IngestItem], success_count, failed_count`
  - `DatasetListResponse`, `DatasetDetailResponse`, `UpdateRequest`

### 1.5 Service（同步实现）

- `app/service/meta_collect.py`：

  ```python
  async def ingest_urls(urls: list[str]) -> dict:
      """同步遍历 URL 列表，逐个调 web_scrap agent + upsert"""
      items = []
      for url in urls:
          dataset_id = hashlib.sha256(url.encode()).hexdigest()
          try:
              agent = build_web_scrap_agent()
              result = await agent.ainvoke({"messages": [HumanMessage(content=url)]})
              # result 是 ScrapResult
              if result.scrape_status == "success":
                  metadata = result.metadata
                  status = "scraped"
              else:
                  metadata = {"reason": result.reason}
                  status = "failed"
              await dataset_dao.upsert_dataset(dataset_id, url, metadata, status)
              items.append({"url": url, "dataset_id": dataset_id, "status": status})
          except Exception as e:
              items.append({"url": url, "dataset_id": dataset_id, "status": "failed", "error_message": str(e)})
      return {"ok": True, "items": items, "success_count": sum(1 for i in items if i["status"] != "failed"), "failed_count": sum(1 for i in items if i["status"] == "failed")}
  ```

### 1.6 Agent + Tools（搬自 v1.0）

- `app/agents/web_scrap/builder.py` (18 行)
- `app/agents/web_scrap/prompt.py` (87 行)
- `app/agents/web_scrap/schema.py` (54 行) - ScrapResult
- `app/agents/tools/browser_tool.py` (294 行) - 5 个工具

### 1.7 API 路由

- `app/api/routes/meta_collect.py`：

  ```python
  router = APIRouter(prefix="/meta-collect")

  @router.post("/datasets/ingest")        # 同步批量
  @router.get("/datasets")                 # 列表
  @router.get("/datasets/{dataset_id}")    # 详情
  @router.put("/datasets/{dataset_id}")    # 修改
  @router.delete("/datasets/{dataset_id}") # 删除
  ```

- `app/api/app.py`：`app.include_router(meta_collect.router)`

---

## Phase 1 前端任务

### 1.8 API 封装

- `web/src/api/meta-collect.ts`：
  - `ingest(urls)` / `listDatasets(page, size, status)` / `getDataset(id)` / `updateDataset(id, metadata)` / `deleteDataset(id)`

### 1.9 View

- `web/src/views/MetaCollectView.vue`（覆盖原占位）：
  - 顶部操作区：搜索框 + 状态过滤 + 刷新按钮 + 「新增采集」按钮
  - 中部：表格（ID / URL / 状态 / 采集时间 / 操作：查看/修改/删除）
  - 「新增采集」Drawer：URL textarea（一行一个）+ 「提交」按钮（同步显示结果）
  - 「查看详情」Drawer：metadata JSON 折叠树
  - 「修改」Drawer：metadata JSON 编辑器

### 1.10 组件

- `web/src/components/meta-collect/`：
  - `DatasetList.vue` - 表格 + 分页 + 行操作
  - `DatasetDialog.vue` - 详情/编辑 Drawer
  - `UrlInput.vue` - URL textarea 组件

---

## Phase 1 验收标准

- [ ] `alembic upgrade head` 成功，psql 看到 datasets 表
- [ ] `POST /meta-collect/datasets/ingest` 提交 1~2 个 URL，返回 items 数组
- [ ] `GET /meta-collect/datasets` 能列出已采集项
- [ ] `PUT /meta-collect/datasets/{id}` 修改 metadata 成功
- [ ] `DELETE /meta-collect/datasets/{id}` 删除成功
- [ ] 前端 MetaCollectView 完整流程跑通（输入 URL → 抓取 → 列表 → 详情 → 修改 → 删除）

---

✅ **本 Phase 验收清单全勾完成后，进入 Phase 2。**
