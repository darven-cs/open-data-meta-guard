"""meta_evaluate 3 个 observation tool（HTTP HEAD / DCAT-AP 合规 / 受控词表匹配）。

给 meta_evaluate agent 用，让 LLM 拿「真实世界」判定结果，而不是凭字符串印象给分：

| Tool | 用途 | EU 规则 | 实现要点 |
|---|---|---|---|
| http_head_check | HTTP HEAD 探测 | A1 / A3 | httpx.AsyncClient.head + 5s timeout |
| dcat_ap_compliance_check | DCAT-AP 必填字段检查 | I6 | 9 字段必填清单 + 中英别名 + presence 检查 |
| vocabulary_match | 受控词表匹配 | I3 / I4 / I5 / R2 / R4 | 5 种 vocab_type 常量集合 |

失败时一律返回 JSON 字符串（tool contract），让 agent 能拿到结构化判定。
"""
import json
import re
from urllib.parse import urlparse

import httpx
from langchain.tools import tool

from app.core.log import logger


_HEAD_TIMEOUT = 5.0


# ---------- DCAT-AP 必填字段清单（I6）----------

# DCAT-AP 3.0.0 必填字段 + 中英别名（web_scrap 抓回的是中文键）
# 每条 = 标准 DCAT 名 : 别名集（命中任一就算 present）
_DCAT_AP_REQUIRED = {
    "dct:title": ["title", "标题", "数据集名称", "数据名称", "名称", "dataset title"],
    "dct:description": ["description", "描述", "简介", "说明", "dataset description"],
    "dcat:accessURL": ["accessURL", "access_url", "访问地址", "链接", "url", "主页"],
    "dcat:downloadURL": ["downloadURL", "download_url", "下载链接", "下载地址", "下载"],
    "dct:format": ["format", "格式", "文件格式"],
    "dcat:mediaType": ["mediaType", "media_type", "媒体类型", "MIME"],
    "dct:license": ["license", "许可证", "授权", "许可"],
    "dct:publisher": ["publisher", "发布方", "发布机构", "发布单位", "来源"],
    "dcat:contactPoint": ["contactPoint", "contact_point", "联系方式", "联系人", "联系"],
}


def _field_present(meta: dict, aliases: list[str]) -> str | None:
    """检查 metadata 中是否有任一别名（大小写不敏感、空值过滤）。"""
    meta_lower = {k.lower(): k for k in meta.keys() if k}
    for alias in aliases:
        a_lower = alias.lower()
        if a_lower in meta_lower:
            real_key = meta_lower[a_lower]
            v = meta.get(real_key)
            if v and (
                not isinstance(v, (list, str))
                or (isinstance(v, str) and v.strip())
                or (isinstance(v, list) and len(v) > 0)
            ):
                return real_key
    return None


# ---------- 受控词表 ----------

# 机器可读格式（I5）
_MACHINE_READABLE_FORMATS = {
    "JSON", "CSV", "RDF", "XML", "TSV", "JSONL", "NDJSON",
    "XLSX", "GEOJSON", "PARQUET", "NETCDF", "KML",
}

# 非私有 / 开放格式（I4）
_NON_PROPRIETARY_FORMATS = {
    "CSV", "JSON", "XML", "RDF", "TSV", "JSONL", "NDJSON",
    "GEOJSON", "PARQUET", "NETCDF", "KML", "ATOM", "RSS",
}

# 标准 MIME（I3）
_VALID_MIMETYPES = {
    "text/csv", "application/json", "application/xml", "text/xml",
    "application/rdf+xml", "application/ld+json",
    "text/tab-separated-values", "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "application/geo+json", "application/x-ndjson",
}

# 开放许可证（license_vocabulary 用）
_OPEN_LICENSES = {
    "cc-by", "cc-by-4.0", "cc-by-3.0", "cc-by-sa", "cc-by-sa-4.0",
    "cc0", "cc0-1.0", "odc", "odc-by", "odc-pddl", "odbl", "pddl",
    "public-domain", "mit", "apache-2.0",
}

# 受控访问权限词表（access_restrictions_vocabulary 用）
_ACCESS_RIGHTS_VOCAB = {
    "public", "restricted", "confidential", "non-public",
    "公开", "受限", "机密", "内部",
}


def _norm_license(s: str) -> str:
    """license 字符串标准化（保留字母数字 + . + -，转小写）。

    注意：必须保留 `.`，否则 "CC-BY-4.0" 会变成 "cc-by-40" 无法匹配 vocab。
    """
    return re.sub(r"[^a-z0-9\-\.]", "", s.lower()) if s else ""


def _norm_format(s: str) -> str:
    return s.upper().strip() if s else ""


def _norm_mt(s: str) -> str:
    return s.lower().strip() if s else ""


# ---------- HTTP HEAD（A1 / A3 用）----------

@tool
async def http_head_check(url: str) -> str:
    """HTTP HEAD 探测 URL 是否可达，返回 status_code + accessible + error。

    用于 EU MQA 405 分制的两条硬规则：
    - **A1 accessURL accessibility**（50 分）：HTTP HEAD 200/302/3xx 算可达
    - **A3 downloadURL accessibility**（30 分）：同上

    agent 必须根据 status_code 给分（A1: 2xx/3xx 给 50，否则 0）。

    Args:
        url: 待探测 URL（accessURL 或 downloadURL）

    Returns:
        JSON: {ok, url, status_code, accessible, redirect_url, error}
    """
    if not url or not urlparse(url).scheme.startswith("http"):
        return json.dumps({
            "ok": False,
            "url": url,
            "accessible": False,
            "error": f"non-http URL or empty: {url!r}",
        }, ensure_ascii=False)

    try:
        async with httpx.AsyncClient(timeout=_HEAD_TIMEOUT, follow_redirects=True) as c:
            r = await c.head(url)
        return json.dumps({
            "ok": True,
            "url": url,
            "status_code": r.status_code,
            "accessible": r.status_code < 400,
            "redirect_url": str(r.url) if r.url else url,
            "error": None,
        }, ensure_ascii=False)
    except httpx.TimeoutException:
        logger.debug("[mqa-tool] HEAD timeout: {}", url)
        return json.dumps({
            "ok": True,
            "url": url,
            "status_code": None,
            "accessible": False,
            "redirect_url": url,
            "error": "timeout",
        }, ensure_ascii=False)
    except Exception as e:
        logger.debug("[mqa-tool] HEAD failed: {} -> {}", url, e)
        return json.dumps({
            "ok": True,
            "url": url,
            "status_code": None,
            "accessible": False,
            "redirect_url": url,
            "error": f"{type(e).__name__}: {e}",
        }, ensure_ascii=False)


# 工具列表（必须在所有 @tool 函数定义之后）
meta_evaluate_tools = [http_head_check]