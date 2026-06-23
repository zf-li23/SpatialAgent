### 📚 仓库功能回顾与新发现归类

我把你克隆的 16 个仓库按在 BioAgent 中的作用分成了 4 层，让你心里有谱：

| 层级 | 对应仓库 | 核心价值（你的 BioAgent 该如何复用） |
| :--- | :--- | :--- |
| **🧠 大脑 & 网关层** | `openclaw`, `opencode`, `deepseek-v4-for-copilot` | **OpenClaw** 作为唯一执行网关（连接 IDE、前端和后端 API）；Copilot 插件仅用于 IDE 编码辅助，不与最终产品耦合。 |
| **🧬 空间组学专用“业务大脑”** | `SpatialAgent` (GeneTech), `qust` (QuST-LLM), `stLearn`, `omicverse` | **直接复制其核心脚本逻辑**，封装成 OpenClaw 可调用的 **Python Skills**，让 AI 能听懂“空间变异分析”、“区域选择”等指令。 |
| **🩺 生信通用技能库** | `ClawBio`, `OpenBioMed`, `OpenClaw-Medical-Skills`, `Biomni`, `bia`, `PantheonOS` | 提供现成的生物信息技能模板（如数据清洗、差异表达）。重点参考 `ClawBio` 的 `SKILL.md` 格式来规范你自己的技能描述。 |
| **🎨 前端 & 多智能体编排** | `CopilotKit`, `chat-copilot`, `AIAgents4Pharma`, `OpenBioLLM` | **CopilotKit** 是最佳前端 UI 方案（专为 React 设计）；`OpenBioLLM` 的“路由-查询-验证”架构适合改造为空间组学的多 Agent 工作流。 |

*(注：`CodeWhale` 偏向通用 AI 编程环境，暂不作为核心依赖)*

---

### 🏗️ BioAgent 项目架构设计（适配无计算资源环境）

由于你**没有独立计算资源**，后端直接调 DeepSeek API，我们的落地策略是：

> **前端（React + Vite）** 发送自然语言指令 → **OpenClaw 网关（本地进程）** 解析任务 → **动态调用 Python 脚本（复用 stLearn/omicverse 逻辑）** 进行轻量级 CPU 计算（非 GPU 训练）→ 返回 JSON 结果 → **前端可视化展示。**

#### 推荐的目录结构（直接在 `~/BioAgent` 下新建）

```
BioAgent/
├── frontend/                 # React + Vite + CopilotKit
│   ├── src/
│   │   ├── pages/            # 空间组学分析面板
│   │   └── components/       # 图表（Plotly）、3D 空间可视化
│   └── package.json
├── openclaw-gateway/         # 软链接到 ./repos/openclaw，或独立配置
│   ├── skills/               # 【核心】存放自定义空间组学技能
│   │   ├── st_analysis/      # 封装自 stLearn/omicverse
│   │   ├── spatial_region/   # 封装自 qust
│   │   └── metadata_mcp/     # 对接本地数据库文件
│   └── config.yaml           # 默认模型设为 DeepSeek API
└── data/                     # 存放示例空间组学测试数据（.h5ad / .csv）
```

---

### 🤖 给 GitHub Copilot 的“终极架构提示词”

以下是你需要**逐条复制粘贴到 VS Code Copilot Chat (或 Agent 模式)** 中的任务指令。**建议按顺序执行**，每个任务 Copilot 都能充分复用你 `repos/` 下的现有源码。

#### 📝 Prompt 1：初始化前端与核心依赖
> “我们正在构建一个名为 BioAgent 的空间组学 AI 辅助平台。请利用 **`CopilotKit`** 和 **React + Vite + TypeScript** 初始化前端项目。要求：
> 1. 参考 `./repos/CopilotKit/examples` 的结构，在主页面集成 CopilotKit 的聊天面板。
> 2. 创建 `SpatialDashboard` 组件，预留用于展示空间转录组切片（`plotly.js`）和基因表达热图的区域。
> 3. 配置 `package.json`，引入 `@copilotkit/react-core`、`axios`、`plotly.js-dist` 和 `ag-grid-react`（用于表格展示）。
> 4. 环境变量中预留 `VITE_OPENCLAW_API_URL`（指向本地网关，如 `http://localhost:3000`）。”

---

