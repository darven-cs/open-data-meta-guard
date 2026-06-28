// 元数据采集 API 封装（Phase 1）
// 与后端 /meta-collect/datasets/* 路由一一对应

/** 数据集（列表项 / 详情通用） */
export interface Dataset {
  id: string
  url: string
  metadata: Record<string, unknown>
  status: 'pending' | 'scraped' | 'failed' | string
  created_at: string | null
  updated_at: string | null
}

/** 分页列表响应 */
export interface DatasetListResponse {
  items: Dataset[]
  page: number
  size: number
  count: number
}

/** 采集单条结果 */
export interface IngestItem {
  url: string
  dataset_id: string
  status: 'scraped' | 'failed'
  error_message: string | null
}

/** 采集响应 */
export interface IngestResponse {
  ok: boolean
  items: IngestItem[]
  success_count: number
  failed_count: number
}

/** ResponseModel 通用包装 */
interface ApiEnvelope<T> {
  code: number
  data: T | null
  msg: string
}

const BASE = '/api/meta-collect'

async function unwrap<T>(res: Response): Promise<T> {
  const json = (await res.json()) as ApiEnvelope<T>
  if (!res.ok || json.code !== 200 || json.data === null) {
    throw new Error(json.msg || `HTTP ${res.status}`)
  }
  return json.data
}

/** 批量采集（同步阻塞，等待所有 URL 处理完返回 items） */
export async function ingest(urls: string[]): Promise<IngestResponse> {
  const res = await fetch(`${BASE}/datasets/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ urls }),
  })
  return unwrap<IngestResponse>(res)
}

/** 分页列表（按 created_at DESC；可按 status 过滤） */
export async function listDatasets(
  page = 1,
  size = 20,
  status?: string,
): Promise<DatasetListResponse> {
  const qs = new URLSearchParams({
    page: String(page),
    size: String(size),
  })
  if (status) qs.set('status', status)
  const res = await fetch(`${BASE}/datasets?${qs.toString()}`)
  return unwrap<DatasetListResponse>(res)
}

/** 单 dataset 详情 */
export async function getDataset(id: string): Promise<Dataset> {
  const res = await fetch(`${BASE}/datasets/${encodeURIComponent(id)}`)
  return unwrap<Dataset>(res)
}

/** 整块覆盖 metadata */
export async function updateDataset(
  id: string,
  metadata: Record<string, unknown>,
): Promise<Dataset> {
  const res = await fetch(`${BASE}/datasets/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ metadata }),
  })
  return unwrap<Dataset>(res)
}

/** 删除 dataset（幂等） */
export async function deleteDataset(id: string): Promise<void> {
  const res = await fetch(`${BASE}/datasets/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const json = (await res.json().catch(() => null)) as ApiEnvelope<unknown> | null
    throw new Error(json?.msg || `HTTP ${res.status}`)
  }
}
