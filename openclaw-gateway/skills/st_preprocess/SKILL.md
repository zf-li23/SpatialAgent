---
name: st_preprocess
description: "读取 10x Visium 空间转录组数据，执行基本质控并返回 QC 指标"
license: MIT
metadata:
  version: "0.1.0"
  domain: spatial_transcriptomics
  tags: [preprocessing, qc, visium, 10x]
  inputs:
    - name: data_path
      type: string
      format: path
      description: ".h5ad 文件路径"
      required: true
  outputs:
    - name: qc_report
      type: object
      format: json
      description: "QC 指标 JSON"
  dependencies:
    python: ">=3.10"
    packages: [scanpy>=1.9, pandas>=2.0, numpy>=1.24]
  demo_data:
    - path: "../../data/visium_lymph_node.h5ad"
      description: "模拟 Human Lymph Node Visium 数据"
  endpoints:
    cli: "python skills/st_preprocess/run.py --data_path {data_path}"
    gateway: "POST /skills/st_preprocess"
  openclaw:
    requires: {bins: [python3]}
    always: false
    emoji: "🔬"
    install: [{kind: pip, package: scanpy}]
    trigger_keywords: ["加载数据", "质控", "QC", "预处理", "读入", "load data", "preprocess"]
---

# 🔬 st_preprocess — 空间数据加载与质控

## 触发条件
当用户说以下任何内容时触发此技能：
- "加载数据"、"读入数据"、"打开数据"
- "做个质控"、"QC一下"、"看看数据质量"
- "预处理"、"数据预处理"
- "load data"、"preprocess"、"quality control"

## 工作流程
1. 使用 `scanpy.read_h5ad` 读取 .h5ad 文件
2. 提取空间坐标（`adata.obsm['spatial']`）
3. 计算 QC 指标：基因数、UMI数、线粒体比例、核糖体比例
4. 返回 JSON 格式的 QC 报告

## 输出示例
```json
{
  "n_spots": 4035,
  "n_genes": 36601,
  "median_genes_per_spot": 1800,
  "median_umi_per_spot": 4500,
  "pct_mito": 5.2,
  "pct_ribo": 12.8,
  "spatial_coords_shape": [4035, 2]
}
```
