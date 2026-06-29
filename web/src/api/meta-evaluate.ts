// 元数据评估 API 封装（Phase 2）
// 与后端 /meta-evaluate/evaluations/* 路由一一对应

/** EU MQA 23 条 indicator 满分（前端条形图 / 表格渲染） */
export const EU_MQA_RULE_MAX: Record<string, number> = {
  // Findability
  keyword_usage: 30,
  categories: 30,
  geo_search: 20,
  time_based_search: 20,
  // Accessibility
  access_url_accessibility: 50,
  download_url: 20,
  download_url_accessibility: 30,
  // Interoperability
  format: 20,
  media_type: 10,
  format_vocabulary: 10,
  non_proprietary: 20,
  machine_readable: 20,
  dcat_ap_compliance: 30,
  // Reusability
  license_information: 20,
  license_vocabulary: 10,
  access_restrictions: 10,
  access_restrictions_vocabulary: 5,
  contact_point: 20,
  publisher: 10,
  // Contextuality
  rights: 5,
  file_size: 5,
  date_of_issue: 5,
  modification_date: 5,
}

/** EU MQA 23 条 indicator 顺序（条形图渲染顺序） */
export const EU_MQA_RULE_KEYS: string[] = [
  // Findability
  'keyword_usage', 'categories', 'geo_search', 'time_based_search',
  // Accessibility
  'access_url_accessibility', 'download_url', 'download_url_accessibility',
  // Interoperability
  'format', 'media_type', 'format_vocabulary', 'non_proprietary',
  'machine_readable', 'dcat_ap_compliance',
  // Reusability
  'license_information', 'license_vocabulary', 'access_restrictions',
  'access_restrictions_vocabulary', 'contact_point', 'publisher',
  // Contextuality
  'rights', 'file_size', 'date_of_issue', 'modification_date',
]

/** 5 维满分（雷达图 / 报告用） */
export const EU_MQA_DIMENSION_MAX = {
  discover: 100,
  access: 100,
  interop: 110,
  reuse: 75,
  context: 20,
} as const

/** 评估列表项 */
export interface EvaluationListItem {
  id: number
  dataset_id: string
  score_total: number
  grade: 'Excellent' | 'Good' | 'Sufficient' | 'Bad' | string
  created_at: string | null
}

/** 分页列表响应 */
export interface EvaluationListResponse {
  items: EvaluationListItem[]
  page: number
  size: number
  count: number
}

/** 评估详情（含 5 维分 + rule_scores + Markdown 报告） */
export interface EvaluationDetail extends EvaluationListItem {
  score_discover: number
  score_access: number
  score_interop: number
  score_reuse: number
  score_context: number
  rule_scores: Record<string, number>
  llm_notes: Record<string, unknown>
  evaluation_content: string
  report_json?: Record<string, unknown> | null
}

/** dataset 最新一次 evaluation 摘要 */
export interface LatestEvaluation {
  id: number
  score_total: number
  grade: string
  created_at: string | null
}

/** datasets + latest_evaluation 列表单条 */
export interface DatasetEvalItem {
  id: string
  url: string
  status: 'pending' | 'scraped' | 'failed' | string
  metadata: Record<string, unknown>
  created_at: string | null
  updated_at: string | null
  latest_evaluation: LatestEvaluation | null
}

/** datasets + latest_evaluation 列表响应 */
export interface DatasetEvalListResponse {
  items: DatasetEvalItem[]
  page: number
  size: number
  count: number
}

/** 触发评估 / job 状态响应（异步 job 模型） */
export interface EvaluateJobResponse {
  job_id: number
  dataset_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | string
  evaluation_id: string | null
  error: string | null
  elapsed_ms: number | null
  token_prompt: number | null
  token_completion: number | null
  token_total: number | null
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

/** ResponseModel 通用包装 */
interface ApiEnvelope<T> {
  code: number
  data: T | null
  msg: string
}

const BASE = '/api/meta-evaluate'

async function unwrap<T>(res: Response): Promise<T> {
  const json = (await res.json()) as ApiEnvelope<T>
  if (!res.ok || json.code !== 200 || json.data === null) {
    throw new Error(json.msg || `HTTP ${res.status}`)
  }
  return json.data
}

/** 触发一次评估（异步，立即返回 job_id） */
export async function triggerEvaluate(datasetId: string): Promise<EvaluateJobResponse> {
  const res = await fetch(`${BASE}/evaluations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId }),
  })
  return unwrap<EvaluateJobResponse>(res)
}

/** 查询评估 job 状态 */
export async function getEvaluationJob(jobId: number): Promise<EvaluateJobResponse> {
  const res = await fetch(`${BASE}/evaluations/jobs/${jobId}`)
  return unwrap<EvaluateJobResponse>(res)
}

/** 单 evaluation 详情 */
export async function getEvaluation(id: number | string): Promise<EvaluationDetail> {
  const res = await fetch(`${BASE}/evaluations/${id}`)
  return unwrap<EvaluationDetail>(res)
}

/** 按 dataset_id 拉评估历史 */
export async function listEvaluations(
  datasetId: string,
  page = 1,
  size = 20,
  grade?: string,
): Promise<EvaluationListResponse> {
  const qs = new URLSearchParams({
    dataset_id: datasetId,
    page: String(page),
    size: String(size),
  })
  if (grade) qs.set('grade', grade)
  const res = await fetch(`${BASE}/evaluations?${qs.toString()}`)
  return unwrap<EvaluationListResponse>(res)
}

/** datasets 列表 + 每条 dataset 的最新 evaluation 摘要 */
export async function listDatasetsWithEvaluation(
  page = 1,
  size = 20,
  status?: string,
): Promise<DatasetEvalListResponse> {
  const qs = new URLSearchParams({
    page: String(page),
    size: String(size),
  })
  if (status) qs.set('status', status)
  const res = await fetch(`${BASE}/datasets?${qs.toString()}`)
  return unwrap<DatasetEvalListResponse>(res)
}