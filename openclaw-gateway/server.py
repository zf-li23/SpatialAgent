# ============================================================
# SpatialAgent — FastAPI 网关服务器
# 简化版 OpenClaw 网关，桥接前端与 Python 技能
# v0.2: 集成 AgentOrchestrator (Planner + Executor + Evaluator)
# ============================================================

import sys
import os
import json
import logging
from pathlib import Path
from typing import Optional

# 确保能引用 repos 和 agents 模块
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "repos")
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from agents.spatial_executor import run_skill
from agents.spatial_planner import plan_task as _plan_task
from agents.orchestrator import get_orchestrator
from planner.adaptive_planner import build_pipeline, execute_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spatialagent.gateway")

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

# 技能元数据缓存
_skills_cache: dict[str, dict] = {}

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

# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="SpatialAgent Gateway",
    description="空间组学 AI 分析网关 v0.2",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 技能发现（委托给 spatial_executor）
# ============================================================

def discover_skills() -> dict[str, dict]:
    """扫描 skills/ 目录"""
    global _skills_cache
    if _skills_cache:
        return _skills_cache

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        run_py = skill_dir / "run.py"
        if not run_py.exists():
            continue
        info = {"name": skill_dir.name, "path": str(skill_dir), "run_script": str(run_py)}
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            info.update(_parse_skill_md(skill_md))
        _skills_cache[skill_dir.name] = info

    logger.info(f"发现 {len(_skills_cache)} 个技能: {list(_skills_cache.keys())}")
    return _skills_cache


def _parse_skill_md(path: Path) -> dict:
    """从 SKILL.md 提取 YAML 前置元数据"""
    info = {}
    try:
        with open(path) as f:
            content = f.read()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        key, val = line.split(":", 1)
                        key, val = key.strip(), val.strip().strip('"').strip("'")
                        if key == "trigger_keywords":
                            val = [v.strip() for v in val.strip("[]").replace('"', '').split(",")]
                        info[key] = val
    except Exception:
        pass
    return info


# ============================================================
# 技能执行（委托给 spatial_executor.run_skill）
# ============================================================

def _run_skill_via_executor(skill_name: str, args: dict) -> dict:
    """通过 spatial_executor 的 run_skill 执行"""
    discover_skills()  # 确保缓存中有技能信息
    skill_info = _skills_cache.get(skill_name, {})
    # 合并默认参数
    if "data_path" not in args:
        default_data = str(DATA_DIR / "visium_lymph_node.h5ad")
        if os.path.exists(default_data):
            args["data_path"] = default_data
    return run_skill(skill_name, args)


# ============================================================
# 数据集发现
# ============================================================

def discover_datasets() -> list[dict]:
    """扫描 data/ 目录的 .h5ad 文件"""
    import anndata
    datasets = []
    for h5ad_path in sorted(DATA_DIR.glob("*.h5ad")):
        try:
            adata = anndata.read_h5ad(h5ad_path, backed="r")
            info = {
                "name": h5ad_path.name,
                "path": str(h5ad_path),
                "shape": list(adata.shape),
                "n_spots": adata.n_obs,
                "n_genes": adata.n_vars,
            }
            adata.file.close()
            datasets.append(info)
        except Exception:
            datasets.append({"name": h5ad_path.name, "path": str(h5ad_path)})
    return datasets


# ============================================================
# API 路由
# ============================================================

@app.get("/health")
async def health():
    skills = discover_skills()
    return {"status": "ok", "version": "0.2.0", "skills": len(skills)}


@app.get("/skills")
async def list_skills():
    skills = discover_skills()
    return [
        {
            "name": name,
            "description": info.get("description", ""),
            "triggers": info.get("trigger_keywords", []),
        }
        for name, info in skills.items()
    ]


@app.get("/datasets")
async def list_datasets():
    return discover_datasets()


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    接收聊天消息 → AgentOrchestrator 编排 → 返回结果
    
    编排流程: SpatialPlanner(规划) → SpatialExecutor(执行) → Evaluator(评估)
    """
    logger.info(f"收到消息: {request.message[:80]}")

    datasets = discover_datasets()
    orchestrator = get_orchestrator()

    # 使用编排器执行完整流水线
    result = orchestrator.run(
        user_message=request.message,
        data_path=request.data_path,
        datasets=datasets,
    )

    return {
        "plan": result["plan"],
        "results": result["results"],
        "explanation": result["explanation"],
        "evaluation": result.get("evaluation", {}),
        "retries": result.get("retries", 0),
    }


@app.post("/skills/{skill_name}")
async def execute_skill(skill_name: str, request: SkillRequest):
    """直接执行单个技能"""
    args = request.args
    if request.data_path:
        args["data_path"] = request.data_path
    return _run_skill_via_executor(skill_name, args)


@app.post("/plan")
async def plan_only(request: ChatRequest):
    """仅规划，不执行（用于预览）"""
    datasets = discover_datasets()
    plan_result = _plan_task(request.message, request.data_path, datasets)
    return plan_result


@app.post("/adaptive")
async def adaptive_pipeline(request: ChatRequest):
    """AdaptivePlanner：模糊请求 → 自动构建分析流水线 → 执行"""
    logger.info(f"自适应规划: {request.message[:80]}")
    try:
        datasets = discover_datasets()
        pipeline = build_pipeline(request.message, datasets=datasets, data_path=request.data_path)
        results = execute_pipeline(pipeline, data_path=request.data_path)
        return {"mode": "adaptive", "pipeline": pipeline, "results": results}
    except Exception as e:
        logger.error(f"自适应规划失败: {e}")
        raise HTTPException(500, f"自适应规划失败: {str(e)}")


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧬 SpatialAgent Gateway v0.2")
    print("   Planner: SpatialPlanner (LLM + rules)")
    print("   Executor: SpatialExecutor (5 skills)")
    print("   Evaluator: Quality gate with retry")
    print("=" * 60)
    discover_skills()
    ds = discover_datasets()
    print(f"[Gateway] 数据集: {len(ds)} 个")
    for d in ds:
        print(f"  - {d['name']} ({d.get('n_spots', '?')} spots)")
    print(f"[Gateway] 启动于 http://0.0.0.0:3000")
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
