import { useState, useEffect, useMemo } from 'react'
import Plot from 'react-plotly.js'
import type { PlanStep, SkillResult, DatasetInfo } from '../types/spatial'

interface Props { plan: PlanStep[]; results: SkillResult[]; activeDataset: DatasetInfo | null }
type Tab = 'spatial' | 'heatmap' | 'umap' | 'table'
const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: 'spatial', label: '空间图', icon: '🗺️' },
  { key: 'heatmap', label: '热图', icon: '🔥' },
  { key: 'umap', label: 'UMAP', icon: '🫧' },
  { key: 'table', label: '表格', icon: '📋' },
]

export default function SpatialDashboard({ plan, results, activeDataset }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('spatial')
  const [spatialData, setSpatialData] = useState<{ x: number[]; y: number[] } | null>(null)
  const [umapData, setUmapData] = useState<{ x: number[]; y: number[] } | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!activeDataset) { setSpatialData(null); setUmapData(null); return }
    setLoading(true)
    const base = import.meta.env.VITE_OPENCLAW_API_URL || 'http://localhost:3000'
    fetch(`${base}/datasets/${activeDataset.name}/preview`)
      .then(r => r.json()).then(d => {
        if (d.spatial) setSpatialData(d.spatial)
        if (d.umap) setUmapData(d.umap)
      }).catch(() => {}).finally(() => setLoading(false))
  }, [activeDataset?.name])

  const svgGenes = useMemo(() => {
    const r = results.find(x => x.skill === 'st_spatial_pattern' && x.success)
    return (r?.output as any)?.top_svg_genes || []
  }, [results])
  const cellCommPairs = useMemo(() => {
    const r = results.find(x => x.skill === 'st_cell_comm' && x.success)
    return (r?.output as any)?.top_interactions || []
  }, [results])

  const currentStep = plan.find(s => s.status === 'running')
  const completedSteps = plan.filter(s => s.status === 'completed').length

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b shrink-0" style={{ borderColor: 'var(--color-border)' }}>
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium">{activeDataset ? `📦 ${activeDataset.name}` : '未加载数据集'}</span>
          {activeDataset && <span className="text-xs" style={{ color: 'var(--color-muted)' }}>{activeDataset.n_spots.toLocaleString()} spots</span>}
        </div>
        {plan.length > 0 && <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--color-muted)' }}>
          <span>{completedSteps}/{plan.length} 完成</span>
          {currentStep && <span className="flex items-center gap-1" style={{ color: 'var(--color-accent)' }}>
            <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: 'var(--color-accent)' }} />{currentStep.purpose}
          </span>}
        </div>}
      </div>

      <div className="flex border-b shrink-0" style={{ borderColor: 'var(--color-border)' }}>
        {TABS.map(tab => (
          <button key={tab.key} className="flex items-center gap-1 px-3 py-2 text-xs font-medium transition-colors border-b-2"
            style={{ color: activeTab === tab.key ? 'var(--color-accent)' : 'var(--color-muted)', borderColor: activeTab === tab.key ? 'var(--color-accent)' : 'transparent' }}
            onClick={() => setActiveTab(tab.key)}><span>{tab.icon}</span><span>{tab.label}</span></button>
        ))}
        <div className="flex-1" />
        {loading && <span className="text-xs px-2 py-2 animate-pulse" style={{ color: 'var(--color-muted)' }}>加载中...</span>}
      </div>

      <div className="flex-1 overflow-hidden relative">
        {!activeDataset && <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ color: 'var(--color-muted)' }}>
          <span className="text-5xl mb-3">🧬</span><p className="text-sm">请先在左侧面板选择数据集</p></div>}

        {activeDataset && activeTab === 'spatial' && (spatialData ? (
          <Plot data={[{ x: spatialData.x, y: spatialData.y, mode: 'markers', type: 'scatter', marker: { size: 3, color: '#06b6d4', opacity: 0.6 } }]}
            layout={{ title: `CosMX 空间图 (${spatialData.x.length} cells 采样)`, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: '#e2e8f0' },
              xaxis: { title: 'X (px)', gridcolor: '#334155' }, yaxis: { title: 'Y (px)', gridcolor: '#334155' }, margin: { t: 40, r: 20, b: 40, l: 50 } }}
            useResizeHandler style={{ width: '100%', height: '100%' }} />
        ) : <div className="absolute inset-0 flex items-center justify-center text-sm" style={{ color: 'var(--color-muted)' }}>{loading ? '🔄 加载...' : '⚠️ 无空间坐标'}</div>)}

        {activeDataset && activeTab === 'umap' && (umapData ? (
          <Plot data={[{ x: umapData.x, y: umapData.y, mode: 'markers', type: 'scatter', marker: { size: 3, color: '#10b981', opacity: 0.6 } }]}
            layout={{ title: `UMAP (${umapData.x.length} cells)`, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: '#e2e8f0' },
              xaxis: { title: 'UMAP1', gridcolor: '#334155' }, yaxis: { title: 'UMAP2', gridcolor: '#334155' }, margin: { t: 40, r: 20, b: 40, l: 50 } }}
            useResizeHandler style={{ width: '100%', height: '100%' }} />
        ) : <div className="absolute inset-0 flex items-center justify-center text-sm" style={{ color: 'var(--color-muted)' }}>{loading ? '🔄 加载...' : '⚠️ 无 UMAP'}</div>)}

        {activeDataset && activeTab === 'heatmap' && (
          <Plot data={[{ z: Array.from({ length: 10 }, () => Array.from({ length: 15 }, () => Math.random() * 3)), type: 'heatmap', colorscale: 'RdBu', zmin: -2, zmax: 2 }]}
            layout={{ title: 'Top 高变基因 × 空间域（模拟）', paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: '#e2e8f0' },
              xaxis: { title: '空间域', tickvals: Array.from({ length: 15 }, (_, i) => i), ticktext: Array.from({ length: 15 }, (_, i) => `D${i + 1}`) },
              yaxis: { title: '基因', tickvals: Array.from({ length: 10 }, (_, i) => i), ticktext: svgGenes.length > 0 ? svgGenes.slice(0, 10).map(g => g.gene) : Array.from({ length: 10 }, (_, i) => `Gene${i + 1}`) },
              margin: { t: 40, r: 20, b: 50, l: 60 } }}
            useResizeHandler style={{ width: '100%', height: '100%' }} />
        )}

        {activeDataset && activeTab === 'table' && (
          <div className="overflow-auto h-full p-4">
            {svgGenes.length > 0 ? (
              <table className="w-full text-xs border-collapse">
                <thead><tr style={{ borderBottom: '2px solid var(--color-border)' }}>
                  <th className="text-left py-2 px-3" style={{ color: 'var(--color-accent)' }}>基因</th>
                  <th className="text-right py-2 px-3" style={{ color: 'var(--color-accent)' }}>Moran's I</th>
                  <th className="text-right py-2 px-3" style={{ color: 'var(--color-accent)' }}>p-value</th>
                  <th className="text-center py-2 px-3" style={{ color: 'var(--color-accent)' }}>显著</th>
                </tr></thead>
                <tbody>{svgGenes.map((row: any, i: number) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td className="py-1.5 px-3">{row.gene}</td>
                    <td className="text-right py-1.5 px-3">{row.moran_i?.toFixed(4)}</td>
                    <td className="text-right py-1.5 px-3">{row.p_value?.toFixed(6)}</td>
                    <td className="text-center py-1.5 px-3">{row.p_value < 0.05 ? '✅' : '❌'}</td>
                  </tr>))}</tbody>
              </table>
            ) : (
              <div className="text-center py-10" style={{ color: 'var(--color-muted)' }}>
                <p className="mb-2">📋 暂无分析结果</p>
                <p className="text-xs">在左侧输入分析指令，例如 "分析空间高变基因"</p>
                {cellCommPairs.length > 0 && <div className="mt-6 text-left max-w-md mx-auto">
                  <p className="text-sm font-medium mb-2" style={{ color: 'var(--color-accent)' }}>📡 细胞通讯</p>
                  {cellCommPairs.slice(0, 10).map((p: any, i: number) => (
                    <div key={i} className="text-xs py-1 flex justify-between" style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <span>{p.ligand} → {p.receptor}</span><span style={{ color: 'var(--color-accent)' }}>ρ={p.score}</span>
                    </div>
                  ))}
                </div>}
              </div>
            )}
          </div>
        )}
      </div>

      {plan.length > 0 && <div className="flex items-center gap-4 px-4 py-1.5 border-t text-xs shrink-0" style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}>
        {plan.map(step => <div key={step.step} className="flex items-center gap-1">
          <span>{step.status === 'completed' ? '✅' : step.status === 'running' ? '🔄' : '⏳'}</span><span>{step.purpose}</span>
        </div>)}
      </div>}
    </div>
  )
}
