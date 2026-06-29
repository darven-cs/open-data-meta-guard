// 数据采集 API 封装（Phase 3）
// 与后端 /data-collect/* 路由一一对应

/** 上传响应 */
export interface UploadResponse {
  download_id: number
  dataset_id: string
  file_name: string
  file_format: 'csv' | 'xlsx' | 'json' | string
  file_size: number
  file_sha256: string
  created_at: string | null
}

/** 列表单条 */
export interface DownloadListItem {
  id: number
  dataset_id: string
  file_name: string
  file_format: string
  file_size: number
  file_sha256: string
  source: string
  status: string
  created_at: string | null
}

/** 列表响应 */
export interface DownloadListResponse {
  items: DownloadListItem[]
  page: number
  size: number
  count: number
}

/** 详情响应 */
export interface DownloadDetail extends DownloadListItem {
  file_path: string
  error_message: string | null
}

/** 列表单条（按 dataset 维度） */
export interface DatasetSelectItem {
  id: string
  url: string
  has_uploaded: boolean
  status: string
  created_at: string | null
}

/** 列表响应（分页） */
export interface DatasetSelectListResponse {
  items: DatasetSelectItem[]
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

const BASE = '/api/data-collect'

async function unwrap<T>(res: Response): Promise<T> {
  const json = (await res.json()) as ApiEnvelope<T>
  if (!res.ok || json.code !== 200 || json.data === null) {
    throw new Error(json.msg || `HTTP ${res.status}`)
  }
  return json.data
}

/** 分页拉取 datasets 列表 */
export async function listDatasets(
  page = 1,
  size = 20,
): Promise<DatasetSelectListResponse> {
  const qs = new URLSearchParams({ page: String(page), size: String(size) })
  const res = await fetch(`${BASE}/datasets?${qs.toString()}`)
  return unwrap<DatasetSelectListResponse>(res)
}

/** 上传文件（XHR 走 onprogress）。 */
export function upload(
  datasetId: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<UploadResponse> {
  return new Promise<UploadResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const form = new FormData()
    form.append('dataset_id', datasetId)
    form.append('file', file, file.name)

    xhr.open('POST', `${BASE}/upload`)
    xhr.responseType = 'json'
    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return
      onProgress?.(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onerror = () => reject(new Error('network error'))
    xhr.onload = () => {
      const json = (xhr.response ?? null) as ApiEnvelope<UploadResponse> | null
      if (xhr.status >= 200 && xhr.status < 300 && json && json.code === 200 && json.data) {
        onProgress?.(100)
        resolve(json.data)
      } else {
        reject(new Error(json?.msg || `HTTP ${xhr.status}`))
      }
    }
    xhr.send(form)
  })
}

/** 按 dataset_id 拉上传列表 */
export async function listDownloads(
  datasetId: string,
  page = 1,
  size = 20,
): Promise<DownloadListResponse> {
  const qs = new URLSearchParams({
    dataset_id: datasetId,
    page: String(page),
    size: String(size),
  })
  const res = await fetch(`${BASE}?${qs.toString()}`)
  return unwrap<DownloadListResponse>(res)
}

/** 详情 */
export async function getDownload(id: number): Promise<DownloadDetail> {
  const res = await fetch(`${BASE}/${id}`)
  return unwrap<DownloadDetail>(res)
}

/** 删除（同时删磁盘文件） */
export async function deleteDownload(id: number): Promise<void> {
  const res = await fetch(`${BASE}/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const json = (await res.json().catch(() => null)) as ApiEnvelope<unknown> | null
    throw new Error(json?.msg || `HTTP ${res.status}`)
  }
}

/** 给 <a> 直接下载用的 URL */
export function buildDownloadUrl(id: number): string {
  return `${BASE}/${id}/download`
}