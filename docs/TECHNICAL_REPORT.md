# SpatialAgent — 空间组学 AI 辅助分析平台 技术报告

> **课程作业项目**
> 
> GitHub: https://github.com/zf-li23/SpatialAgent
>
> 技术栈: React + Vite + TypeScript (前端) / FastAPI + Python (后端) / DeepSeek API (LLM)

---

## 1. 项目概述

### 1.1 项目定位

SpatialAgent 是一个面向**空间转录组学数据分析**的 AI 智能体平台。用户通过自然语言对话驱动完整分析流程：数据加载、质量控制、空间可变基因识别、区域表达查询、空间轨迹推断和细胞通讯分析。

### 1.2 核心策略

- **复用而非重写**：所有分析逻辑从现有生物信息学仓库（stLearn、squidpy、scanpy、omicverse）直接导入
- **粘合代码为主**：本项目新增代码主要是 API 封装、SKILL.md 定义、前端组件
- **JSON 贯穿始终**：所有技能输出均为 JSON，前端直接解析渲染
- **LLM + 规则双模式**：有 DeepSeek API Key 时用 LLM 智能规划，无 Key 时自动回退规则匹配

### 1.3 无计算资源策略

由于没有独立 GPU 计算资源，后端直接调用 DeepSeek API，分析脚本运行在 CPU 上（使用 scanpy 最小示例数据 ~50-5000 cells），不启动大规模矩阵运算。功能"演示出来"而非"完整跑通"是课程作业的最优解。

---

## 2. 系统架构

### 2.1 四层架构

```
┌─────────────────────────────────────────────────────────────┐
│  🎨 用户交互层                                              │
│  React + Vite + TypeScript + CopilotKit                     │
│  ┌─────────────┐  ┌──────────────────────────────────────┐  │
│  │ ChatPanel   │  │ SpatialDashboard                      │  │
│  │ - 聊天面板  │  │ - 空间图 (Plotly 2D scatter)          │  │
│  │ - 快捷指令  │  │ - UMAP (真实降维)                      │  │
│  │ - Pipeline  │  │ - 热图                                 │  │
│  │   可视化    │  │ - SVG 表格 (ag-Grid)                   │  │
│  └──────┬──────┘  └──────────────────────────────────────┘  │
│         │ HTTP/SSE (localhost:3000)                         │
├─────────┼───────────────────────────────────────────────────┤
│  🧠 网关层                                                  │
│  ┌──────┴──────────────────────────────────────────────┐   │
│  │  FastAPI Gateway (openclaw-gateway/server.py)       │   │
│  │  POST /chat     → 标准聊天 (Planner+Executor)       │   │
│  │  POST /adaptive → 自适应流水线 (模糊请求)            │   │
│  │  POST /plan     → 仅规划不执行                      │   │
│  │  POST /skills/* → 直接执行单个技能                   │   │
│  │  GET  /datasets → 数据集列表                        │   │
│  │  GET  /datasets/{name}/preview → 空间坐标+UMAP      │   │
│  │  GET  /health   → 健康检查                          │   │
│  └────────────────────────────────────────────────────┘   │
│         │                                                  │
│  ┌──────┴──────────────────────────────────────────────┐   │
│  │  双 Agent 编排 (AgentOrchestrator)                   │   │
│  │                                                      │   │
│  │  SpatialPlanner  ──→  SpatialExecutor  ──→ Evaluator │   │
│  │  (只读·拆解任务)       (执行技能)        (质量门控)  │   │
│  │       ↑                                ↓             │   │
│  │       └────────── 重试 (最多 2 次) ──────────┘       │   │
│  │                                                      │   │
│  │  AdaptivePlanner (模糊请求 → 自动构建流水线)          │   │
│  └────────────────────────────────────────────────────┘   │
│         │                                                  │
├─────────┼───────────────────────────────────────────────────┤
│  🧬 技能层 (Python Skills)                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───┐│
│  │st_preproc│ │spatial   │ │region    │ │trajectory│ │cel││
│  │  ess     │ │ pattern  │ │ query    │ │          │ │l_c││
│  │  QC      │ │ Moran's I│ │ 区域表达 │ │ DPT/PAGA │ │omm││
│  │ scanpy   │ │ squidpy  │ │ annData  │ │ scanpy   │ │LR ││
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └─┬─┘│
│       └────────────┴────────────┴────────────┴─────────┘   │
│                      conda run -n zf-li23                   │
├─────────────────────────────────────────────────────────────┤
│  🤖 LLM 层                                                  │
│  DeepSeek API (OpenAI 兼容) · https://api.deepseek.com/v1  │
│  模型: deepseek-chat · 回退: 规则匹配 (无需 API Key)        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户输入 "分析空间高变基因"
  │
  ▼
ChatPanel (React)
  │ POST /chat {message, data_path}
  ▼
FastAPI Gateway
  │
  ├─ SpatialPlanner (LLM 规划)
  │   ├─ 有 API Key → DeepSeek 智能规划
  │   └─ 无 API Key → 规则匹配回退
  │   └─ 输出: {"plan": [...], "explanation": "..."}
  │
  ├─ SpatialExecutor (顺序执行)
  │   ├─ Step 1: st_preprocess
  │   │   └─ conda run python run.py --data_path ...
  │   │   └─ JSON: {n_spots, n_genes, median_genes, ...}
  │   ├─ Step 2: st_spatial_pattern
  │   │   └─ conda run python run.py --data_path ...
  │   │   └─ JSON: {top_svg_genes: [...], ...}
  │   └─ Step 3-N: ...
  │
  ├─ Evaluator (质量门控)
  │   ├─ passed → 返回前端
  │   └─ failed → 重试 (最多 2 次)
  │
  └─ 返回 JSON: {plan, results, evaluation, explanation}
      │
      ▼
ChatPanel 显示文本结果
SpatialDashboard 实时更新可视化
  ├─ 空间图: 5000 cells 真实坐标 (from metadata)
  ├─ UMAP: scanpy 计算的真实降维
  ├─ 热图: SVG 基因 × 空间域
  └─ 表格: Moran's I 排序列表
```

