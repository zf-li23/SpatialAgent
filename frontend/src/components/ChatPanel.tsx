// ============================================================
// SpatialAgent — 聊天面板
// ============================================================

import { useState, useRef, useEffect, useCallback } from 'react'
import type {
  PlanStep,
  SkillResult,
  DatasetInfo,
  PipelineDefinition,
  PipelineStage,
} from '../types/spatial'
import * as api from '../services/apiService'

interface ChatPanelProps {
  onResponse: (response: {
    plan?: PlanStep[]
    results?: SkillResult[]
    pipeline?: PipelineDefinition
  }) => void
  activeDataset: DatasetInfo | null
  onDatasetChange: (dataset: DatasetInfo | null) => void
  plan: PlanStep[]
  pipeline: PipelineDefinition | null
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  planSteps?: PlanStep[]
}

const QUICK_COMMANDS = [
  { label: '📊 数据质控', msg: '加载数据并进行质量控制' },
  { label: '🎯 空间高变基因', msg: '分析这个切片的空间高变基因' },
  { label: '🗺️ 区域查询', msg: '查询某个区域的基因表达' },
  { label: '🛤️ 空间轨迹', msg: '分析空间轨迹和伪时间' },
  { label: '📡 细胞通讯', msg: '分析配体-受体互作' },
]