#### 📝 Prompt 2：构建 OpenClaw 网关与自定义空间技能
> “现在搭建 AI 网关层。我们在 `./openclaw-gateway/skills/` 下构建 **`spatial_omics`** 技能包。请完成以下代码复用：
> 1. 从 `./repos/ClawBio/skills/` 中复刻其 `SKILL.md` 的编写规范，创建 `st_preprocess` 技能，功能为“读取 10x Visium 数据并返回基本质控指标”。
> 2. 从 `./repos/stLearn/stlearn/` 中提取核心函数，封装为技能 `st_spatial_pattern`，调用 `stlearn.tl.spatial_pattern` 进行空间可变基因分析。
> 3. 从 `./repos/qust/` 中借鉴其 LLM 与 QuPath 交互的思路，但不依赖 GUI，改为纯函数：给定坐标和基因名，返回该区域平均表达量。
> 4. 确保所有技能最终输出均为 **JSON 格式**，以便前端 CopilotKit 直接解析渲染。”

---

#### 📝 Prompt 3：接入 DeepSeek API 并配置 Plan/Agent 双模式
> “配置 OpenClaw 的默认大模型为 DeepSeek：
> 1. 参考 `./repos/deepseek-v4-for-copilot` 中的认证逻辑，在 OpenClaw 的 `config.yaml` 中设置 `provider: deepseek`，并适配 OpenAI 兼容的 API 接口。
> 2. 借鉴 `./repos/OpenBioLLM` 的**多 Agent 分工思想**，在 OpenClaw 中定义两个 Agent 角色：
>    - `SpatialPlanner`：只读模式，负责拆解复杂分析任务。
>    - `SpatialExecutor`：执行模式，拥有调用上述自定义技能的权限。
> 3. 写一个 MCP 服务器配置，指向 `./repos/Biomni/biomni/environment` 中提取的数据库访问类，实现本地 `data/` 文件夹中 `.h5ad` 文件的自动加载。”

---

#### 📝 Prompt 4：前端与技能联动（核心界面交互）
> “实现前端与后端的完整联动：
> 1. 当用户在 CopilotKit 聊天框中输入“分析这个切片的空间高变基因”时，前端 `SpatialDashboard` 调用网关 `http://localhost:3000/skills/st_spatial_pattern`，并将返回的 JSON 数据利用 **Plotly** 在 2D 空间图上动态着色。
> 2. 参考 `./repos/SpatialAgent` 中人类参与式交互的设计，在聊天侧边栏加入“确认”按钮，允许用户在 AI 自动标注的 ROI（感兴趣区域）基础上进行点选修正。
> 3. 复制 `./repos/omicverse/omicverse/pl/` 下的绘图函数，用于生成美观的聚类 UMAP 图。”
*(小贴士：这里可以让 Copilot 写一个 `apiService.ts` 专门封装这些请求)*

---

#### 📝 Prompt 5：基于 Biomni 的“自适应规划”机制（加分项）
> “为了提升 Demo 的展示层次，请参考 `./repos/Biomni` 的论文实现思想，但不做全量复现。为 OpenClaw 增加一个 `AdaptivePlanner` 模块：
> 1. 写一个 Prompt 模板：**“根据用户的模糊请求（例如：帮我看看这个空间数据有什么问题），自动组合上述 3 个技能（预处理 -> QC -> 空间模式）形成分析流水线。”**
> 2. 前端展示规划的过程节点（如 Processing → QC → Analysis），使用 `react-flow` 或简单的列表展示，增强用户对 AI 工作流的信任感。”

---

### ⚠️ 关键实现提醒（避坑指南）

1. **无计算资源的“并行”策略**：Copilot 写 `stlearn` 调用时，务必让它 **使用 `scanpy` 的 `read_visium` 读入最小示例数据**（几百个细胞），**不要**启动大规模矩阵运算。将功能“演示出来”而非“完整跑通”，是课程作业的最优解。
2. **复用而非重写**：告诉 Copilot “重点利用 `./repos/...` 中的类和方法，仅编写粘合代码（Glue Code）”，这样 Copilot 会优先读你仓库里的源码生成导入逻辑，而不是自己凭空写算法。
3. **环境隔离**：由于涉及 Python 技能，建议在项目根目录写一个 `environment.yml`，并要求 Copilot 在生成的 Python 脚本头部自动加载 `sys.path.append("./repos/...")` 以解决模块引用问题。

### 🚀 启动步骤建议

1. 在 VS Code 中按 `Ctrl+Shift+P` 运行 “Copilot: Start Agent Mode”（如果你有 Copilot Agent 权限），或直接打开 Chat 面板，逐个喂入上述 5 条提示词。
2. 第一条提示词执行后，在 `frontend` 目录下 `npm install` 并 `npm run dev`，先看到前端页面。
3. 第二条提示词完成后，手动 `pip install scanpy stlearn`，并运行 OpenClaw 网关测试技能调用。

你克隆的代码仓库本身就是最好的“上下文文档”。目前这些 Copilot 提示词已经帮你把“**前端交互**”（React/CopilotKit）和“**领域逻辑**”（Python Skills）的边界划清了。