---

## 3. 组件详细设计

### 3.1 前端 (React + Vite + TypeScript)

#### 3.1.1 文件结构

```
frontend/src/
├── main.tsx                             # 入口 (BrowserRouter)
├── App.tsx                              # 路由配置
├── index.css                            # Tailwind + 深色主题
├── types/spatial.ts                     # 9 个 TypeScript 接口定义
├── services/apiService.ts               # 6 个 API 封装函数
├── pages/MainLayout.tsx                 # 左右分栏布局
└── components/
    ├── ChatPanel.tsx                    # 聊天面板
    │   ├── 网关状态检测 (health check)
    │   ├── 数据集选择 (dropdown)
    │   ├── 5 个快捷指令按钮
    │   ├── 消息列表 (渐进式动画)
    │   ├── 模糊请求自动路由 /adaptive
    │   └── PipelineVisualizer 集成
    ├── SpatialDashboard.tsx             # 可视化面板
    │   ├── 4 Tab (空间图/热图/UMAP/表格)
    │   ├── 选择数据集时自动加载真实坐标
    │   └── 分析完成后展示真实结果
    └── PipelineVisualizer.tsx           # 流水线可视化
        ├── 4 种节点颜色 (PROC/QC/ANALY/VIS)
        ├── 箭头连线 + 状态动画
        └── 进度条
```

#### 3.1.2 核心依赖

| 包名 | 用途 |
|:---|:---|
| `@copilotkit/react-core` | CopilotKit 聊天框架 |
| `@copilotkit/react-ui` | 聊天 UI 组件 |
| `react-plotly.js` + `plotly.js-dist` | 空间图、热图、UMAP 渲染 |
| `ag-grid-react` + `ag-grid-community` | 分析结果表格 |
| `axios` | HTTP 请求 |
| `tailwindcss` | 样式框架 |
| `react-router-dom` | 路由 |

#### 3.1.3 类型定义 (`types/spatial.ts`)

定义了 9 个核心接口：`ChatRequest`, `ChatResponse`, `PlanStep`, `SkillResult`, `DatasetInfo`, `QCResult`, `SVGGene`, `SpatialPatternResult`, `RegionQueryResult`, `TrajectoryResult`, `CellCommResult`, `PipelineDefinition`。

### 3.2 网关 (FastAPI + Python)

#### 3.2.1 文件结构

