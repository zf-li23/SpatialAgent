# ============================================================
# SpatialAgent — SpatialPlanner Agent
# 只读规划者，负责拆解用户意图为子任务序列
# 参考: OpenBioLLM 的 Router 路由模式
# ============================================================

import os
import sys
import json
import logging
from typing import Optional

logger = logging.getLogger("spatialagent.planner")

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llm_client import get_llm_client, has_api_key

# 可用技能清单
AVAILABLE_SKILLS = """
- st_preprocess: 数据加载与质控（读取 .h5ad 文件，返回 spots/genes/QC 指标）
- st_spatial_pattern: 空间可变基因分析（Moran's I 识别空间模式基因）
- st_region_query: 区域表达量查询（给定坐标范围，返回基因平均表达量）
- st_trajectory: 空间轨迹推断（伪时间分析，DPT + PAGA）
- st_cell_comm: 细胞通讯分析（配体-受体互作推断）
"""

PLANNER_SYSTEM_PROMPT = f"""你是空间组学分析的规划专家 SpatialPlanner。

你的职责：
1. 分析用户的自然语言请求，提取关键分析意图
2. 将复杂请求拆解为有序的子任务序列
3. 为每个子任务匹配合适的技能
4. 输出结构化的执行计划（JSON格式）

你只能进行规划，不能执行任何技能。执行由 SpatialExecutor 负责。

可用技能清单：
{AVAILABLE_SKILLS}

输出格式（严格 JSON）：
{{
  "plan": [
    {{"step": 1, "skill": "st_preprocess", "purpose": "加载数据并进行质控", "args": {{}}}},
    {{"step": 2, "skill": "st_spatial_pattern", "purpose": "识别空间可变基因", "args": {{"method": "morans_i"}}}}
  ],
  "explanation": "对用户请求的简要中文说明"
}}

注意：
- 所有分析必须先执行 st_preprocess（除非用户已加载数据）
- 如果用户请求模糊，优先计划 st_preprocess + st_spatial_pattern
- args 中只需填写非默认参数
- explanation 必须用中文
"""


def plan_task(
    user_message: str,
    data_path: Optional[str] = None,
    datasets: Optional[list] = None,
) -> dict:
    """
    根据用户消息生成执行计划。

    若 DeepSeek API Key 可用，使用 LLM 规划；
    否则回退到规则匹配。
    """

    # 尝试 LLM 规划
    if has_api_key():
        try:
            return _llm_plan(user_message, data_path, datasets)
        except Exception as e:
            logger.warning(f"LLM 规划失败，回退到规则匹配: {e}")

    # 规则匹配回退
    return _rule_based_plan(user_message, data_path)


def _llm_plan(user_message: str, data_path: Optional[str], datasets: Optional[list]) -> dict:
    """使用 DeepSeek LLM 进行智能规划"""
    client = get_llm_client()

    # 构建上下文
    context = ""
    if datasets:
        context += "\n可用数据集：\n"
        for ds in datasets:
            context += f"  - {ds.get('name', ds.get('filename', 'unknown'))} ({ds.get('n_spots', '?')} spots)\n"
    if data_path:
        context += f"\n当前数据路径：{data_path}\n"

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": f"{context}\n用户请求：{user_message}"},
    ]

    result = client.chat_json(messages, fallback=_rule_based_plan(user_message, data_path))

    # 标准化输出格式
    if "plan" not in result:
        result = _rule_based_plan(user_message, data_path)

    # 确保每个 step 有 status 字段
    for step in result.get("plan", []):
        step.setdefault("status", "pending")
        step.setdefault("args", {})

    return result


def _rule_based_plan(user_message: str, data_path: Optional[str] = None) -> dict:
    """基于规则的规划（无需 LLM）"""
    msg_lower = user_message.lower()
    steps = []

    # 总是从预处理开始
    need_preprocess = any(
        kw in msg_lower
        for kw in ["加载", "质控", "qc", "预处理", "读入", "load", "preprocess"]
    ) or True  # 默认都需要预处理

    if need_preprocess:
        steps.append({
            "step": 1,
            "skill": "st_preprocess",
            "purpose": "加载数据并进行质控",
            "status": "pending",
            "args": {},
        })

    step_num = len(steps)

    # 空间可变基因
    if any(kw in msg_lower for kw in ["高变基因", "svg", "空间模式", "空间可变", "spatial pattern", "moran"]):
        step_num += 1
        steps.append({
            "step": step_num,
            "skill": "st_spatial_pattern",
            "purpose": "识别空间可变基因 (Moran's I)",
            "status": "pending",
            "args": {"method": "morans_i"},
        })

    # 区域查询
    if any(kw in msg_lower for kw in ["区域", "region", "坐标", "表达量"]):
        step_num += 1
        steps.append({
            "step": step_num,
            "skill": "st_region_query",
            "purpose": "查询指定区域的基因表达量",
            "status": "pending",
            "args": {},
        })

    # 轨迹
    if any(kw in msg_lower for kw in ["轨迹", "trajectory", "伪时间", "pseudotime"]):
        step_num += 1
        steps.append({
            "step": step_num,
            "skill": "st_trajectory",
            "purpose": "空间轨迹推断与伪时间分析",
            "status": "pending",
            "args": {},
        })

    # 细胞通讯
    if any(kw in msg_lower for kw in ["通讯", "配体", "受体", "cell communication", "ccc", "liana"]):
        step_num += 1
        steps.append({
            "step": step_num,
            "skill": "st_cell_comm",
            "purpose": "配体-受体互作分析",
            "status": "pending",
            "args": {"method": "correlation"},
        })

    # 如果没有任何特定分析请求，默认做 SVG
    if len(steps) <= 1:
        step_num += 1
        steps.append({
            "step": step_num,
            "skill": "st_spatial_pattern",
            "purpose": "识别空间可变基因（默认分析）",
            "status": "pending",
            "args": {"method": "morans_i"},
        })

    return {
        "plan": steps,
        "explanation": f"已为您生成 {len(steps)} 步分析计划（规则匹配模式）",
    }
