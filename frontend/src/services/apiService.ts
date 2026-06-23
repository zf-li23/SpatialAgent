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

export async function listSkills(): Promise<string[]> {
  const { data } = await api.get<string[]>('/skills')
  return data
}

// --- 数据集 ---

export async function listDatasets(): Promise<DatasetInfo[]> {
  const { data } = await api.get<DatasetInfo[]>('/datasets')
  return data
}

// --- 健康检查 ---

export async function healthCheck(): Promise<{ status: string }> {
  const { data } = await api.get<{ status: string }>('/health')
  return data
}
