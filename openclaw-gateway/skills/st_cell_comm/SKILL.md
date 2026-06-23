---
name: st_cell_comm
description: "基于空间邻域信息推断配体-受体互作（细胞通讯分析），复用 LIANA / omicverse Commot"
license: MIT
metadata:
  version: "0.1.0"
  domain: spatial_transcriptomics
  tags: [cell_communication, ligand_receptor, liana, ccc]
  inputs:
    - name: data_path
      type: string
      format: path
      required: true
    - name: method
      type: string
      format: enum
      description: "分析方法 (liana, correlation)"
      required: false
  outputs:
    - name: ccc_report
      type: object
      format: json
  dependencies:
    python: ">=3.10"
    packages: [scanpy>=1.9, numpy>=1.24, pandas>=2.0]
  openclaw:
    requires: {bins: [python3]}
    always: false
    emoji: "📡"
    trigger_keywords: ["细胞通讯", "配体", "受体", "通讯", "cell communication", "ccc", "liana"]
---

# 📡 st_cell_comm — 细胞通讯分析

## 触发条件
- "分析细胞通讯"、"配体-受体互作"
- "哪些细胞在交流"、"cell communication"
- "ligand-receptor"、"CCC"

## 工作流程
1. 读取数据 + 预处理
2. 使用 LIANA (如可用) 或基于共表达相关性的简化方法
3. 推断空间邻域内的配体-受体对
4. 返回显著性排序

## 参考
- omicverse.space.Commot 集成
- LIANA (ligand-receptor analysis framework)
