// 知识图谱 API 封装（Phase 5）
// 与后端 /kg/* 路由一一对应

/** 图节点 */
export interface GraphNode {
  id: string
  type: 'Dataset' | 'Publisher' | 'Theme' | 'Keyword' | 'Format'
  label: string
  source_field?: string | null
}

/** 图边 */
export interface GraphEdge {
  source: string
  target: string
  type: string
  weight: number
}

/** 图数据响应 */
export interface GraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

/** 图谱构建结果 */
export interface KgBuildResult {
  datasets_processed: number
  entities_upserted: number
  relationships_created: number
  similar_edges: number
  errors: string[]
}

/** 实体列表项 */
export interface EntityListItem {
  id: string
  type: string
  name: string
  dataset_count: number
}

/** 实体列表响应 */
export interface EntityListResponse {
  items: EntityListItem[]
  page: number
  size: number
  count: number
}

/** 实体详情 */
export interface EntityDetail {
  id: string
  type: string
  name: string
  related_datasets: Array<{
    dataset_id: string
    rel_type: string
    confidence: number | null
  }>
}

/** ResponseModel 通用包装 */
interface ApiEnvelope<T> {
  code: number
  data: T | null
  msg: string
}

const BASE = '/api/kg'

async function unwrap<T>(res: Response): Promise<T> {
  const json = (await res.json()) as ApiEnvelope<T>
  if (!res.ok || json.code !== 200 || json.data === null) {
    throw new Error(json.msg || `HTTP ${res.status}`)
  }
  return json.data
}

/** 全量重建知识图谱 */
export async function buildGraph(): Promise<KgBuildResult> {
  const res = await fetch(`${BASE}/build`, { method: 'POST' })
  return unwrap<KgBuildResult>(res)
}

/** 获取图数据 */
export async function getGraph(entityTypes?: string[]): Promise<GraphResponse> {
  const qs = new URLSearchParams()
  if (entityTypes && entityTypes.length > 0) {
    qs.set('entity_types', entityTypes.join(','))
  }
  const url = qs.toString() ? `${BASE}/graph?${qs.toString()}` : `${BASE}/graph`
  const res = await fetch(url)
  return unwrap<GraphResponse>(res)
}

/** 分页实体列表 */
export async function listEntities(
  type?: string,
  page = 1,
  size = 20,
): Promise<EntityListResponse> {
  const qs = new URLSearchParams({ page: String(page), size: String(size) })
  if (type) qs.set('type', type)
  const res = await fetch(`${BASE}/entities?${qs.toString()}`)
  return unwrap<EntityListResponse>(res)
}

/** 实体详情 */
export async function getEntityDetail(entityId: string): Promise<EntityDetail> {
  const res = await fetch(`${BASE}/entities/${encodeURIComponent(entityId)}`)
  return unwrap<EntityDetail>(res)
}

/** 数据集的所有关系 */
export async function getDatasetRelations(datasetId: string): Promise<GraphResponse> {
  const res = await fetch(`${BASE}/datasets/${datasetId}/relations`)
  return unwrap<GraphResponse>(res)
}
