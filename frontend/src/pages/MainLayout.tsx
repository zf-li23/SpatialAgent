// ============================================================
// SpatialAgent — 主布局（左聊天 / 右可视化）
// ============================================================

import { useState, useCallback } from 'react'
import ChatPanel from '../components/ChatPanel'
import SpatialDashboard from '../components/SpatialDashboard'
import type {
  PlanStep,
  SkillResult,
  DatasetInfo,
} from '../types/spatial'

export default function MainLayout() {
  const [plan, setPlan] = useState<PlanStep[]>([])
  const [results, setResults] = useState<SkillResult[]>([])
  const [activeDataset, setActiveDataset] = useState<DatasetInfo | null>(null)

  const handleChatResponse = useCallback(
    (response: { plan?: PlanStep[]; results?: SkillResult[] }) => {
      if (response.plan) setPlan(response.plan)
      if (response.results) setResults((prev) => [...prev, ...response.results!])
    },
    []
  )

  const handleDatasetChange = useCallback((dataset: DatasetInfo | null) => {
    setActiveDataset(dataset)
    setPlan([])
    setResults([])
  }, [])

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      {/* 左侧面板：聊天 */}
      <div
        className="flex flex-col border-r"
        style={{
          width: '380px',
          minWidth: '320px',
          backgroundColor: 'var(--color-panel)',
          borderColor: 'var(--color-border)',
        }}
      >
        {/* 标题栏 */}
        <div
          className="flex items-center gap-2 px-4 py-3 border-b shrink-0"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <span className="text-xl">🧬</span>
          <span className="font-bold text-lg" style={{ color: 'var(--color-accent)' }}>
            SpatialAgent
          </span>
          <span className="text-xs px-2 py-0.5 rounded" style={{
            backgroundColor: 'var(--color-accent2)',
            color: '#fff',
          }}>
            v0.1
          </span>
        </div>

        {/* 聊天面板 */}
        <div className="flex-1 overflow-hidden">
          <ChatPanel
            onResponse={handleChatResponse}
            activeDataset={activeDataset}
            onDatasetChange={handleDatasetChange}
            plan={plan}
          />
        </div>
      </div>

      {/* 右侧面板：可视化 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <SpatialDashboard
          plan={plan}
          results={results}
          activeDataset={activeDataset}
        />
      </div>
    </div>
  )
}
