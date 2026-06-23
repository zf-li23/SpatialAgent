// ============================================================
// SpatialAgent — 聊天面板
// ============================================================

import { useState, useRef, useEffect, useCallback } from 'react'
import type {
  PlanStep,
  SkillResult,
  DatasetInfo,
} from '../types/spatial'
import * as api from '../services/apiService'

interface ChatPanelProps {
  onResponse: (response: {
    plan?: PlanStep[]
    results?: SkillResult[]
  }) => void
  activeDataset: DatasetInfo | null
  onDatasetChange: (dataset: DatasetInfo | null) => void
  plan: PlanStep[]
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
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [datasets, setDatasets] = useState<DatasetInfo[]>([])
  const [gatewayStatus, setGatewayStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 初始化
  useEffect(() => {
    api.healthCheck()
      .then((r) => setGatewayStatus(r.status === 'ok' ? 'online' : 'offline'))
      .catch(() => setGatewayStatus('offline'))
    api.listDatasets().then(setDatasets).catch(() => {})
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

    try {
      const response = await api.sendChat({
        message: text,
        data_path: activeDataset?.path,
      })

      if (response.plan && response.plan.length > 0) {
        // 模拟逐步执行动画
        for (let i = 0; i < response.plan.length; i++) {
          const updatedPlan = response.plan.map((s, idx) => ({
            ...s,
            status: (idx < i ? 'completed' : idx === i ? 'running' : 'pending') as PlanStep['status'],
          }))
          onResponse({ plan: updatedPlan })
          await new Promise((r) => setTimeout(r, 800))
        }
      }

      const results = response.results || []
      const finalPlan = (response.plan || []).map((s) => ({ ...s, status: 'completed' as const }))
      onResponse({ plan: finalPlan, results })

      const reply = formatResultsAsText(text, results, response.explanation)
      addMessage('assistant', reply, response.plan, results)

    } catch {
      addMessage('system', `⚠️ 网关未连接\n\n${generateFallbackResponse(text)}`)
    } finally {
      setLoading(false)
    }
  }, [input, loading, addMessage, onResponse, activeDataset])

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

// ============================================================
// 结果格式化
// ============================================================

function formatResultsAsText(userMessage: string, results: SkillResult[], explanation: string): string {
  if (!results || results.length === 0) return generateFallbackResponse(userMessage)

  let text = `✅ ${explanation || '分析完成！'}\n\n`
  for (const r of results) {
    if (!r.success) { text += `❌ ${r.skill}: ${r.error || '失败'}\n`; continue }
    const out = r.output || {} as any
    switch (r.skill) {
      case 'st_preprocess':
        text += `📊 数据质控: ${out.n_spots?.toLocaleString()} spots, ${out.n_genes?.toLocaleString()} genes\n`
        text += `  中位基因/spot: ${out.median_genes_per_spot}, 线粒体: ${out.pct_mito?.toFixed(1)}%\n`; break
      case 'st_spatial_pattern':
        const svgs = out.top_svg_genes || []; text += `🎯 SVG (${out.method}): ${out.n_significant_genes} 个\n`
        svgs.slice(0, 5).forEach((g: any, i: number) => { text += `  ${i + 1}. ${g.gene} (I=${g.moran_i})\n` }); break
      case 'st_region_query':
        text += `🗺️ 区域 (${out.n_spots_in_region} spots):\n`
        Object.entries(out.gene_expression || {}).slice(0, 5).forEach(([g, v]: any) => { text += `  ${g}: ${v.mean}\n` }); break
      case 'st_trajectory':
        text += `🛤️ 伪时间 [${out.pseudotime_range?.[0]?.toFixed(2)}, ${out.pseudotime_range?.[1]?.toFixed(2)}], ${out.n_branches} 分支\n`; break
      case 'st_cell_comm':
        const pairs = out.top_interactions || []; text += `📡 细胞通讯: ${out.n_significant_pairs} 显著对\n`
        pairs.slice(0, 3).forEach((p: any) => { text += `  ${p.ligand}→${p.receptor} (ρ=${p.score})\n` }); break
    }
    text += '\n'
  }
  return text
}

function generateFallbackResponse(userMessage: string): string {
  for (const [kw, hint] of Object.entries({ '质控': '请先选择数据集并输入"加载数据并进行质量控制"', '高变': '请输入"分析空间高变基因"', '轨迹': '请输入"分析空间轨迹和伪时间"', '通讯': '请输入"分析配体-受体互作"' })) {
    if (userMessage.includes(kw)) return hint
  }
  return `收到: "${userMessage}"。请启动网关 (cd openclaw-gateway && python server.py) 后重试。`
}