export default function ChatPanel({
  onResponse,
  activeDataset,
  onDatasetChange,
  plan,
  pipeline,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [datasets, setDatasets] = useState<DatasetInfo[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 初始化加载数据集列表
  useEffect(() => {
    api.listDatasets().then(setDatasets).catch(() => {
      // 模拟数据
      setDatasets([
        { name: 'visium_lymph_node.h5ad', path: '../data/visium_lymph_node.h5ad', shape: [4035, 36601], n_spots: 4035, n_genes: 36601 },
      ])
    })
  }, [])

  // 自动滚动
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const addMessage = useCallback(
    (role: ChatMessage['role'], content: string, planSteps?: PlanStep[]) => {
      setMessages((prev) => [...prev, { role, content, timestamp: new Date(), planSteps }])
    },
    []
  )

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    addMessage('user', text)
    setLoading(true)

    // 模拟 Pipeline 定义（后续由网关返回）
    const mockPipeline: PipelineDefinition = {
      pipeline_name: '空间组学分析流水线',
      stages: [
        { type: 'PROCESSING', skill: 'st_preprocess', purpose: '加载数据并进行质控', status: 'pending' },
        { type: 'ANALYSIS', skill: 'st_spatial_pattern', purpose: '识别空间可变基因', status: 'pending' },
        { type: 'VISUALIZATION', skill: '', purpose: '渲染可视化结果', status: 'pending' },
      ],
      estimated_runtime_seconds: 30,
    }

    onResponse({ pipeline: mockPipeline })

    // 模拟逐步执行
    setTimeout(() => {
      const updatedStages: PipelineStage[] = [
        { ...mockPipeline.stages[0], status: 'completed' },
        { ...mockPipeline.stages[1], status: 'running' },
        { ...mockPipeline.stages[2], status: 'pending' },
      ]
      onResponse({ pipeline: { ...mockPipeline, stages: updatedStages } })
    }, 1500)

    setTimeout(() => {
      addMessage('assistant', generateMockResponse(text))
      setLoading(false)
    }, 3000)
  }, [input, loading, addMessage, onResponse])

  const handleQuickCommand = useCallback(
    (msg: string) => {
      setInput(msg)
    },
    []
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  return (
    <div className="flex flex-col h-full">
      {/* 数据集选择 */}
      <div className="px-3 py-2 border-b shrink-0" style={{ borderColor: 'var(--color-border)' }}>
        <label className="text-xs font-medium" style={{ color: 'var(--color-muted)' }}>
          📦 数据集
        </label>
        <select
          className="w-full mt-1 px-2 py-1.5 rounded text-sm outline-none"
          style={{
            backgroundColor: 'var(--color-bg)',
            color: 'var(--color-text)',
            border: '1px solid var(--color-border)',
          }}
          value={activeDataset?.name ?? ''}
          onChange={(e) => {
            const ds = datasets.find((d) => d.name === e.target.value) ?? null
            onDatasetChange(ds)
          }}
        >
          <option value="">-- 选择数据集 --</option>
          {datasets.map((ds) => (
            <option key={ds.name} value={ds.name}>
              {ds.name} ({ds.n_spots} spots)
            </option>
          ))}
        </select>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-8" style={{ color: 'var(--color-muted)' }}>
            <p className="text-3xl mb-2">🧬</p>
            <p className="text-sm">欢迎使用 SpatialAgent</p>
            <p className="text-xs mt-1">选择数据集后，在下方输入分析指令</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className="max-w-[90%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap"
              style={{
                backgroundColor:
                  msg.role === 'user' ? 'var(--color-accent)' : 'var(--color-bg)',
                color:
                  msg.role === 'user' ? '#fff' : 'var(--color-text)',
              }}
            >
              {msg.content}
              {msg.planSteps && msg.planSteps.length > 0 && (
                <div className="mt-2 pt-2 border-t" style={{ borderColor: 'var(--color-border)' }}>
                  <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-accent)' }}>
                    📋 执行计划：
                  </p>
                  {msg.planSteps.map((step) => (
                    <div key={step.step} className="text-xs flex items-center gap-1 py-0.5">
                      <span>{step.status === 'completed' ? '✅' : step.status === 'running' ? '🔄' : '⏳'}</span>
                      <span>{step.purpose}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* 快捷指令 */}
      <div className="px-3 py-2 border-t shrink-0 flex flex-wrap gap-1" style={{ borderColor: 'var(--color-border)' }}>
        {QUICK_COMMANDS.map((cmd) => (
          <button
            key={cmd.label}
            className="text-xs px-2 py-1 rounded-full transition-colors hover:opacity-80"
            style={{
              backgroundColor: 'var(--color-bg)',
              color: 'var(--color-muted)',
              border: '1px solid var(--color-border)',
            }}
            onClick={() => handleQuickCommand(cmd.msg)}
          >
            {cmd.label}
          </button>
        ))}
      </div>

      {/* 输入框 */}
      <div className="px-3 py-2 border-t shrink-0" style={{ borderColor: 'var(--color-border)' }}>
        <div className="flex gap-2">
          <textarea
            className="flex-1 px-3 py-2 rounded-lg text-sm resize-none outline-none"
            style={{
              backgroundColor: 'var(--color-bg)',
              color: 'var(--color-text)',
              border: '1px solid var(--color-border)',
            }}
            rows={2}
            placeholder="输入空间组学分析指令..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="px-4 rounded-lg text-sm font-medium transition-opacity shrink-0"
            style={{
              backgroundColor: 'var(--color-accent)',
              color: '#fff',
              opacity: loading ? 0.5 : 1,
            }}
            disabled={loading}
            onClick={handleSend}
          >
            {loading ? '⏳' : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}

// --- 模拟响应（后续替换为真实 API 调用） ---

function generateMockResponse(userMessage: string): string {
  if (userMessage.includes('质控') || userMessage.includes('QC')) {
    return `✅ 质控完成！

数据集: visium_lymph_node.h5ad
Spots: 4,035
Genes: 36,601

QC 指标:
• 中位基因数/spot: 1,800
• 中位 UMI/spot: 4,500
• 线粒体比例: 5.2%
• 核糖体比例: 12.8%`
  }

  if (userMessage.includes('高变基因') || userMessage.includes('SVG')) {
    return `✅ 空间可变基因分析完成！

方法: Moran's I

Top 5 空间可变基因:
1. Mbp  (Moran's I: 0.82, p=0.001)
2. Plp1 (Moran's I: 0.78, p=0.001)
3. Mog  (Moran's I: 0.75, p=0.002)
4. Mag  (Moran's I: 0.72, p=0.003)
5. Mobp (Moran's I: 0.69, p=0.004)

共发现 245 个显著的空间可变基因。`
  }

  if (userMessage.includes('轨迹') || userMessage.includes('伪时间')) {
    return `✅ 空间轨迹推断完成！

分析方法: Pseudo-time (stlearn)
根节点: spot #1200
伪时间范围: [0.00, 1.00]
分支数: 3

分支 A: 450 spots (早期)
分支 B: 680 spots (中期)
分支 C: 520 spots (晚期)

请在右侧面板查看轨迹着色。`
  }

  if (userMessage.includes('通讯') || userMessage.includes('配体')) {
    return `✅ 细胞通讯分析完成！

方法: LIANA

Top 5 配体-受体对:
1. Lgals9 → Cd44 (score: 0.95)
2. Apoe → Lrp1 (score: 0.91)
3. Ccl5 → Ccr5 (score: 0.87)
4. Cxcl12 → Cxcr4 (score: 0.84)
5. Il16 → Cd4 (score: 0.82)

共发现 120 个显著互作对。`
  }

  return `收到您的指令："${userMessage}"

请尝试以下分析:
• 📊 数据质控 — "加载数据并进行质量控制"
• 🎯 空间高变基因 — "分析这个切片的空间高变基因"
• 🗺️ 区域查询 — "查询某个区域的基因表达"
• 🛤️ 空间轨迹 — "分析空间轨迹和伪时间"
• 📡 细胞通讯 — "分析配体-受体互作"`
}
