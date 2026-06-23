# SpatialAgent

> 面向空间组学数据分析的 AI 智能体平台 | 课程作业项目

## 概述

SpatialAgent 是一个空间组学 AI 辅助分析平台，允许用户通过自然语言对话驱动空间转录组数据的加载、质控、分析和可视化。项目采用"前端交互（React + CopilotKit）+ 网关调度（OpenClaw）+ Python 技能（复用 stLearn/omicverse）+ DeepSeek API"的四层架构。

## 架构

```
用户自然语言 → React 前端 (CopilotKit) → OpenClaw 网关 → Python 技能 → JSON 结果 → 前端可视化
                                                ↓
                                          DeepSeek API (LLM)
```

## 目录结构

```
SpatialAgent/
├── frontend/                 # React + Vite + CopilotKit 前端
├── openclaw-gateway/         # AI 网关与空间组学技能
├── data/                     # 示例空间组学数据
├── scripts/                  # 辅助脚本
├── docs/                     # 文档
├── repos/                    # 参考代码仓库（只读复用）
├── prompt.md                 # 项目提示词工程
└── plan.md                   # 详细实施计划
```

## 快速开始

```bash
# 环境准备
conda run -n zf-li23 pip install scanpy stlearn squidpy plotly pandas numpy

# 启动前端
cd frontend && npm install && npm run dev

# 启动网关
cd openclaw-gateway && python server.py
```

## 技术栈

| 层级 | 技术 |
|:---|:---|
| 前端 | React + Vite + TypeScript + CopilotKit |
| 可视化 | Plotly.js + ag-Grid |
| 网关 | OpenClaw / FastAPI + LangGraph |
| LLM | DeepSeek API (OpenAI 兼容) |
| 分析 | Python (scanpy + stlearn + squidpy + omicverse) |

## 许可

MIT
