// 首页 5 功能区元数据（v2.0 简化）
// v1.0 → v2.0 改造：
//   - 去掉 meta-report / quality-report / data-story（v2.0 砍掉报告层）
//   - 新增 meta-evaluate / data-quality（独立评估能力）
//   - ready 全部 false：Phase 0 占位，Phase 1-5 依次点亮

export interface Feature {
  /** 路由 segment，与 path 一致 */
  id: string
  /** 中文标题（卡片主标题，Fraunces 衬线） */
  title: string
  /** 英文 / 副标题（标题下方，Fraunces 斜体） */
  subtitle: string
  /** 2-3 句功能简介（Inter Tight 正文） */
  description: string
  /**
   * inline SVG path d= (24×24 viewBox, 1.5px stroke, currentColor)。
   * 瑞士风几何，线条结构清晰。
   */
  iconPath: string
  /** 唯一 ready 的卡片显示「In Preparation」以外的标记 */
  ready: boolean
}

export const FEATURES: Feature[] = [
  {
    id: 'meta-collect',
    title: '元数据采集',
    subtitle: 'Metadata Ingestion',
    description:
      '从数据源抽取 schema / 字段 / 数据规模等元数据，为后续评估与报告提供原料。',
    // 三个方块堆叠，表「分层元数据」
    iconPath:
      'M3 6h7v4H3zM14 6h7v4h-7zM3 14h7v4H3zM14 14h7v4h-7z',
    ready: true,  // Phase 1 完成
  },
  {
    id: 'meta-evaluate',
    title: '元数据评估',
    subtitle: 'Metadata Evaluation',
    description:
      '基于 EU MQA（Metadata Quality Assurance）规则评估元数据合规性，输出打分与改进建议。',
    // 文档 + 对勾，表「质量评估」
    iconPath:
      'M6 3h9l4 4v14H6zM15 3v4h4M9 13l2 2 4-4',
    ready: true,   // Phase 2 点亮
  },
  {
    id: 'data-collect',
    title: '数据采集',
    subtitle: 'Data Acquisition',
    description:
      '上传本地数据文件（CSV / XLSX / JSON / XML），建立数据集并入库管理。',
    // 下行箭头入箱，表「采集入库」
    iconPath:
      'M12 3v12m0 0l-4-4m4 4l4-4M5 21h14',
    ready: false,  // Phase 3 点亮
  },
  {
    id: 'data-quality',
    title: '数据质量评估',
    subtitle: 'Data Quality',
    description:
      'pandera schema 校验 + ydata-profiling + LLM 综合评估，产出数据质量报告与改进建议。',
    // 柱状图，表「质量评估」
    iconPath:
      'M4 20V8m5 12V4m5 16v-7m5 7V11M3 20h18',
    ready: false,  // Phase 4 点亮
  },
  {
    id: 'chat',
    title: '数据小D',
    subtitle: 'Data Agent',
    description:
      '对话式 LLM agent，自然语言触发上述所有数据能力，是整个系统的主入口。',
    // 对话气泡，呼应 ChatLayout 主形象
    iconPath:
      'M4 5h16v11H8l-4 4zM8 9h8M8 12h5',
    ready: true,  // Phase 5 骨架先亮
  },
]

/** 根据 id 找 feature，找不到返回 undefined */
export function findFeature(id: string): Feature | undefined {
  return FEATURES.find((f) => f.id === id)
}
