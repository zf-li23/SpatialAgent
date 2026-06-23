---
name: st_region_query
description: "根据空间坐标范围和基因名列表，查询该区域的平均表达量（参考 qust 的 LLM-空间交互思路）"
license: MIT
metadata:
  version: "0.1.0"
  domain: spatial_transcriptomics
  tags: [region_query, expression, spatial_selection]
  inputs:
    - name: data_path
      type: string
      format: path
      required: true
    - name: x_min
      type: float
      required: true
    - name: x_max
      type: float
      required: true
    - name: y_min
      type: float
      required: true
    - name: y_max
      type: float
      required: true
    - name: gene_list
      type: string
      format: "comma-separated"
      required: false
  outputs:
    - name: region_report
      type: object
      format: json
  dependencies:
    python: ">=3.10"
    packages: [scanpy>=1.9, numpy>=1.24, pandas>=2.0]
  openclaw:
    requires: {bins: [python3]}
    always: false
    emoji: "🗺️"
    trigger_keywords: ["区域查询", "表达量", "坐标", "region", "查询"]
---

# 🗺️ st_region_query — 空间区域表达量查询

## 触发条件
- "查询某个区域的基因表达"、"这个区域表达了什么"
- "坐标 (x,y) 附近的基因表达"
- "region query"、"expression at location"

## 工作流程
1. 读取 .h5ad 数据
2. 根据空间坐标范围 (x_min, x_max, y_min, y_max) 筛选 spots
3. 计算区域内指定基因的平均表达量
4. 返回 JSON 结果

## 参考
- qust 的 LLM + QuPath 交互思路：将自然语言坐标查询映射到空间数据切片
