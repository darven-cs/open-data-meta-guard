"""数据质量评估 — 格式化常量（列名映射、指标说明等）。"""

# ──────────────────────── 列名中文映射 ────────────────────────

COLUMN_NAME_MAP: dict[str, str] = {
    "n": "行数",
    "p": "列数",
    "n_duplicates": "重复行数",
    "p_duplicates": "重复率(%)",
    "p_missing": "缺失率(%)",
    "n_missing": "缺失值总数",
    "memory_size": "内存占用",
    "n_variables_with_missing": "有缺失值的列数",
}

# ──────────────────────── 报告 section 标题 ────────────────────────

REPORT_SECTIONS = {
    "overview": "## 数据集概览",
    "variables": "## 变量统计",
    "missing": "## 缺失值分析",
    "duplicates": "## 重复值分析",
    "correlations": "## 相关性",
    "issues": "## 数据质量问题",
}

# ──────────────────────── pandera 默认校验规则 ────────────────────────

DEFAULT_PANDERA_CHECKS: list[dict] = [
    {"check": "columns_exist", "description": "列名不能为空字符串"},
    {"check": "no_duplicate_columns", "description": "不能有重名列"},
    {"check": "min_rows(1)", "description": "至少包含 1 行数据"},
]
