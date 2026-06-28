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


# ---------- DCAT-AP 合规检查（I6）----------

@tool
async def dcat_ap_compliance_check(metadata_json: str) -> str:
    """检查 metadata 是否满足 DCAT-AP 必填字段清单（启发式，**不是真 SHACL**）。

    用于 EU MQA 405 分制 I6（DCAT-AP 合规，30 分）：
    - 9 个 DCAT-AP 必填字段（dct:title / description / accessURL / downloadURL /
      format / mediaType / license / publisher / contactPoint）
    - 中英文别名都接受（web_scrap 抓回可能是中文键）
    - missing 字段数 → 扣分逻辑由 agent 自己算（present=9 给 30；每缺 1 个扣 30/9 ≈ 3.3）

    Args:
        metadata_json: metadata JSON 字符串（支持中英文键）

    Returns:
        JSON: {ok, compliant, present, missing, mapped_keys, total_required, present_count}
    """
    try:
        meta = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
    except json.JSONDecodeError as e:
        return json.dumps({"ok": False, "error": f"metadata invalid JSON: {e}"}, ensure_ascii=False)

    if not isinstance(meta, dict):
        return json.dumps({"ok": False, "error": "metadata must be a JSON object"}, ensure_ascii=False)

    present: list[str] = []
    missing: list[str] = []
    mapped_keys: dict[str, str] = {}

    for dcat_field, aliases in _DCAT_AP_REQUIRED.items():
        hit_key = _field_present(meta, aliases)
        if hit_key is not None:
            present.append(dcat_field)
            mapped_keys[dcat_field] = hit_key
        else:
            missing.append(dcat_field)

    return json.dumps({
        "ok": True,
        "compliant": len(missing) == 0,
        "present": present,
        "missing": missing,
        "mapped_keys": mapped_keys,
        "total_required": len(_DCAT_AP_REQUIRED),
        "present_count": len(present),
    }, ensure_ascii=False)


# ---------- 受控词表匹配（I3 / I4 / I5 / R2 / R4）----------

@tool
async def vocabulary_match(value: str, vocab_type: str) -> str:
    """检查 value 是否在受控词表中，匹配 EU MQA 的 5 条 vocab 规则。

    vocab_type 取值：
    - `format_machine_readable`：机器可读格式（I5，命中给 20 分）
    - `format_non_proprietary`：非私有开放格式（I4，命中给 20 分）
    - `media_type`：标准 MIME type（I3，命中给 10 分）
    - `license`：开放许可证（license_vocabulary R2，命中给 10 分）
    - `access_rights`：受控访问权限词（access_restrictions_vocabulary，命中给 5 分）

    Args:
        value: 待匹配的字符串
        vocab_type: 见上方 5 种

    Returns:
        JSON: {ok, matched, score, vocab_type, value, normalized}
    """
    if not value:
        return json.dumps({
            "ok": False,
            "matched": False,
            "score": 0,
            "vocab_type": vocab_type,
            "value": value,
            "error": "value is empty",
        }, ensure_ascii=False)

    if vocab_type == "format_machine_readable":
        norm = _norm_format(value)
        matched = norm in _MACHINE_READABLE_FORMATS
        return json.dumps({
            "ok": True,
            "matched": matched,
            "score": 20 if matched else 0,
            "vocab_type": vocab_type,
            "value": value,
            "normalized": norm,
        }, ensure_ascii=False)

    if vocab_type == "format_non_proprietary":
        norm = _norm_format(value)
        matched = norm in _NON_PROPRIETARY_FORMATS
        return json.dumps({
            "ok": True,
            "matched": matched,
            "score": 20 if matched else 0,
            "vocab_type": vocab_type,
            "value": value,
            "normalized": norm,
        }, ensure_ascii=False)

    if vocab_type == "media_type":
        norm = _norm_mt(value)
        matched = norm in _VALID_MIMETYPES
        return json.dumps({
            "ok": True,
            "matched": matched,
            "score": 10 if matched else 0,
            "vocab_type": vocab_type,
            "value": value,
            "normalized": norm,
        }, ensure_ascii=False)

    if vocab_type == "license":
        norm = _norm_license(value)
        matched = norm in _OPEN_LICENSES
        if not matched and "creativecommons.org" in value.lower() and "by" in value.lower():
            matched = True
        return json.dumps({
            "ok": True,
            "matched": matched,
            "score": 10 if matched else 0,
            "vocab_type": vocab_type,
            "value": value,
            "normalized": norm,
        }, ensure_ascii=False)

    if vocab_type == "access_rights":
        norm = value.strip().lower()
        matched = norm in _ACCESS_RIGHTS_VOCAB
        return json.dumps({
            "ok": True,
            "matched": matched,
            "score": 5 if matched else 0,
            "vocab_type": vocab_type,
            "value": value,
            "normalized": norm,
        }, ensure_ascii=False)

    return json.dumps({
        "ok": False,
        "matched": False,
        "score": 0,
        "vocab_type": vocab_type,
        "value": value,
        "error": (
            f"unknown vocab_type: {vocab_type} (must be one of: "
            "format_machine_readable, format_non_proprietary, media_type, license, access_rights)"
        ),
    }, ensure_ascii=False)


# 工具列表（必须在所有 @tool 函数定义之后）
meta_evaluate_tools = [http_head_check, dcat_ap_compliance_check, vocabulary_match]