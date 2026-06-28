# Phase 2：元数据评估

**目标**：选已采集的 dataset → 后端用 meta_evaluate agent 按 EU MQA 规则评分 → 生成 Markdown 评估报告。

> 上一阶段：[02_Phase1_元数据采集.md](./02_Phase1_元数据采集.md)
> 下一阶段：[04_Phase3_数据采集.md](./04_Phase3_数据采集.md)

---

## Phase 2 后端任务

### 2.1 数据库迁移

- `app/alembic/versions/0002_v2_init_meta_evaluations.py`：
  - 建 `meta_evaluations` 表
  - 字段：id BIGSERIAL / dataset_id VARCHAR(64) / evaluation_content TEXT / rule_scores JSONB / score_total INTEGER / grade VARCHAR(16) / created_at
  - 索引：B-tree(dataset_id) + B-tree(grade)

### 2.2 ORM + DAO + Schemas

- `app/model/meta_evaluation.py`：MetaEvaluation 类
- `app/dao/meta_evaluation.py`：CRUD（4 函数）
- `app/schemas/meta_evaluate.py`：EvaluateRequest/EvaluateResponse/EvaluationDetail/EvaluationList

### 2.3 Service

- `app/service/meta_evaluate.py`：
  - `async def evaluate_dataset(dataset_id) -> dict`：从 datasets 取 metadata → 调 agent → 构造 Markdown 报告 → 落库 → 返回 evaluation_id
  - `async def list_evaluations(dataset_id, page, size) -> dict`

### 2.4 Agent + Tools（搬自 v1.0）

- `app/agents/meta_evaluate/builder.py` (37 行)
- `app/agents/meta_evaluate/prompt.py` (218 行) - 23 条 EU MQA 规则
- `app/agents/meta_evaluate/schema.py` (108 行) - MetaEvaluateResult
- `app/agents/tools/meta_evaluate_tool.py` (351 行)：
  - `http_head_check(url)` → A1/A3
  - `dcat_ap_compliance_check(metadata_json)` → I6
  - `vocabulary_match(value, vocab_type)` → I3/I4/I5/R2/R4

### 2.5 API

- `app/api/routes/meta_evaluate.py`：

  ```python
  @router.post("/meta-evaluate")                    # {dataset_id} 触发
  @router.get("/meta-evaluate/{id}")               # 单条详情
  @router.get("/meta-evaluate")                    # ?dataset_id=xxx 历史列表
  ```

---

## Phase 2 前端任务

### 2.6 API 封装

- `web/src/api/meta-evaluate.ts`：`evaluate(datasetId)` / `getEvaluation(id)` / `listEvaluations(datasetId)`

### 2.7 View

- `web/src/views/MetaEvaluateView.vue`：
  - 操作区：搜索 + 等级过滤 + 刷新 + 「触发评估」
  - 列表：ID / dataset / 等级 / 总分 / 时间 / 操作
  - 触发评估 Drawer：下拉选 dataset（数据来自 `/meta-collect/datasets`）
  - 详情 Drawer：MarkdownView 渲染 evaluation_content + 顶部摘要（grade 徽章 + score_total + rule_scores 条形图）

### 2.8 组件

- `web/src/components/meta-evaluate/`：
  - `EvaluateForm.vue` - 触发评估 Drawer
  - `EvaluateList.vue` - 列表
  - `RuleScoresChart.vue` - 23 条规则得分可视化

---

## Phase 2 验收标准

- [ ] 迁移成功，meta_evaluations 表存在
- [ ] 选 1 个 dataset 触发评估，返回 evaluation_id
- [ ] 评估详情包含 Markdown 报告 + rule_scores JSON + grade
- [ ] 历史评估列表按 dataset_id 过滤正常
- [ ] 前端完整流程跑通

---

✅ **本 Phase 验收清单全勾完成后，进入 Phase 3。**