```
openclaw-gateway/
├── config.yaml                          # 网关配置
├── server.py                            # FastAPI 主服务器 (v0.2)
├── llm_client.py                        # DeepSeek LLM 工厂
├── agents/
│   ├── __init__.py
│   ├── spatial_planner.py               # SpatialPlanner Agent
│   ├── spatial_executor.py              # SpatialExecutor Agent
│   └── orchestrator.py                  # 双 Agent 编排器
├── planner/
│   └── adaptive_planner.py              # 自适应规划模块
└── skills/
    ├── st_preprocess/                   # 数据加载与质控
    │   ├── SKILL.md                     # YAML front matter
    │   └── run.py                       # scanpy 实现
    ├── st_spatial_pattern/              # 空间可变基因
    │   ├── SKILL.md
    │   └── run.py                       # squidpy Moran's I
    ├── st_region_query/                 # 区域表达查询
    │   ├── SKILL.md
    │   └── run.py                       # 坐标自动缩放
    ├── st_trajectory/                   # 空间轨迹
    │   ├── SKILL.md
    │   └── run.py                       # scanpy DPT+PAGA
    ├── st_cell_comm/                    # 细胞通讯
    │   ├── SKILL.md
    │   └── run.py                       # Spearman 相关性
    └── metadata_mcp/
        └── server.py                    # 数据目录扫描
```

#### 3.2.2 API 端点

| 端点 | 方法 | 功能 | 输入 | 输出 |
|:---|:---|:---|:---|:---|
| `/health` | GET | 健康检查 | — | `{status, version, skills}` |
| `/skills` | GET | 技能列表 | — | `[{name, description, triggers}]` |
| `/datasets` | GET | 数据集列表 | — | `[{name, path, n_spots, n_genes}]` |
| `/datasets/{name}/preview` | GET | 数据预览 | 名称 | `{spatial, umap, stats}` |
| `/chat` | POST | 完整聊天 | `{message, data_path}` | `{plan, results, evaluation}` |
| `/adaptive` | POST | 自适应规划 | `{message, data_path}` | `{pipeline, results}` |
| `/plan` | POST | 仅规划 | `{message, data_path}` | `{plan, explanation}` |
| `/skills/{name}` | POST | 执行技能 | `{data_path, args}` | `{skill, success, output}` |

#### 3.2.3 LLM 客户端 (`llm_client.py`)

**多层 API Key 回退策略**（参考 deepseek-v4-for-copilot 的 AuthManager）：

```python
self.api_key = (
    api_key                    # 构造函数传入
    or os.environ.get("DEEPSEEK_API_KEY")  # 环境变量
    or os.environ.get("OPENAI_API_KEY")    # 备用
    or ""
)
```

**容错机制**：
- 无 Key → 自动回退规则匹配
- LLM 调用失败 → 自动回退规则匹配
- JSON 解析失败 → 正则提取 JSON 块
- 超时保护 → `OpenAI(timeout=120.0)`

#### 3.2.4 智能规划 (`spatial_planner.py`)

**LLM 模式**（需 API Key）：
- 向 DeepSeek 发送完整系统提示词（含可用技能清单）
- 使用 `response_format: json_object` 强制 JSON 输出
- 解析返回的结构化执行计划

**规则模式**（无 API Key）：
- 关键词匹配：`高变基因` → `st_spatial_pattern`
- 复合请求：多条关键词 → 多步骤计划
- 默认：`st_preprocess` + `st_spatial_pattern`

#### 3.2.5 双 Agent 编排 (`orchestrator.py`)

```
用户输入 → SpatialPlanner(规划) → SpatialExecutor(执行) → Evaluator(评估)
                                            ↑                    |
                                            └── 重试 (最多2次) ──┘
```

- **SpatialPlanner**：只读模式，负责分析用户意图并拆解为子任务序列
- **SpatialExecutor**：执行模式，顺序调用 Python 技能，上下文自动传递
- **Evaluator**：检查结果是否满足用户请求，不满足则生成重试计划

#### 3.2.6 自适应规划 (`adaptive_planner.py`)

参考 Biomni 的 A1 智能体 env_desc 感知思想，根据用户模糊请求自动组合技能形成分析流水线。

**规则匹配逻辑**：

| 关键词 | 触发技能 |
|:---|:---|
| `看看`, `有什么`, `怎么样`, `分析一下`, `帮我`, `检查`, `查看`, `问题`, `异常` | st_preprocess + st_spatial_pattern |
| `高变`, `SVG`, `空间模式`, `差异`, `标记` | st_spatial_pattern |
| `区域`, `坐标`, `位置`, `局部` | st_region_query |
| `轨迹`, `伪时间`, `分化`, `PAGA` | st_trajectory |
| `通讯`, `配体`, `受体`, `互作`, `信号`, `CCC` | st_cell_comm |

### 3.3 Python 技能 (Skills)

所有技能遵循 ClawBio 的 SKILL.md 规范（YAML front matter + Markdown 正文）。

