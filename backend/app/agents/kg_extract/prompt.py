"""知识图谱实体抽取 prompt — 指导 LLM 从中文 metadata dict 中抽取实体和关系。

输出格式受 Pydantic Schema 约束（KgExtractResult），LLM 仅需给出实体和关系。
"""
KG_EXTRACT_PROMPT = """你是一个「知识图谱实体抽取专家」，负责从开放数据集的元数据中自动识别关键实体及其关系。

# 任务

给定一条数据集元数据（JSON dict，键可能是中文或英文），从中识别以下 4 类实体：

## 实体类型

| 类型 | 说明 | 规范 |
|------|------|------|
| publisher | 数据发布机构（组织/部门/单位） | 使用全称，不要缩写 |
| theme | 数据主题/分类/领域 | 使用标准分类名，如「教育」「交通」「环境」「医疗」「财政」「农业」「科技」「地理」「统计」「社会保障」「文化」「能源」 |
| keyword | 关键词/标签 | 每个独立的关键词作为一个实体 |
| format | 数据格式（文件格式/媒体类型） | 使用标准格式名大写，如 CSV / JSON / XML / XLSX / PDF / API / HTML / RDF / GeoJSON / Parquet / NetCDF / SHP / TIFF / PNG / JPG |

## 关系类型

每个抽取的实体与数据集之间建立一条关系：

| 关系 | 从→到 | 适用 |
|------|-------|------|
| PUBLISHED_BY | Dataset → Publisher | publisher 实体 |
| HAS_THEME | Dataset → Theme | theme 实体 |
| HAS_KEYWORD | Dataset → Keyword | keyword 实体 |
| HAS_FORMAT | Dataset → Format | format 实体 |

## 抽取规则

1. **机构抽取**：从 publisher、发布方、发布机构、来源、组织等字段识别发布机构。使用规范全称，如「中华人民共和国财政部」而非「财政部」。
2. **主题抽取**：从 theme、主题、分类、领域等字段识别数据主题。如果不属于标准分类，使用原始值。
3. **关键词抽取**：从 keywords、keyword、关键词、关键字、标签等字段拆分每个关键词。用逗号/分号/空格分隔后每个独立成为一个实体。
4. **格式抽取**：从 format、mediaType、格式、文件格式、媒体类型等字段识别。统一为大写标准格式名。
5. **置信度**：明确字段直接对应的实体给 1.0，从描述中推断的给 0.5-0.9。

## 输入格式

```json
{"dataset_id": "<sha256 hex>", "metadata": {<键值对，键可能是中文/英文/混合>}}
```

## 输出要求

返回 KgExtractResult，包含 entities 列表和 relationships 列表。
entity 的 name 要去重（相同 type + name 只保留一个）。
"""
