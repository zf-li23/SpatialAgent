// ============================================================
// SpatialAgent — 可视化面板
// ============================================================

import { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import type {
  PlanStep,
  SkillResult,
  DatasetInfo,
} from '../types/spatial'

interface Props {
  plan: PlanStep[]
  results: SkillResult[]
  activeDataset: DatasetInfo | null
}

type Tab = 'spatial' | 'heatmap' | 'umap' | 'table'

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: 'spatial', label: '空间图', icon: '🗺️' },
  { key: 'heatmap', label: '热图', icon: '🔥' },
  { key: 'umap', label: 'UMAP', icon: '🫧' },
  { key: 'table', label: '表格', icon: '📋' },
]

export default function SpatialDashboard({ plan, results, activeDataset }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('spatial')

  // 生成模拟空间散点
  const spatialScatter = useMemo(() => {
    const n = 200
    const xs: number[] = []
    const ys: number[] = []
    const colors: number[] = []
    for (let i = 0; i < n; i++) {
      xs.push(Math.random() * 100)
      ys.push(Math.random() * 100)
      colors.push(Math.random())
    }
    return { xs, ys, colors }
  }, [])

  // 生成模拟 UMAP 散点
  const umapScatter = useMemo(() => {
    const n = 200
    const xs: number[] = []
    const ys: number[] = []
    const clusters: number[] = []
    for (let i = 0; i < n; i++) {
      xs.push(Math.random() * 15)
      ys.push(Math.random() * 15)
      clusters.push(Math.floor(Math.random() * 6))
    }
    return { xs, ys, clusters }
  }, [])

  // 当前步骤
  const currentStep = plan.find((s) => s.status === 'running')
  const completedSteps = plan.filter((s) => s.status === 'completed').length

  return (
    <div className="flex flex-col h-full">
      {/* 顶部状态栏 */}
      <div
        className="flex items-center justify-between px-4 py-2 border-b shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium">
            {activeDataset ? `📦 ${activeDataset.name}` : '未加载数据集'}
          </span>
          {activeDataset && (
            <span className="text-xs" style={{ color: 'var(--color-muted)' }}>
              {activeDataset.n_spots.toLocaleString()} spots × {activeDataset.n_genes.toLocaleString()} genes
            </span>
          )}
        </div>

        {/* 执行进度 */}
        {plan.length > 0 && (
          <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--color-muted)' }}>
            <span>
              {completedSteps}/{plan.length} 步骤完成
            </span>
            {currentStep && (
              <span className="flex items-center gap-1" style={{ color: 'var(--color-accent)' }}>
                <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: 'var(--color-accent)' }} />
                {currentStep.purpose}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Tab 导航 */}
      <div className="flex border-b shrink-0" style={{ borderColor: 'var(--color-border)' }}>
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className="flex items-center gap-1 px-3 py-2 text-xs font-medium transition-colors border-b-2"
            style={{
              color: activeTab === tab.key ? 'var(--color-accent)' : 'var(--color-muted)',
              borderColor: activeTab === tab.key ? 'var(--color-accent)' : 'transparent',
            }}
            onClick={() => setActiveTab(tab.key)}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
        <div className="flex-1" />
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-hidden relative">
        {/* 无数据提示 */}
        {!activeDataset && (
          <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ color: 'var(--color-muted)' }}>
            <span className="text-5xl mb-3">🧬</span>
            <p className="text-sm">请先在左侧面板选择数据集</p>
            <p className="text-xs mt-1">然后在聊天框中输入分析指令</p>
          </div>
        )}

        {activeDataset && (
          <>
            {/* 空间散点图 */}
            {activeTab === 'spatial' && (
              <Plot
                data={[
                  {
                    x: spatialScatter.xs,
                    y: spatialScatter.ys,
                    mode: 'markers',
                    type: 'scatter',
                    marker: {
                      size: 5,
                      color: spatialScatter.colors,
                      colorscale: 'Viridis',
                      showscale: true,
                      colorbar: { title: '表达量' },
                    },
                    text: spatialScatter.xs.map((_, i) => `Spot ${i}`),
                    hoverinfo: 'text+x+y',
                  },
                ]}
                layout={{
                  title: '空间转录组切片 (2D)',
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#e2e8f0' },
                  xaxis: { title: 'X (μm)', gridcolor: '#334155' },
                  yaxis: { title: 'Y (μm)', gridcolor: '#334155' },
                  margin: { t: 40, r: 20, b: 40, l: 50 },
                  dragmode: 'select',
                }}
                useResizeHandler
                style={{ width: '100%', height: '100%' }}
              />
            )}

            {/* 热图 */}
            {activeTab === 'heatmap' && (
              <Plot
                data={[
                  {
                    z: Array.from({ length: 10 }, () =>
                      Array.from({ length: 15 }, () => Math.random() * 3)
                    ),
                    type: 'heatmap',
                    colorscale: 'RdBu',
                    zmin: -2,
                    zmax: 2,
                  },
                ]}
                layout={{
                  title: 'Top 10 高变基因 × 空间域',
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#e2e8f0' },
                  xaxis: {
                    title: '空间域',
                    tickvals: Array.from({ length: 15 }, (_, i) => i),
                    ticktext: Array.from({ length: 15 }, (_, i) => `D${i + 1}`),
                  },
                  yaxis: {
                    title: '基因',
                    tickvals: Array.from({ length: 10 }, (_, i) => i),
                    ticktext: ['Mbp', 'Plp1', 'Mog', 'Mag', 'Mobp', 'Cnp', 'Olig1', 'Olig2', 'Sox10', 'Nkx2-2'],
                  },
                  margin: { t: 40, r: 20, b: 50, l: 60 },
                }}
                useResizeHandler
                style={{ width: '100%', height: '100%' }}
              />
            )}

            {/* UMAP */}
            {activeTab === 'umap' && (
              <Plot
                data={Array.from({ length: 6 }, (_, cluster) => ({
                  x: umapScatter.xs.filter((_, i) => umapScatter.clusters[i] === cluster),
                  y: umapScatter.ys.filter((_, i) => umapScatter.clusters[i] === cluster),
                  mode: 'markers',
                  type: 'scatter',
                  name: `Cluster ${cluster}`,
                  marker: { size: 4 },
                }))}
                layout={{
                  title: '聚类 UMAP 可视化',
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#e2e8f0' },
                  xaxis: { title: 'UMAP1', gridcolor: '#334155' },
                  yaxis: { title: 'UMAP2', gridcolor: '#334155' },
                  margin: { t: 40, r: 20, b: 40, l: 50 },
                  legend: { font: { color: '#e2e8f0' } },
                }}
                useResizeHandler
                style={{ width: '100%', height: '100%' }}
              />
            )}

            {/* 表格 */}
            {activeTab === 'table' && (
              <div className="overflow-auto h-full p-4">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
                      <th className="text-left py-2 px-3" style={{ color: 'var(--color-accent)' }}>基因</th>
                      <th className="text-right py-2 px-3" style={{ color: 'var(--color-accent)' }}>Moran's I</th>
                      <th className="text-right py-2 px-3" style={{ color: 'var(--color-accent)' }}>p-value</th>
                      <th className="text-right py-2 px-3" style={{ color: 'var(--color-accent)' }}>显著</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { gene: 'Mbp', moran: 0.82, p: 0.001, sig: true },
                      { gene: 'Plp1', moran: 0.78, p: 0.001, sig: true },
                      { gene: 'Mog', moran: 0.75, p: 0.002, sig: true },
                      { gene: 'Mag', moran: 0.72, p: 0.003, sig: true },
                      { gene: 'Mobp', moran: 0.69, p: 0.004, sig: true },
                      { gene: 'Cnp', moran: 0.65, p: 0.008, sig: true },
                      { gene: 'Olig1', moran: 0.62, p: 0.012, sig: true },
                      { gene: 'Olig2', moran: 0.58, p: 0.025, sig: true },
                      { gene: 'Sox10', moran: 0.55, p: 0.038, sig: true },
                      { gene: 'Nkx2-2', moran: 0.51, p: 0.052, sig: false },
                    ].map((row, i) => (
                      <tr
                        key={i}
                        style={{ borderBottom: '1px solid var(--color-border)' }}
                        className="hover:bg-opacity-50"
                      >
                        <td className="py-1.5 px-3">{row.gene}</td>
                        <td className="text-right py-1.5 px-3">{row.moran.toFixed(3)}</td>
                        <td className="text-right py-1.5 px-3">{row.p.toFixed(4)}</td>
                        <td className="text-right py-1.5 px-3">
                          {row.sig ? '✅' : '❌'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      {/* 底部状态 */}
      {plan.length > 0 && (
        <div
          className="flex items-center gap-4 px-4 py-1.5 border-t text-xs shrink-0"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
        >
          {plan.map((step) => (
            <div key={step.step} className="flex items-center gap-1">
              <span>
                {step.status === 'completed' ? '✅' : step.status === 'running' ? '🔄' : '⏳'}
              </span>
              <span>{step.purpose}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