#### 技能 1: `st_preprocess`

- **功能**：读取 .h5ad 文件，执行基本质控
- **复用**：`scanpy.read_h5ad`, `sc.pp.calculate_qc_metrics`
- **输出**：
  ```json
  {
    "n_spots": 43117,
    "n_genes": 960,
    "median_genes_per_spot": 352.0,
    "median_umi_per_spot": 962.0,
    "pct_mito": 0.0,
    "min_genes_per_spot": 1,
    "max_genes_per_spot": 802,
    "spatial_coords_shape": [43117, 2]
  }
  ```

#### 技能 2: `st_spatial_pattern`

- **功能**：识别空间可变基因 (SVG)
- **复用**：`squidpy.gr.spatial_neighbors`, `squidpy.gr.spatial_autocorr`
- **优化**：先筛选 500 个高变基因再计算 Moran's I（否则 960 基因的排列检验太慢）
- **输出**：Top N 基因列表 + Moran's I + p-value

#### 技能 3: `st_region_query`

- **功能**：给定坐标范围查询区域基因表达
- **参考**：qust (QuST-LLM) 的 LLM-空间交互思路，去除 GUI 依赖
- **特性**：坐标范围自动缩放（检测数据实际范围）
- **输出**：区域 spots 数 + 基因平均表达量

#### 技能 4: `st_trajectory`

- **功能**：空间轨迹推断与伪时间分析
- **复用**：`scanpy.tl.paga`, `scanpy.tl.dpt`
- **输出**：伪时间范围 + 分支分布 + 采样点列表

#### 技能 5: `st_cell_comm`

- **功能**：配体-受体互作分析
- **算法**：
  1. 尝试 LIANA（如安装）
  2. 回退到已知 LR 配对库的 Spearman 相关性
  3. 再回退到 Top 100 HVG 全对全相关性
- **LR 配对库**：25 对已知配体-受体（LGALS9-CD44, APOE-LRP1, CCL5-CCR5 等）
- **输出**：显著互作对列表

---

## 4. 数据

### 4.1 测试数据集

| 属性 | 值 |
|:---|:---|
| **来源** | GSE263791 — NanoString CosMX |
| **样本** | ID61-ID62 (S10) + ID67-ID68 (S18) |
| **技术** | CosMX (NanoString)，靶向基因面板 |
| **细胞** | 43,117 (21,713 + 21,404) |
| **基因** | 500 HVG (从 960 靶向基因筛选) |
| **空间坐标** | 真实细胞质心坐标 (metadata 中 CenterX/Y_global_px) |
| **预计算** | PCA (30 components) + UMAP + Leiden (15 clusters) |
| **大小** | 105 MB |

### 4.2 数据组成分析

| 原始 tar 内容 | 大小 | 必要性 |
|:---|:---:|:---|
| `tx_file.csv.gz` (×2) — 7817万条单转录本坐标 | 1.26 GB | ❌ 已聚合到计数矩阵 |
| `CellOverlay/CellComposite` (×2) — 组织图像 | ~640 MB | ❌ 可视化用，非分析必需 |
| 表达矩阵 + 元数据 | ~15 MB | ✅ 分析核心 |
| 其他 (标签图、隔室、多边形) | ~100 MB | ❌ 非必需 |

### 4.3 可复现性

```bash
wget -O GSE263791_RAW.tar "https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE263791&format=file"
mkdir -p GSE263791 && tar -xf GSE263791_RAW.tar -C GSE263791
cd GSE263791 && python build_anndata.py
```

---

## 5. 分析流程验证

### 5.1 端到端测试结果

| 测试项 | 结果 |
|:---|:---|
| `GET /health` | `{"status":"ok","version":"0.2.0","skills":5}` ✅ |
| `GET /skills` | 5 个技能含 trigger_keywords ✅ |
| `GET /datasets` | cosmx_combined.h5ad (43117 spots) ✅ |
| `GET /datasets/{name}/preview` | 5000 cells 空间坐标 + UMAP ✅ |
| `POST /chat "分析空间高变基因"` | 2 步计划 → 2/2 成功 → 评估通过 ✅ |
| `POST /adaptive "帮我看看数据"` | 自适应流水线 → 执行成功 ✅ |
| `POST /plan "分析细胞通讯"` | preprocess + cell_comm ✅ |

### 5.2 CosMX 真实数据分析结果

