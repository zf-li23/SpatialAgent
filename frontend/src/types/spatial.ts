// ============================================================
// SpatialAgent — 空间组学数据类型定义
// ============================================================

// --- API 请求/响应 ---

export interface ChatRequest {
  message: string
  session_id?: string
  data_path?: string
}

export interface PlanStep {
  step: number
  skill: string
  purpose: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  args?: Record<string, unknown>
}

export interface SkillResult {
  skill: string
  output: Record<string, unknown>
  error?: string
}

export interface VisualizationData {
  plot_type: 'scatter' | 'heatmap' | 'umap' | 'table'
  data: unknown
  layout?: Record<string, unknown>
}

export interface ChatResponse {
  plan?: PlanStep[]
  results?: SkillResult[]
  explanation: string
  visualization?: VisualizationData
}

// --- 数据集 ---

export interface DatasetInfo {
  name: string
  path: string
  shape: [number, number]
  n_spots: number
  n_genes: number
}

// --- QC 结果 ---

export interface QCResult {
  n_spots: number
  n_genes: number
  median_genes_per_spot: number
  median_umi_per_spot: number
  pct_mito: number
  pct_ribo: number
  spatial_coords_shape: [number, number]
}

// --- 空间可变基因结果 ---

export interface SVGGene {
  gene: string
  moran_i: number
  p_value: number
}

export interface SpatialPatternResult {
  top_svg_genes: SVGGene[]
  n_significant_genes: number
  method: string
  n_spots: number
}

// --- 区域查询 ---

export interface RegionQueryRequest {
  x_min: number
  x_max: number
  y_min: number
  y_max: number
  gene_list: string[]
}

export interface RegionQueryResult {
  region: { x_range: [number, number]; y_range: [number, number] }
  n_spots_in_region: number
  gene_expression: Record<string, { mean: number; std: number }>
}

// --- 轨迹 ---

export interface PseudotimeSpot {
  index: number
  pseudotime: number
  branch: string
}

export interface TrajectoryResult {
  n_spots: number
  pseudotime_range: [number, number]
  n_branches: number
  root_spot_index: number
  spots: PseudotimeSpot[]
}

// --- 细胞通讯 ---

export interface LigandReceptorPair {
  ligand: string
  receptor: string
  score: number
}

export interface CellCommResult {
  n_significant_pairs: number
  top_interactions: LigandReceptorPair[]
  method: string
}

// --- 自适应流水线 ---

export interface PipelineStage {
  type: 'PROCESSING' | 'QC' | 'ANALYSIS' | 'VISUALIZATION'
  skill: string
  purpose: string
  status: 'pending' | 'running' | 'completed' | 'failed'
}

export interface PipelineDefinition {
  pipeline_name: string
  stages: PipelineStage[]
  estimated_runtime_seconds: number
}
