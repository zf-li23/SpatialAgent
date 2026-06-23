---
name: st_trajectory
description: "空间轨迹推断与伪时间分析，复用 stlearn 的 pseudotime 模块"
license: MIT
metadata:
  version: "0.1.0"
  domain: spatial_transcriptomics
  tags: [trajectory, pseudotime, paga, spatial_trajectory]
  inputs:
    - name: data_path
      type: string
      format: path
      required: true
    - name: root_index
      type: integer
      description: "手动指定根节点索引（可选）"
      required: false
  outputs:
    - name: trajectory_report
      type: object
      format: json
  dependencies:
    python: ">=3.10"
    packages: [scanpy>=1.9, stlearn>=1.4, numpy>=1.24]
  openclaw:
    requires: {bins: [python3]}
    always: false
    emoji: "🛤️"
    trigger_keywords: ["轨迹", "伪时间", "pseudotime", "trajectory", "PAGA"]
---

# 🛤️ st_trajectory — 空间轨迹推断

## 触发条件
- "分析空间轨迹"、"伪时间分析"
- "细胞分化轨迹"、"spatial trajectory"
- "PAGA"、"pseudotime"

## 工作流程
1. 读取数据 + 预处理
2. 构建空间邻域图 + PAGA 图
3. 使用 stlearn 或 scanpy 计算伪时间
4. 返回每个 spot 的伪时间和分支分配

## 参考
- stlearn.spatial.trajectory.pseudotimespace_global
- scanpy.tl.paga + scanpy.tl.dpt
