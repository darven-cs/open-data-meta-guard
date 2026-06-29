// 数据质量评估 API 封装（Phase 4）

/** 评估列表项 */
export interface QualityListItem {
  id: number
  dataset_id: string
  data_download_id: number
  file_name?: string
  summary: Record<string, unknown>
  created_at: string | null
}

/** 语义层脏数据问题 */
export interface SemanticIssue {
  category: string
  severity: "error" | "warning" | "info"
  dimension: string
  field: string | null
  description: string
  suggestion: string
}

/** QualityDetail.summary 扩展（含可选语义维度评分） */
export interface QualitySummary {
  n: number; p: number
  n_missing: number; p_missing: number
  n_duplicates: number; p_duplicates: number
  memory_size: string
  completeness_score?: number
  consistency_score?: number
  accuracy_score?: number
  timeliness_score?: number
  uniqueness_score?: number
  normativity_score?: number
  openness_score?: number
  security_score?: number
  overall_score?: number
}

/** 评估详情 */
export interface QualityDetail extends QualityListItem {
  evaluation_content: string
  issues: Array<Record<string, unknown>>
}

/** 分页列表响应 */
export interface QualityListResponse {
  items: QualityListItem[]
  page: number
  size: number
  count: number
}

/** 触发响应 */
export interface QualityResponse {
  ok: boolean
  evaluation_id: number
  data_download_id: number
  created_at: string
}

/** data_download 最新 quality eval 摘要 */
export interface LatestQualitySummary {
  id: number
  summary: Record<string, unknown>
  created_at: string | null
}

/** data_download + latest_evaluation */
export interface DownloadWithQualityItem {
  id: number
  dataset_id: string
  file_name: string
  file_format: string
  file_size: number
  file_sha256: string
  source: string
  status: string
  created_at: string | null
  latest_evaluation: LatestQualitySummary | null
}

/** downloads + latest_evaluation 列表 */
export interface DownloadWithQualityListResponse {
  items: DownloadWithQualityItem[]
  page: number
  size: number
  count: number
}

/** ResponseModel 通用包装 */
interface ApiEnvelope<T> {
  code: number
  data: T | null
  msg: string
}

const BASE = '/api/data-quality'

async function unwrap<T>(res: Response): Promise<T> {
  const json = (await res.json()) as ApiEnvelope<T>
  if (!res.ok || json.code !== 200 || json.data === null) {
    throw new Error(json.msg || `HTTP ${res.status}`)
  }
  return json.data
}

/** 触发数据质量评估（同步） */
export async function evaluate(dataDownloadId: number): Promise<QualityResponse> {
  const res = await fetch(`${BASE}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data_download_id: dataDownloadId }),
  })
  return unwrap<QualityResponse>(res)
}

/** 单条评估详情 */
export async function getQuality(id: number): Promise<QualityDetail> {
  const res = await fetch(`${BASE}/${id}`)
  return unwrap<QualityDetail>(res)
}

/** 按 dataset_id 列评估历史 */
export async function listQualities(
  datasetId: string,
  page = 1,
  size = 20,
): Promise<QualityListResponse> {
  const qs = new URLSearchParams({
    dataset_id: datasetId,
    page: String(page),
    size: String(size),
  })
  const res = await fetch(`${BASE}?${qs.toString()}`)
  return unwrap<QualityListResponse>(res)
}

/** data_downloads + 最新 quality eval 摘要 */
export async function listDownloadsWithQuality(
  page = 1,
  size = 20,
): Promise<DownloadWithQualityListResponse> {
  const qs = new URLSearchParams({
    page: String(page),
    size: String(size),
  })
  const res = await fetch(`${BASE}/downloads?${qs.toString()}`)
  return unwrap<DownloadWithQualityListResponse>(res)
}
