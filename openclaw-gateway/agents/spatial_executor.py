# ============================================================
# SpatialAgent — SpatialExecutor Agent
# 执行者，按计划顺序调用 Python 技能
# 参考: OpenBioLLM 的 agent 执行模式
# ============================================================

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("spatialagent.executor")

# 路径
GATEWAY_DIR = Path(__file__).parent.parent
SKILLS_DIR = GATEWAY_DIR / "skills"
DATA_DIR = GATEWAY_DIR.parent / "data"
CONDA_ENV = "zf-li23"

EXECUTOR_SYSTEM_PROMPT = """你是空间组学分析的执行专家 SpatialExecutor。

你的职责：
1. 接收 SpatialPlanner 的执行计划
2. 按顺序调用指定的技能
3. 收集每个步骤的结果
4. 汇总生成最终的分析报告

你必须严格按照计划顺序执行，上一步的输出会作为下一步的上下文。

可用技能：
- st_preprocess: 数据加载与质控
- st_spatial_pattern: 空间可变基因分析 (Moran's I)
- st_region_query: 区域表达量查询
- st_trajectory: 空间轨迹推断 (DPT/PAGA)
- st_cell_comm: 细胞通讯分析 (配体-受体)"""


def execute_plan(
    plan: list[dict],
    data_path: Optional[str] = None,
    on_step_start: Optional[callable] = None,
    on_step_end: Optional[callable] = None,
) -> list[dict]:
    """
    按顺序执行计划中的每个步骤。

    Args:
        plan: [{"step": 1, "skill": "st_preprocess", "args": {}, ...}, ...]
        data_path: 数据文件路径
        on_step_start: 步骤开始回调 (step: dict) -> None
        on_step_end: 步骤结束回调 (step: dict, result: dict) -> None

    Returns:
        [{"skill": "...", "success": bool, "output": {...}}, ...]
    """
    results = []
    ctx = {"data_path": data_path}  # 上下文传递

    for step in plan:
        skill_name = step.get("skill", "")
        step_args = step.get("args", {})

        # 传递 data_path
        if "data_path" not in step_args and ctx.get("data_path"):
            step_args["data_path"] = ctx["data_path"]

        # 回调
        if on_step_start:
            on_step_start(step)

        logger.info(f"执行步骤 {step.get('step')}: {skill_name} - {step.get('purpose')}")

        # 执行技能
        result = run_skill(skill_name, step_args)

        # 更新上下文
        if result.get("success") and result.get("output"):
            ctx["last_output"] = result["output"]
            # 如果输出中有 data_path，更新
            if isinstance(result["output"], dict):
                ctx.update({k: v for k, v in result["output"].items()
                           if not k.startswith("_")})

        # 回调
        if on_step_end:
            on_step_end(step, result)

        results.append(result)

        # 如果步骤失败，停止后续执行
        if not result.get("success"):
            logger.warning(f"步骤 {skill_name} 失败，停止后续执行")
            break

    return results


def run_skill(skill_name: str, args: dict) -> dict:
    """通过 conda run 执行单个技能"""
    skill_dir = SKILLS_DIR / skill_name
    run_script = skill_dir / "run.py"

    if not run_script.exists():
        return {
            "skill": skill_name,
            "success": False,
            "error": f"技能脚本不存在: {run_script}",
        }

    # 构建命令行参数
    cmd_args = []
    for k, v in args.items():
        if v is None or v == "":
            continue
        cmd_args.extend([f"--{k}", str(v)])

    # 默认 data_path
    if "data_path" not in args:
        default_data = str(DATA_DIR / "visium_lymph_node.h5ad")
        if os.path.exists(default_data):
            cmd_args.extend(["--data_path", default_data])

    cmd = [
        "conda", "run", "--no-capture-output",
        "-n", CONDA_ENV,
        "python", "-u", str(run_script),
        *cmd_args,
    ]

    logger.debug(f"执行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(GATEWAY_DIR),
        )

        if result.returncode != 0:
            return {
                "skill": skill_name,
                "success": False,
                "error": result.stderr.strip()[-500:] or result.stdout.strip()[-500:],
            }

        # 解析 JSON 输出
        stdout = result.stdout.strip()
        output = None
        for line in reversed(stdout.split("\n")):
            line = line.strip()
            if line.startswith("{"):
                try:
                    output = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if output is None:
            output = {"raw_output": stdout[:500]}

        return {
            "skill": skill_name,
            "success": True,
            "output": output,
        }

    except subprocess.TimeoutExpired:
        return {
            "skill": skill_name,
            "success": False,
            "error": "执行超时（>300秒）",
        }
    except Exception as e:
        return {
            "skill": skill_name,
            "success": False,
            "error": str(e),
        }


# ============================================================
# Evaluator — 质量门控（参考 OpenBioLLM 的 Evaluator）
# ============================================================

def evaluate_results(
    user_message: str,
    plan: list[dict],
    results: list[dict],
) -> dict:
    """
    评估执行结果是否满足用户请求。
    若质量不足，返回需要重试的技能。

    参考: OpenBioLLM 的 Evaluator 节点：
    如果答案不充分 → 回退到 Router 重新规划
    """
    failed_steps = [r for r in results if not r.get("success")]
    success_steps = [r for r in results if r.get("success")]

    evaluation = {
        "passed": len(failed_steps) == 0,
        "total_steps": len(results),
        "success_steps": len(success_steps),
        "failed_steps": len(failed_steps),
        "failed_skills": [r["skill"] for r in failed_steps],
        "needs_retry": len(failed_steps) > 0,
        "retry_plan": None,
    }

    if failed_steps:
        # 生成重试计划：只重试失败的步骤
        evaluation["retry_plan"] = [
            {
                "step": i + 1,
                "skill": r["skill"],
                "purpose": f"重试: {r.get('error', '未知错误')[:100]}",
                "status": "pending",
                "args": {},
            }
            for i, r in enumerate(failed_steps)
        ]

    return evaluation