| 分析 | 关键发现 |
|:---|:---|
| **QC** | 43,117 cells, 500-960 genes, 中位 352 genes/cell, 962 UMI/cell |
| **SVG** | Penk (I=0.030), Foxj1 (I=0.014), Adora2a (I=0.012) 等 |
| **通讯** | Tgfb1→Tgfbr1 (ρ=0.29), Bdnf→Ntrk2 (ρ=0.11), Vegfa→Kdr (ρ=0.11) |
| **UMAP** | 15 Leiden 聚类，PCA+UMAP 降维 |

### 5.3 LLM 规划测试

| 用户输入 | LLM 规划输出 |
|:---|:---|
| "帮我分析这个 CosMX 空间转录组数据的空间高变基因和细胞通讯" | 1. st_preprocess (加载数据质控) → 2. st_spatial_pattern (识别SVG) → 3. st_cell_comm (细胞通讯分析) |
| "帮我看看这个数据有什么问题" | 1. st_preprocess → 2. st_spatial_pattern (自适应默认) |
| "分析细胞通讯" | 1. st_preprocess → 2. st_cell_comm |

---

## 6. 参考代码仓库复用

| 仓库 | 复用内容 | 用途 |
|:---|:---|:---|
| `ClawBio` | `templates/SKILL-TEMPLATE.md` | 5 个技能的 SKILL.md 编写规范 |
| `stLearn` | `stlearn/spatial/`, `stlearn/tl/` | 空间轨迹、空间模式函数参考 |
| `squidpy` (通过 pip) | `gr.spatial_neighbors`, `gr.spatial_autocorr` | Moran's I SVG 分析 |
| `omicverse` | `omicverse/pl/`, `omicverse/space/` | 绘图函数、空间工具参考 |
| `Biomni` | `biomni/llm.py`, `biomni/tool/tool_registry.py` | 多提供商 LLM 工厂、工具注册模式 |
| `SpatialAgent (GeneTech)` | `spatialagent/agent/spatialagent.py` | LangGraph Agent 模式、Hooks 系统参考 |
| `OpenBioLLM` | `openbiollm/src/core/router.py`, `rag.py` | Router→Agent→Evaluator 路由循环 |
| `deepseek-v4-for-copilot` | `src/auth.ts` | API Key 多层回退认证逻辑 |
| `qust` | `qust_scripts/llm.py` | LLM-空间交互思路（区域查询） |
| `CopilotKit` | `packages/react-core/src/hooks/` | 前端聊天框架 Hooks |

---

## 7. 环境与依赖

### 7.1 Python 环境

```bash
conda env: zf-li23
Python: 3.13
核心包: scanpy 1.12, stlearn 1.4, squidpy 1.8, plotly 6.8
网关: fastapi, uvicorn, pydantic, openai
```

### 7.2 Node.js 环境

```bash
Node.js: 24.15
npm: 11.12
Vite: 6.4
React: 19
```

### 7.3 配置

```bash
# API Key (可选，无 Key 时回退规则匹配)
export DEEPSEEK_API_KEY="sk-..."

# 启动
cd openclaw-gateway && python server.py    # 网关 :3000
cd frontend && npm run dev                 # 前端 :5173
```

---

## 8. 代码审查与修复记录

阶段 6 对全部 10 个源文件进行了全面代码审查，共修复 18 个问题：

| 严重度 | 修复 |
|:---|:---|
| 🔴 Critical | `SpatialDashboard` 未定义变量引用 (`spatialScatter` → `spatialTrace`)、`AdaptivePlanner` 用户输入含 `{` 时 `.format()` 崩溃、`ChatPanel` 参数数量不匹配、`Orchestrator` 无效类型 `callable` |
| 🟡 Medium | `SkillResult` 缺少 `success` 字段、`listSkills` 返回类型错误、`apiService` 无 `adaptivePipeline` 函数、`/adaptive` 端点无错误处理、死代码 `EXECUTOR_SYSTEM_PROMPT` (16行) |
| 🟢 Minor | `discover_datasets` 每文件重复 import、`LLMClient` 无超时 |

---

## 9. 项目统计

| 指标 | 数值 |
|:---|:---|
| Python 源文件 | 10 |
| TypeScript/React 源文件 | 7 |
| CSS | 1 |
| YAML/配置 | 4 |
| SKILL.md (技能定义) | 5 |
| API 端点 | 8 |
| 可执行技能 | 5 |
| 参考仓库 | 10 |
| 测试数据集大小 | 105 MB (h5ad) / 2.0 GB (tar) |
| 代码行数 (估算) | ~3,000 |
