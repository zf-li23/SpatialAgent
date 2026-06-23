---
name: st_spatial_pattern
description: "使用 Moran's I 等方法识别空间可变基因 (SVG)，返回显著性排序列表"
license: MIT
metadata:
  version: "0.1.0"
  domain: spatial_transcriptomics
  tags: [svg, moran_i, spatial_pattern, spatial_autocorrelation]
  inputs:
    - name: data_path
      type: string
      format: path
      description: ".h5ad 文件路径"
      required: true
    - name: method
      type: string
      format: enum
      description: "SVG 方法 (morans_i, sepal)"
      required: false
    - name: n_top_genes
      type: integer
      format: int
      description: "返回 Top N 基因"
      required: false
  outputs:
    - name: svg_report
      type: object
      format: json
      description: "SVG 列表 + Moran's I 值"
  dependencies:
    python: ">=3.10"
    packages: [scanpy>=1.9, squidpy>=1.3, numpy>=1.24]
  demo_data:
    - path: "../../data/visium_lymph_node.h5ad"
  endpoints:
    cli: "python skills/st_spatial_pattern/run.py --data_path {data_path}"
    gateway: "POST /skills/st_spatial_pattern"
  openclaw:
    requires: {bins: [python3]}
    always: false
    emoji: "🎯"
    install: [{kind: pip, package: squidpy}]
    trigger_keywords: ["高变基因", "SVG", "空间模式", "空间可变", "spatial pattern", "moran"]
---

# 🎯 st_spatial_pattern — 空间可变基因分析

## 触发条件
- "分析空间高变基因"、"找 SVG"、"空间可变基因"
- "spatial variable genes"、"Moran's I"
- "哪些基因在空间上有模式"

## 工作流程
1. 读取 .h5ad 数据
2. 构建空间邻域图 (squidpy.gr.spatial_neighbors)
3. 计算 Moran's I (squidpy.gr.spatial_autocorr)
4. 按显著性排序，返回 Top N

## 输出示例
```json
{
  "top_svg_genes": [
    {"gene": "Mbp", "moran_i": 0.82, "p_value": 0.001},
    {"gene": "Plp1", "moran_i": 0.78, "p_value": 0.001}
  ],
  "n_significant_genes": 245,
  "method": "morans_i",
  "n_spots": 4035
}
```
