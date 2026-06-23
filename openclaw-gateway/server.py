# ============================================================
# SpatialAgent — FastAPI 网关服务器
# 简化版 OpenClaw 网关，桥接前端与 Python 技能
# ============================================================

import sys
import os
import json
import subprocess
import time
import uuid
import glob
from pathlib import Path
from typing import Optional

# 确保能引用 repos 下的代码
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "repos")
sys.path.insert(0, REPO_ROOT)

# --- FastAPI 依赖检查 ---
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("请先安装: pip install fastapi uvicorn pydantic")
    sys.exit(1)

# ============================================================
# 配置
# ============================================================

GATEWAY_DIR = Path(__file__).parent
SKILLS_DIR = GATEWAY_DIR / "skills"
DATA_DIR = GATEWAY_DIR.parent / "data"
CONDA_ENV = "zf-li23"

# 技能列表（从 SKILL.md 自动发现）
SKILLS: dict[str, dict] = {}

# ============================================================
# Pydantic 模型
# ============================================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    data_path: Optional[str] = None

class SkillRequest(BaseModel):
    data_path: Optional[str] = None
    args: dict = {}

class PlanStep(BaseModel):
    step: int
    skill: str
    purpose: str
    status: str = "pending"
    args: dict = {}

class PlanResponse(BaseModel):
    plan: list[PlanStep]
    explanation: str

# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="SpatialAgent Gateway",
    description="空间组学 AI 分析网关",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 技能发现
# ============================================================

def discover_skills():
    """扫描 skills/ 目录，解析 SKILL.md 中的 YAML 元数据"""
    global SKILLS
    SKILLS = {}

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue

        skill_md = skill_dir / "SKILL.md"
        run_py = skill_dir / "run.py"

        if not run_py.exists():
            continue

        info = {
            "name": skill_dir.name,
            "path": str(skill_dir),
            "run_script": str(run_py),
        }

        # 解析 SKILL.md 的 YAML 前置元数据
        if skill_md.exists():
            info.update(parse_skill_md(skill_md))

        SKILLS[skill_dir.name] = info

    print(f"[Gateway] 发现 {len(SKILLS)} 个技能: {list(SKILLS.keys())}")


