# Phase 3：数据采集（人工上传）

**目标**：选 dataset → 选本地 csv/xlsx/json → 上传 + 落盘 + 算 sha256 + 落库 + 关联 dataset。

> 上一阶段：[03_Phase2_元数据评估.md](./03_Phase2_元数据评估.md)
> 下一阶段：[05_Phase4_数据质量评估.md](./05_Phase4_数据质量评估.md)

---

## Phase 3 后端任务

### 3.1 数据库迁移

- `app/alembic/versions/0003_v2_init_data_downloads.py`：
  - 建 `data_downloads` 表
  - 字段：id BIGSERIAL / dataset_id VARCHAR(64) / file_name / file_path / file_format VARCHAR(16) / file_size BIGINT / file_sha256 VARCHAR(64) / source VARCHAR(16) DEFAULT 'user_upload' / status VARCHAR(16) DEFAULT 'uploaded' / error_message TEXT / created_at
  - 索引：B-tree(dataset_id) + B-tree(status)

### 3.2 ORM + DAO + Schemas

- `app/model/data_download.py`：DataDownload 类
- `app/dao/data_download.py`：CRUD（4 函数 + 1 个 `delete_with_file`）
- `app/schemas/data_collect.py`：UploadResponse/ListResponse/DetailResponse

### 3.3 Service

- `app/service/data_collect.py`：
  - `async def upload_file(dataset_id, file: UploadFile) -> dict`：
    1. 校验文件类型（csv/xlsx/json，从扩展名判断）
    2. 校验 dataset_id 存在
    3. 生成唯一文件名（dataset_id + 时间戳）
    4. 保存到 `data/uploads/{dataset_id}/{filename}.{ext}`
    5. 计算 sha256 + file_size
    6. 落库
    7. 顺便把 dataset.status 推进到 "uploaded"
  - `async def list_datasets_for_select() -> list`：返回已采集元数据的 datasets（status != pending）
  - `async def list_downloads(dataset_id, page, size) -> dict`
  - `async def delete_download(id) -> dict`：同时删磁盘文件

### 3.4 API

- `app/api/routes/data_collect.py`：

  ```python
  @router.get("/data-collect/datasets")                    # 下拉源
  @router.post("/data-collect/upload")                     # multipart
  @router.get("/data-collect/{id}")                        # 详情
  @router.get("/data-collect")                             # ?dataset_id=xxx
  @router.delete("/data-collect/{id}")                     # 删除（含文件）
  ```

---

## Phase 3 前端任务

### 3.5 API 封装

- `web/src/api/data-collect.ts`：
  - `upload(datasetId, file)` - FormData multipart
  - `listDatasetsForSelect()` - dropdown 源
  - `listDownloads(datasetId)` / `getDownload(id)` / `deleteDownload(id)`

### 3.6 View

- `web/src/views/DataCollectView.vue`：
  - 操作区：搜索 + dataset 过滤 + 格式过滤 + 刷新 + 「上传」
  - 列表：ID / dataset / 文件名 / 格式 / 大小 / 时间 / 操作（下载 / 删除）
  - 上传 Drawer：下拉选 dataset + 拖拽/选择文件（accept=".csv,.xlsx,.json"）+ 进度条

### 3.7 组件

- `web/src/components/data-collect/`：
  - `FileUploadInput.vue` - 拖拽 + 点击上传
  - `UploadProgress.vue` - 进度条
  - `UploadList.vue` - 列表

---

## Phase 3 验收标准

- [ ] 迁移成功
- [ ] `POST /data-collect/upload` 接 csv 文件 → 落盘 + 算 sha256 + 落库
- [ ] `DELETE /data-collect/{id}` 同时删除磁盘文件
- [ ] `GET /data-collect/datasets` 返回 status != pending 的 datasets
- [ ] 前端流程跑通（选 dataset → 选文件 → 上传 → 列表 → 下载 → 删除）

---

✅ **本 Phase 验收清单全勾完成后，进入 Phase 4。**
