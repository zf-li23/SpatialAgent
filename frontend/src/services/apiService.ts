// ============================================================
// SpatialAgent — API 服务封装
// ============================================================

import axios from 'axios'
import type {
  ChatRequest,
  ChatResponse,
  SkillResult,
  DatasetInfo,
} from '../types/spatial'

const BASE_URL = import.meta.env.VITE_OPENCLAW_API_URL || 'http://localhost:3000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 300_000, // 5 min for long-running skills
  headers: { 'Content-Type': 'application/json' },
})

// --- 聊天 ---

export async function sendChat(request: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat', request)
  return data
}

// --- 技能执行 ---

export async function executeSkill(
  skillName: string,
  args: Record<string, unknown>
): Promise<SkillResult> {
  const { data } = await api.post<SkillResult>(`/skills/${skillName}`, args)
  return data
}

// --- 技能列表 ---

export interface SkillInfo {
  name: string
  description: string
  triggers: string[]
}

export async function listSkills(): Promise<SkillInfo[]> {
  const { data } = await api.get<SkillInfo[]>('/skills')
  return data
}

// --- 数据集 ---

export async function listDatasets(): Promise<DatasetInfo[]> {
  const { data } = await api.get<DatasetInfo[]>('/datasets')
  return data
}

// --- 健康检查 ---

export async function healthCheck(): Promise<{ status: string; version?: string; skills?: number }> {
  const { data } = await api.get<{ status: string; version?: string; skills?: number }>('/health')
  return data
}

// --- 自适应流水线 ---

export interface AdaptiveResponse {
  mode: string
  pipeline: {
    pipeline_name: string
    stages: Array<{
      type: string
      skill: string
      purpose: string
      status: string
    }>
    explanation: string
    estimated_runtime_seconds: number
  }
  results: SkillResult[]
}

export async function adaptivePipeline(request: ChatRequest): Promise<AdaptiveResponse> {
  const { data } = await api.post<AdaptiveResponse>('/adaptive', request)
  return data
}
