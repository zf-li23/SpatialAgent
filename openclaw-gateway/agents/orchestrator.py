# ============================================================
# SpatialAgent — 双 Agent 编排器
# 串联 SpatialPlanner → SpatialExecutor → Evaluator
# 参考: OpenBioLLM 的 LangGraph 图结构 (Router→Agent→Evaluator)
# ============================================================

import os
import sys
import logging
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from spatial_planner import plan_task
from spatial_executor import execute_plan, evaluate_results

logger = logging.getLogger("spatialagent.orchestrator")


class AgentOrchestrator:
    """
    双 Agent 编排器。

    工作流:
       用户输入 → SpatialPlanner(规划) → SpatialExecutor(执行) → Evaluator(评估)
                                                    ↑                    |
                                                    └── 重试（若失败）───┘
    """

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    def run(
        self,
        user_message: str,
        data_path: Optional[str] = None,
        datasets: Optional[list] = None,
        on_plan_ready: Optional[callable] = None,
        on_step_update: Optional[callable] = None,
    ) -> dict:
        """
        执行完整分析流水线。

        Args:
            user_message: 用户自然语言输入
            data_path: 数据文件路径
            datasets: 可用数据集列表
            on_plan_ready: 计划生成回调
            on_step_update: 步骤状态更新回调

        Returns:
            {
                "plan": [...],
                "results": [...],
                "evaluation": {...},
                "explanation": "..."
            }
        """
        # Phase 1: 规划
        logger.info(f"[Orchestrator] 规划阶段: {user_message[:80]}")
        plan_result = plan_task(user_message, data_path, datasets)
        plan = plan_result.get("plan", [])

        if on_plan_ready:
            on_plan_ready(plan_result)

        # Phase 2: 执行（含重试）
        results = []
        retry_count = 0

        while retry_count <= self.max_retries:
            # 标记所有步骤为 pending
            for step in plan:
                step["status"] = "pending"

            # 执行计划
            results = execute_plan(
                plan,
                data_path=data_path,
                on_step_start=lambda s: _notify_step(s, "running", on_step_update),
                on_step_end=lambda s, r: _notify_step(s, "completed" if r.get("success") else "failed", on_step_update, r),
            )

            # Phase 3: 评估
            evaluation = evaluate_results(user_message, plan, results)

            if not evaluation["needs_retry"]:
                break

            # 准备重试
            retry_count += 1
            logger.warning(f"[Orchestrator] 第 {retry_count} 次重试")
            plan = evaluation.get("retry_plan", [])

        return {
            "plan": plan,
            "results": results,
            "evaluation": evaluate_results(user_message, plan, results),
            "explanation": plan_result.get("explanation", ""),
            "retries": retry_count,
        }


def _notify_step(step: dict, status: str, callback: Optional[callable], result: dict = None):
    """通知步骤状态变更"""
    step["status"] = status
    if result:
        step["result"] = result
    if callback:
        try:
            callback(step)
        except Exception:
            pass


# ============================================================
# 单例
# ============================================================

_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
