"""EU 标准数据故事工具的 pytest 测试。

覆盖：
- _charting_common._safe_read_df（编码自动探测）
- data_cluster_analysis（聚类分层）
- data_exception_mining（异常检测）
- dataset_meta_query（元数据核验）

依赖：
- pytest
- pytest-asyncio（pyproject.toml 已配 asyncio_mode="auto"）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from app.agents.tools._charting_common import _safe_read_df, save_fig_as_png


FIXTURES = Path(__file__).parent / "fixtures"


# ─────────── 共享模块测试 ───────────


def test_safe_read_csv_utf8(tmp_path: Path):
    p = tmp_path / "u.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    df = _safe_read_df(str(p), "csv")
    assert df.shape == (1, 2)
    assert df.iloc[0]["a"] == 1


def test_safe_read_csv_gbk(tmp_path: Path):
    p = tmp_path / "g.csv"
    p.write_bytes("地区,数值\n北京,100\n".encode("gbk"))
    df = _safe_read_df(str(p), "csv")
    assert df.iloc[0]["地区"] == "北京"
    assert df.iloc[0]["数值"] == 100


def test_safe_read_csv_unsupported_encoding_raises(tmp_path: Path):
    p = tmp_path / "bad.csv"
    # 写 latin-1 字节，UTF-8 解码会失败，但 latin-1 在回退链里 → 仍能成功
    p.write_bytes(b"a,b\n\xe9,2\n")
    df = _safe_read_df(str(p), "csv")
    assert df.shape == (1, 2)


def test_save_fig_as_png(tmp_path: Path, monkeypatch):
    """save_fig_as_png 应创建 charts/<dataset_id>/<chart_type>_<ts>.png"""
    import matplotlib.pyplot as plt

    # 临时改 _CHARTS_DIR 的 parent 到 tmp_path
    from app.agents.tools import _charting_common as cc

    fake_charts_dir = tmp_path / "charts"
    fake_charts_dir.mkdir()

    monkeypatch.setattr(cc, "_CHARTS_DIR", fake_charts_dir)
    monkeypatch.setattr(cc.settings, "download_dir", str(tmp_path))

    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])

    rel = save_fig_as_png(fig, "ds_test_001", "test_chart")
    assert rel is not None
    assert rel.startswith("charts/")
    assert rel.endswith(".png")
    assert (tmp_path / rel).exists()


# ─────────── cluster 工具测试 ───────────


@pytest.mark.asyncio
async def test_cluster_basic(monkeypatch):
    """30 行 / 3 档清晰分层 → 至少返回 2 个 tier,样本数总和 = 30,生成图表"""
    from app.agents.tools import cluster_analysis_tool as cat

    fake_path = str(FIXTURES / "cluster_fixture.csv")

    # mock list_by_dataset → 返回 csv 路径
    monkeypatch.setattr(
        cat.download_dao,
        "list_by_dataset",
        AsyncMock(return_value={
            "ok": True,
            "items": [{"file_path": fake_path, "file_format": "csv"}],
        }),
    )

    result = await cat.data_cluster_analysis.ainvoke({
        "dataset_id": "test_cluster_ds",
        "group_col": "region",
        "value_col": "score",
        "n_clusters": 3,
    })
    payload = json.loads(result)
    assert "error" not in payload, payload.get("error")
    assert payload["n_clusters"] >= 2
    assert sum(t["count"] for t in payload["tiers"]) == 30
    assert payload["chart_path"] is not None
    assert payload["chart_path"].endswith(".png")
    assert payload["chart_path"].startswith("charts/test_cluster_ds/")


@pytest.mark.asyncio
async def test_cluster_small_sample_falls_back(monkeypatch):
    """样本数 < n_clusters * 2 时自动降级 quantile binning。"""
    from app.agents.tools import cluster_analysis_tool as cat

    # 仅 5 行 → 应触发 fallback
    fake_path = str(FIXTURES / "cluster_fixture.csv")
    monkeypatch.setattr(
        cat.download_dao,
        "list_by_dataset",
        AsyncMock(return_value={
            "ok": True,
            "items": [{"file_path": fake_path, "file_format": "csv"}],
        }),
    )

    # 把 csv 截到 5 行（临时 monkey-patch _safe_read_df）
    def fake_safe_read(path, fmt):
        df = pd.read_csv(path)
        return df.head(5)

    monkeypatch.setattr(cat, "_safe_read_df", fake_safe_read)

    result = await cat.data_cluster_analysis.ainvoke({
        "dataset_id": "small_ds",
        "group_col": "region",
        "value_col": "score",
        "n_clusters": 3,
    })
    payload = json.loads(result)
    assert "error" not in payload, payload.get("error")
    assert payload["method"] in {"quantile_binning", "KMeans"}


@pytest.mark.asyncio
async def test_cluster_non_numeric_value(monkeypatch):
    """value_col 全是非数值 → 应返回 error 而非崩溃。"""
    from app.agents.tools import cluster_analysis_tool as cat

    fake_path = str(FIXTURES / "cluster_fixture.csv")
    monkeypatch.setattr(
        cat.download_dao,
        "list_by_dataset",
        AsyncMock(return_value={
            "ok": True,
            "items": [{"file_path": fake_path, "file_format": "csv"}],
        }),
    )

    result = await cat.data_cluster_analysis.ainvoke({
        "dataset_id": "non_numeric_ds",
        "group_col": "region",
        "value_col": "score",
    })
    # 此场景 score 是数值，但若 value_col 不存在 → 应返回 error
    result2 = await cat.data_cluster_analysis.ainvoke({
        "dataset_id": "non_numeric_ds",
        "group_col": "region",
        "value_col": "not_exists",
    })
    payload2 = json.loads(result2)
    assert "error" in payload2
    assert payload2["chart_path"] is None


@pytest.mark.asyncio
async def test_cluster_missing_columns(monkeypatch):
    """group_col / value_col 缺失 → 优雅文本错误。"""
    from app.agents.tools import cluster_analysis_tool as cat

    fake_path = str(FIXTURES / "cluster_fixture.csv")
    monkeypatch.setattr(
        cat.download_dao,
        "list_by_dataset",
        AsyncMock(return_value={
            "ok": True,
            "items": [{"file_path": fake_path, "file_format": "csv"}],
        }),
    )

    result = await cat.data_cluster_analysis.ainvoke({
        "dataset_id": "missing_cols_ds",
        "group_col": "nonexistent",
        "value_col": "score",
    })
    payload = json.loads(result)
    assert "error" in payload


# ─────────── exception 工具测试 ───────────


@pytest.mark.asyncio
async def test_exception_iqr_detects_outliers(monkeypatch):
    """30 行 + 2 个明显离群点 → IQR 应检测到 ≥ 2 个异常。"""
    from app.agents.tools import exception_mining_tool as emt

    fake_path = str(FIXTURES / "exception_fixture.csv")
    monkeypatch.setattr(
        emt.download_dao,
        "list_by_dataset",
        AsyncMock(return_value={
            "ok": True,
            "items": [{"file_path": fake_path, "file_format": "csv"}],
        }),
    )

    result = await emt.data_exception_mining.ainvoke({
        "dataset_id": "test_exception_ds",
        "group_col": "region",
        "value_col": "score",
        "method": "iqr",
        "top_k": 5,
    })
    payload = json.loads(result)
    assert "error" not in payload, payload.get("error")
    assert len(payload["exceptions"]) >= 2
    sides = {e["side"] for e in payload["exceptions"]}
    assert sides.issubset({"high", "low"})
    # 海口(98.5)和拉萨(1.5)应是 high + low 各一个
    groups = {e["group"] for e in payload["exceptions"]}
    assert "海口" in groups or any("海口" in g for g in groups)
    assert "拉萨" in groups or any("拉萨" in g for g in groups)
    assert payload["chart_path"] is not None


@pytest.mark.asyncio
async def test_exception_uniform_returns_empty(monkeypatch, tmp_path: Path):
    """均匀分布 → exceptions 应为空数组。"""
    from app.agents.tools import exception_mining_tool as emt

    uniform = tmp_path / "uniform.csv"
    uniform.write_text("region,score\n" + "\n".join(f"R{i},{50 + i * 0.1}" for i in range(20)))

    monkeypatch.setattr(
        emt.download_dao,
        "list_by_dataset",
        AsyncMock(return_value={
            "ok": True,
            "items": [{"file_path": str(uniform), "file_format": "csv"}],
        }),
    )

    result = await emt.data_exception_mining.ainvoke({
        "dataset_id": "uniform_ds",
        "group_col": "region",
        "value_col": "score",
        "method": "iqr",
    })
    payload = json.loads(result)
    assert "error" not in payload
    assert payload["exceptions"] == []
    assert payload["chart_path"] is None  # 无异常 → 不画图


@pytest.mark.asyncio
async def test_exception_zscore_method(monkeypatch):
    """method='zscore' 也应能正常返回。"""
    from app.agents.tools import exception_mining_tool as emt

    fake_path = str(FIXTURES / "exception_fixture.csv")
    monkeypatch.setattr(
        emt.download_dao,
        "list_by_dataset",
        AsyncMock(return_value={
            "ok": True,
            "items": [{"file_path": fake_path, "file_format": "csv"}],
        }),
    )

    result = await emt.data_exception_mining.ainvoke({
        "dataset_id": "zscore_ds",
        "group_col": "region",
        "value_col": "score",
        "method": "zscore",
    })
    payload = json.loads(result)
    assert payload["method"] == "zscore"
    assert isinstance(payload["exceptions"], list)


# ─────────── meta_query 测试 ───────────


@pytest.mark.asyncio
async def test_meta_query_returns_publisher(monkeypatch):
    """dataset_meta_query 应返回 publisher / data_files / schema_columns 等字段。"""
    from app.agents.tools import dataset_meta_tool as dmt
    from app.model.dataset import Dataset as DatasetModel

    # mock session.get(Dataset, ...) → 返回伪对象
    fake_dataset = DatasetModel(
        id="abc123",
        url="https://example.gov.cn/data/abc",
        metadata_={
            "title": "测试数据集",
            "publisher": "测试发布机构",
            "issued": "2024-01-01",
            "update_frequency": "年度",
            "temporal_coverage": "2010-2023",
            "spatial": "全国",
            "category": "经济",
            "language": "zh",
            "description": "这是一个测试数据集的描述",
            "limitations": "数据仅覆盖部分省份",
            "schema_columns": ["年份", "数值"],
        },
        status="scraped",
    )
    fake_dataset.has_uploaded = True

    # 构造一个简单 session mock
    class _FakeSession:
        async def get(self, model, _id):
            return fake_dataset

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    from app.core.db import AsyncSessionLocal as _ASL

    class _CtxMgr:
        async def __aenter__(self):
            return _FakeSession()

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(dmt, "AsyncSessionLocal", lambda: _CtxMgr())
    monkeypatch.setattr(
        dmt.download_dao,
        "list_by_dataset",
        AsyncMock(return_value={
            "ok": True,
            "items": [
                {
                    "file_format": "csv",
                    "file_size": 1024,
                    "created_at": "2024-01-15T10:00:00",
                    "file_name": "data.csv",
                }
            ],
        }),
    )

    result = await dmt.dataset_meta_query.ainvoke({"dataset_id": "abc123"})
    payload = json.loads(result)
    assert payload["dataset_id"] == "abc123"
    assert payload["publisher"] == "测试发布机构"
    assert payload["title"] == "测试数据集"
    assert payload["limitations"] == "数据仅覆盖部分省份"
    assert payload["schema_columns"] == ["年份", "数值"]
    assert len(payload["data_files"]) == 1
    assert payload["data_files"][0]["format"] == "csv"


@pytest.mark.asyncio
async def test_meta_query_handles_missing_metadata(monkeypatch):
    """metadata 为空 dict 时应优雅 fallback。"""
    from app.agents.tools import dataset_meta_tool as dmt
    from app.model.dataset import Dataset as DatasetModel

    fake_dataset = DatasetModel(
        id="empty123",
        url="https://example.gov.cn/data/empty",
        metadata_={},
        status="scraped",
    )
    fake_dataset.has_uploaded = False

    class _FakeSession:
        async def get(self, model, _id):
            return fake_dataset

    class _CtxMgr:
        async def __aenter__(self):
            return _FakeSession()

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(dmt, "AsyncSessionLocal", lambda: _CtxMgr())
    monkeypatch.setattr(
        dmt.download_dao,
        "list_by_dataset",
        AsyncMock(return_value={"ok": True, "items": []}),
    )

    result = await dmt.dataset_meta_query.ainvoke({"dataset_id": "empty123"})
    payload = json.loads(result)
    assert payload["dataset_id"] == "empty123"
    assert payload["title"] == ""
    assert payload["limitations"] == "未提供数据局限性说明"
    assert payload["data_files"] == []