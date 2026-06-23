// ============================================================
// SpatialAgent — 流水线可视化组件
// 展示 AdaptivePlanner 生成的流水线节点及其执行状态
// ============================================================

import { useEffect, useState } from 'react'

export interface PipelineStage {
  type: 'PROCESSING' | 'QC' | 'ANALYSIS' | 'VISUALIZATION'
  skill: string
  purpose: string
  status: 'pending' | 'running' | 'completed' | 'failed'
}

interface Props {
  pipelineName?: string
  stages: PipelineStage[]
  explanation?: string
  estimatedRuntime?: number
  onClose?: () => void
}

const TYPE_ICONS: Record<string, string> = {
  PROCESSING: '📥',
  QC: '🔍',
  ANALYSIS: '🧬',
  VISUALIZATION: '📊',
}

const TYPE_COLORS: Record<string, string> = {
  PROCESSING: '#3b82f6',
  QC: '#f59e0b',
  ANALYSIS: '#06b6d4',
  VISUALIZATION: '#10b981',
}

export default function PipelineVisualizer({
  pipelineName = '分析流水线',
  stages,
  explanation,
  estimatedRuntime,
  onClose,
}: Props) {
  const [animated, setAnimated] = useState(false)

  useEffect(() => {
    setAnimated(true)
  }, [])

  return (
    <div className="px-3 py-3 rounded-lg" style={{ backgroundColor: 'var(--color-bg)', border: '1px solid var(--color-border)' }}>
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm">🔄</span>
          <span className="text-xs font-bold" style={{ color: 'var(--color-accent)' }}>
            {pipelineName}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {estimatedRuntime && (
            <span className="text-xs" style={{ color: 'var(--color-muted)' }}>
              ⏱ ~{estimatedRuntime}s
            </span>
          )}
          {onClose && (
            <button onClick={onClose} className="text-xs hover:opacity-70" style={{ color: 'var(--color-muted)' }}>
              ✕
            </button>
          )}
        </div>
      </div>

      {/* 说明 */}
      {explanation && (
        <p className="text-xs mb-2 italic" style={{ color: 'var(--color-muted)' }}>
          {explanation}
        </p>
      )}

      {/* 节点流程 */}
      <div className="flex items-center gap-0 overflow-x-auto py-1">
        {stages.map((stage, i) => (
          <div key={i} className="flex items-center gap-0 shrink-0">
            {/* 节点 */}
            <div
              className="flex flex-col items-center px-2 py-1.5 rounded-md min-w-[80px] transition-all duration-500"
              style={{
                backgroundColor: stage.status === 'running' ? `${TYPE_COLORS[stage.type]}20` : 'transparent',
                border: `1px solid ${stage.status === 'running' ? TYPE_COLORS[stage.type] : 'var(--color-border)'}`,
                opacity: animated ? 1 : 0,
                transform: animated ? 'translateY(0)' : 'translateY(10px)',
                transitionDelay: `${i * 150}ms`,
              }}
            >
              <span className="text-lg">
                {stage.status === 'completed' ? '✅' : stage.status === 'running' ? '🔄' : stage.status === 'failed' ? '❌' : TYPE_ICONS[stage.type]}
              </span>
              <span className="text-[10px] font-medium mt-0.5 text-center leading-tight" style={{
                color: stage.status === 'running' ? TYPE_COLORS[stage.type] : 'var(--color-text)',
              }}>
                {stage.purpose.length > 12 ? stage.purpose.slice(0, 12) + '…' : stage.purpose}
              </span>
              {stage.skill && (
                <span className="text-[9px] mt-0.5 px-1 rounded" style={{
                  backgroundColor: `${TYPE_COLORS[stage.type]}30`,
                  color: TYPE_COLORS[stage.type],
                }}>
                  {stage.skill}
                </span>
              )}
            </div>

            {/* 连线箭头 */}
            {i < stages.length - 1 && (
              <div className="flex items-center mx-0.5">
                <div
                  className="h-0.5 w-4 transition-all duration-700"
                  style={{
                    backgroundColor: stages[i].status === 'completed' ? 'var(--color-accent)' : 'var(--color-border)',
                  }}
                />
                <span className="text-[10px]" style={{ color: 'var(--color-muted)' }}>→</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 进度条 */}
      <div className="mt-2">
        <div className="h-1 rounded-full" style={{ backgroundColor: 'var(--color-border)' }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${(stages.filter((s) => s.status === 'completed').length / Math.max(stages.length, 1)) * 100}%`,
              backgroundColor: 'var(--color-accent)',
            }}
          />
        </div>
        <div className="flex justify-between mt-0.5">
          <span className="text-[10px]" style={{ color: 'var(--color-muted)' }}>
            {stages.filter((s) => s.status === 'completed').length}/{stages.length} 完成
          </span>
          {stages.some((s) => s.status === 'running') && (
            <span className="text-[10px] animate-pulse" style={{ color: 'var(--color-accent)' }}>
              执行中...
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