def parse_skill_md(path: Path) -> dict:
    """从 SKILL.md 提取 YAML 前置元数据"""
    info = {}
    try:
        with open(path) as f:
            content = f.read()

        # 提取 YAML front matter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # 简单的 key: value 解析（避免 yaml 依赖）
                for line in parts[1].strip().split("\n"):
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        key, val = line.split(":", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        # 提取 trigger_keywords
                        if key == "trigger_keywords":
                            val = val.strip("[]").replace('"', '').split(",")
                            val = [v.strip() for v in val]
                        info[key] = val
    except Exception:
        pass
    return info


# ============================================================
# 技能执行
# ============================================================

def run_skill(skill_name: str, args: dict) -> dict:
    """通过 conda run 执行指定技能"""
    if skill_name not in SKILLS:
        raise HTTPException(404, f"技能 {skill_name} 不存在")

    skill = SKILLS[skill_name]
    run_script = skill["run_script"]

    # 构建参数
    cmd_args = []
    for k, v in args.items():
        cmd_args.extend([f"--{k}", str(v)])

    # 确保 data_path 默认值
    if "data_path" not in args:
        default_data = str(DATA_DIR / "visium_lymph_node.h5ad")
        if os.path.exists(default_data):
            cmd_args.extend(["--data_path", default_data])

    cmd = [
        "conda", "run", "--no-capture-output",
        "-n", CONDA_ENV,
        "python", "-u", run_script,
        *cmd_args,
    ]

    print(f"[Gateway] 执行技能: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=SKILLS.get("timeout_seconds", 300),
            cwd=str(GATEWAY_DIR),
        )

        if result.returncode != 0:
            return {
                "skill": skill_name,
                "success": False,
                "error": result.stderr.strip() or result.stdout.strip(),
            }

        # 尝试解析 JSON 输出
        stdout = result.stdout.strip()
        try:
            output = json.loads(stdout)
        except json.JSONDecodeError:
            # 取最后一行的 JSON
            lines = stdout.split("\n")
            for line in reversed(lines):
                try:
                    output = json.loads(line.strip())
                    break
                except json.JSONDecodeError:
                    continue
            else:
                output = {"raw_output": stdout}

        return {
            "skill": skill_name,
            "success": True,
            "output": output,
        }

    except subprocess.TimeoutExpired:
        return {
            "skill": skill_name,
            "success": False,
            "error": "执行超时",
        }


# ============================================================
# 数据集发现
# ============================================================

def discover_datasets() -> list[dict]:
    """扫描 data/ 目录的 .h5ad 文件"""
    datasets = []
    for h5ad_path in sorted(DATA_DIR.glob("*.h5ad")):
        try:
            import anndata
            adata = anndata.read_h5ad(h5ad_path)
            datasets.append({
                "name": h5ad_path.name,
                "path": str(h5ad_path),
                "shape": list(adata.shape),
                "n_spots": adata.n_obs,
                "n_genes": adata.n_vars,
            })
        except Exception:
            datasets.append({
                "name": h5ad_path.name,
                "path": str(h5ad_path),
                "shape": [0, 0],
                "n_spots": 0,
                "n_genes": 0,
            })
    return datasets


# ============================================================
# 智能规划（模拟版 — 后续接入 DeepSeek）
# ============================================================

def generate_plan(message: str) -> PlanResponse:
    """根据用户消息生成执行计划"""
    steps = []

    # 简单规则匹配
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in ["加载", "质控", "qc", "预处理", "读入"]):
        steps.append(PlanStep(step=1, skill="st_preprocess", purpose="加载数据并进行质控"))

    if any(kw in msg_lower for kw in ["高变基因", "svg", "空间模式", "空间可变", "spatial pattern"]):
        steps.append(PlanStep(
            step=len(steps) + 1,
            skill="st_spatial_pattern",
            purpose="识别空间可变基因 (Moran's I)",
            args={"method": "morans_i"},
        ))

    if any(kw in msg_lower for kw in ["区域", "region", "坐标", "表达量"]):
        steps.append(PlanStep(
            step=len(steps) + 1,
            skill="st_region_query",
            purpose="查询指定区域的基因表达量",
            args={"x_min": 0, "x_max": 500, "y_min": 0, "y_max": 500},
        ))

    if any(kw in msg_lower for kw in ["轨迹", "trajectory", "伪时间", "pseudotime"]):
        steps.append(PlanStep(
            step=len(steps) + 1,
            skill="st_trajectory",
            purpose="空间轨迹推断与伪时间分析",
        ))

    if any(kw in msg_lower for kw in ["通讯", "配体", "受体", "cell communication", "ccc"]):
        steps.append(PlanStep(
            step=len(steps) + 1,
            skill="st_cell_comm",
            purpose="配体-受体互作分析",
            args={"method": "liana"},
        ))

    if not steps:
        # 默认：预处理 + SVG
        steps = [
            PlanStep(step=1, skill="st_preprocess", purpose="加载数据并进行质控"),
            PlanStep(step=2, skill="st_spatial_pattern", purpose="识别空间可变基因"),
        ]

    return PlanResponse(
        plan=steps,
        explanation=f"已为您生成 {len(steps)} 步分析计划",
    )


# ============================================================
# API 路由
# ============================================================

@app.get("/health")
async def health():
    return {"status": "ok", "skills": len(SKILLS)}


@app.get("/skills")
async def list_skills():
    return [
        {
            "name": name,
            "description": info.get("description", ""),
            "triggers": info.get("trigger_keywords", []),
        }
        for name, info in SKILLS.items()
    ]


@app.get("/datasets")
async def list_datasets():
    return discover_datasets()


@app.post("/chat")
async def chat(request: ChatRequest):
    """接收聊天消息 → 规划 → 执行 → 返回结果"""
    print(f"[Gateway] 收到消息: {request.message}")

    # Step 1: 生成计划
    plan_resp = generate_plan(request.message)

    # Step 2: 按顺序执行技能
    results = []
    for step in plan_resp.plan:
        step.status = "running"
        result = run_skill(step.skill, step.args)
        if result.get("success"):
            step.status = "completed"
        else:
            step.status = "failed"
        results.append(result)
        step.status = step.status  # 同步

    return {
        "plan": [s.model_dump() for s in plan_resp.plan],
        "results": results,
        "explanation": plan_resp.explanation,
    }


@app.post("/skills/{skill_name}")
async def execute_skill(skill_name: str, request: SkillRequest):
    """直接执行单个技能"""
    args = request.args
    if request.data_path:
        args["data_path"] = request.data_path
    return run_skill(skill_name, args)


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧬 SpatialAgent Gateway v0.1")
    print("=" * 60)
    discover_skills()
    discover_datasets()
    print(f"[Gateway] 数据集目录: {DATA_DIR}")
    print(f"[Gateway] 启动于 http://0.0.0.0:3000")
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
