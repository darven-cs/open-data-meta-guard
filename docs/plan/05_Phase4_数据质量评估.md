# Phase 4：数据质量评估

**目标**：选已上传的 data_download → 后端用 data_quality_assess agent 跑 pandera + ydata-profiling → 生成 Markdown 质量报告。

> 上一阶段：[04_Phase3_数据采集.md](./04_Phase3_数据采集.md)
> 下一阶段：[06_Phase5_Chat骨架.md](./06_Phase5_Chat骨架.md)

---

## Phase 4 后端任务

### 4.1 数据库迁移

- `app/alembic/versions/0004_v2_init_data_quality_evaluations.py`：
  - 建 `data_quality_evaluations` 表
  - 字段：id BIGSERIAL / dataset_id VARCHAR(64) / data_download_id BIGINT / evaluation_content TEXT / summary JSONB / issues JSONB / created_at
  - 索引：B-tree(dataset_id) + B-tree(data_download_id)

### 4.2 ORM + DAO + Schemas

- `app/model/data_quality_evaluation.py`：DataQualityEvaluation 类
- `app/dao/data_quality_evaluation.py`：CRUD
- `app/schemas/data_quality.py`：QualityRequest/QualityResponse/Detail/List

### 4.3 Service

- `app/service/data_quality.py`：
  - `async def evaluate_data(data_download_id) -> dict`：读文件路径 → 调 agent → 解析返回的 summary/issues/Markdown → 落库
  - `async def list_evaluations(dataset_id, page, size) -> dict`

### 4.4 Agent + Tools（搬自 v1.0，改名）

- `app/agents/data_quality_assess/builder.py`（原 `quality_assess/builder.py` 27 行）
- `app/agents/data_quality_assess/prompt.py`（原 `quality_assess/prompt.py` 67 行）
- `app/agents/tools/quality_tool.py` (605 行)：
  - `mqa_score_rules(metadata)` - 5 维评分
  - `assess_quality(file_path, dataset_id, sample_size)` - pandera + ydata-profiling
  - `extract_issues(report_json_path)` - 抽 issue 列表

### 4.5 API

- `app/api/routes/data_quality.py`：

  ```python
  @router.post("/data-quality")                  # {data_download_id}
  @router.get("/data-quality/{id}")              # 详情
  @router.get("/data-quality")                   # ?dataset_id=xxx
  ```

---

## Phase 4 前端任务

### 4.6 API 封装

- `web/src/api/data-quality.ts`：`evaluate(dataDownloadId)` / `getQuality(id)` / `listQualities(datasetId)`

### 4.7 View

- `web/src/views/DataQualityView.vue`：
  - 操作区：搜索 + 刷新 + 「触发评估」
  - 列表：ID / dataset / 文件 / 行数 / 缺失率 / 时间
  - 触发评估 Drawer：下拉选 data_download（数据来自 `/data-collect?dataset_id=xxx`）
  - 详情 Drawer：顶部 summary 卡片（行数/列数/缺失率/重复率）+ issues 列表 + MarkdownView 渲染

### 4.8 组件

- `web/src/components/data-quality/`：
  - `QualityForm.vue` - 触发评估 Drawer
  - `QualitySummary.vue` - summary 卡片

---

## Phase 4 验收标准

- [ ] 迁移成功
- [ ] 选 1 个 data_download 触发评估
- [ ] 评估结果包含 ydata-profiling 报告 + issues 列表
- [ ] 前端流程跑通

---

✅ **本 Phase 验收清单全勾完成后，进入 Phase 5。**
