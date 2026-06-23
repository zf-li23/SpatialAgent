# ============================================================
# SpatialAgent — AdaptivePlanner 自适应规划模块
# 参考: Biomni 的 A1 智能体 env_desc 感知思想
#       根据模糊用户请求，自动组合技能形成分析流水线
# ============================================================

import os
import sys
import json
import logging
from typing import Optional

logger = logging.getLogger("spatialagent.adaptive")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llm_client import get_llm_client, has_api_key

# 技能能力矩阵
SKILL_CAPABILITIES = {
    "st_preprocess": {
        "category": "PROCESSING",
        "description": "数据加载与质控：读取 .h5ad 文件，计算 spots/genes 数量、线粒体比例、核糖体比例等 QC 指标",
        "triggers": ["加载", "读入", "打开", "质控", "QC", "质量", "预处理"],
        "produces": "QC 报告 JSON",
    },
    "st_spatial_pattern": {
        "category": "ANALYSIS",
        "description": "空间可变基因分析：使用 Moran's I 识别具有空间表达模式的基因",
        "triggers": ["高变", "SVG", "空间模式", "空间可变", "差异", "标记基因", "有什么问题", "异常"],
        "produces": "SVG 列表 + Moran's I 值",
    },
    "st_region_query": {
        "category": "ANALYSIS",
        "description": "区域表达量查询：根据坐标范围查询该区域的基因平均表达量",
        "triggers": ["区域", "坐标", "位置", "特定区域", "切片", "局部"],
        "produces": "区域表达量 JSON",
    },
    "st_trajectory": {
        "category": "ANALYSIS",
        "description": "空间轨迹推断：使用 DPT 和 PAGA 计算伪时间，推断空间分化轨迹",
        "triggers": ["轨迹", "伪时间", "分化", "发育", "pseudotime", "PAGA"],
        "produces": "伪时间序列 + 分支分配",
    },
    "st_cell_comm": {
        "category": "ANALYSIS",
        "description": "细胞通讯分析：基于空间邻域推断配体-受体互作",
        "triggers": ["通讯", "配体", "受体", "互作", "交流", "信号"],
        "produces": "显著配体-受体对列表",
    },
}

ADAPTIVE_PLANNER_PROMPT = """你是一个空间组学自适应分析规划器。

用户请求：{user_request}

可用数据集：
{available_datasets}

可用技能：
{available_skills}

请根据用户的请求（即使是模糊的），自动构建最优的分析流水线。

流水线节点类型：
- PROCESSING: 数据加载/预处理
- QC: 质量控制检查
- ANALYSIS: 核心分析（空间模式/轨迹/通讯）
- VISUALIZATION: 结果可视化

规则：
1. 所有流水线必须以 PROCESSING (st_preprocess) 开始
2. 模糊请求（如"帮我看看数据"、"有什么问题"）→ PROCESSING + ANALYSIS(st_spatial_pattern)
3. 明确提到特定分析 → 相应添加对应技能
4. 综合请求 → PROCESSING + 多个 ANALYSIS 技能

输出格式（严格 JSON）：
{{
  "pipeline_name": "简洁的流水线名称",
  "stages": [
    {{"type": "PROCESSING", "skill": "st_preprocess", "purpose": "加载数据并质控", "status": "pending"}},
    {{"type": "ANALYSIS", "skill": "st_spatial_pattern", "purpose": "识别空间可变基因", "status": "pending"}}
  ],
  "explanation": "中文说明：为什么选择这个流水线",
  "estimated_runtime_seconds": 30
}}
"""


def build_pipeline(
    user_message: str,
    datasets: Optional[list] = None,
    data_path: Optional[str] = None,
) -> dict:
    """
    根据用户模糊请求自动构建分析流水线。

    Args:
        user_message: 用户自然语言输入
        datasets: 可用数据集列表
        data_path: 当前数据路径

    Returns:
        {
            "pipeline_name": "...",
            "stages": [...],
            "explanation": "...",
            "estimated_runtime_seconds": 30
        }
    """

    # 尝试 LLM 规划
    if has_api_key():
        try:
            return _llm_build_pipeline(user_message, datasets)
        except Exception as e:
            logger.warning(f"LLM 自适应规划失败，回退规则: {e}")

    # 规则匹配回退
    return _rule_based_pipeline(user_message, datasets)


def _llm_build_pipeline(user_message: str, datasets: Optional[list]) -> dict:
    """使用 LLM 构建流水线"""
    client = get_llm_client()

    # 构建上下文
    ds_text = "无"
    if datasets:
        ds_text = "\n".join(
            f"  - {d.get('name', 'unknown')} ({d.get('n_spots', '?')} spots × {d.get('n_genes', '?')} genes)"
            for d in datasets
        )

    skills_text = "\n".join(
        f"  - {name}: {info['description']} (触发词: {', '.join(info['triggers'][:3])})"
        for name, info in SKILL_CAPABILITIES.items()
    )

    prompt = ADAPTIVE_PLANNER_PROMPT.replace("{user_request}", user_message).replace("{available_datasets}", ds_text).replace("{available_skills}", skills_text)

    messages = [
        {"role": "system", "content": "你是一个空间组学分析规划器。始终输出 JSON。"},
        {"role": "user", "content": prompt},
    ]

    result = client.chat_json(messages, fallback=_rule_based_pipeline(user_message, datasets))

    # 确保 stages 有 status 字段
    for stage in result.get("stages", []):
        stage.setdefault("status", "pending")

    return result


def _rule_based_pipeline(user_message: str, datasets: Optional[list] = None) -> dict:
    """基于规则的自适应流水线构建"""
    msg_lower = user_message.lower()
    stages = []

    # Step 1: 始终以预处理开始
    stages.append({
        "type": "PROCESSING",
        "skill": "st_preprocess",
        "purpose": "加载数据并进行质控",
        "status": "pending",
    })

    # 分析意图识别
    analysis_added = False

    # 模糊请求 → 默认 SVG（但不要和下面的具体关键词重复）
    fuzzy_keywords = ["看看", "有什么", "怎么样", "分析一下", "帮我", "检查", "查看", "问题", "异常"]
    if any(kw in msg_lower for kw in fuzzy_keywords):
        stages.append({
            "type": "ANALYSIS",
            "skill": "st_spatial_pattern",
            "purpose": "识别空间可变基因（模糊请求默认分析）",
            "status": "pending",
        })
        analysis_added = True

    # 空间模式/差异（如果上面模糊匹配没加）
    if not analysis_added and any(kw in msg_lower for kw in ["高变", "svg", "空间模式", "空间可变", "差异", "标记", "表达模式"]):
        stages.append({
            "type": "ANALYSIS",
            "skill": "st_spatial_pattern",
            "purpose": "识别空间可变基因 (Moran's I)",
            "status": "pending",
        })
        analysis_added = True
    if any(kw in msg_lower for kw in ["区域", "坐标", "位置", "特定区域", "切片区域", "局部"]):
        stages.append({
            "type": "ANALYSIS",
            "skill": "st_region_query",
            "purpose": "查询指定区域的基因表达量",
            "status": "pending",
        })
        analysis_added = True

    # 轨迹
    if any(kw in msg_lower for kw in ["轨迹", "伪时间", "分化", "发育", "pseudotime", "paga"]):
        stages.append({
            "type": "ANALYSIS",
            "skill": "st_trajectory",
            "purpose": "空间轨迹推断与伪时间分析",
            "status": "pending",
        })
        analysis_added = True

    # 细胞通讯
    if any(kw in msg_lower for kw in ["通讯", "配体", "受体", "互作", "交流", "信号", "ccc"]):
        stages.append({
            "type": "ANALYSIS",
            "skill": "st_cell_comm",
            "purpose": "配体-受体互作分析",
            "status": "pending",
        })
        analysis_added = True

    # 综合请求（包含多个关键词）→ 多技能
    if not analysis_added:
        stages.append({
            "type": "ANALYSIS",
            "skill": "st_spatial_pattern",
            "purpose": "识别空间可变基因（默认分析）",
            "status": "pending",
        })

    # 估算运行时间
    runtime = 15  # 预处理
    for s in stages:
        if s["skill"] == "st_spatial_pattern":
            runtime += 20
        elif s["skill"] == "st_trajectory":
            runtime += 25
        elif s["skill"] == "st_cell_comm":
            runtime += 10
        elif s["skill"] == "st_region_query":
            runtime += 5

    # 生成流水线名称
    analysis_names = [s["skill"].replace("st_", "") for s in stages if s["type"] == "ANALYSIS"]
    pipeline_name = "空间组学" + "+".join(analysis_names) + "分析"

    return {
        "pipeline_name": pipeline_name,
        "stages": stages,
        "explanation": f"自动构建的分析流水线（规则匹配模式）：{' → '.join(s['purpose'] for s in stages)}",
        "estimated_runtime_seconds": runtime,
    }


# ============================================================
# 流水线执行器
# ============================================================

def execute_pipeline(
    pipeline: dict,
    data_path: Optional[str] = None,
    on_stage_update: Optional[callable] = None,
) -> list[dict]:
    """
    执行流水线中的每个阶段。

    将 AdaptivePlanner 的 stages 转换为 SpatialExecutor 可执行的 plan。
    """
    from agents.spatial_executor import execute_plan

    # 转换 stages → plan 格式
    plan = []
    for i, stage in enumerate(pipeline.get("stages", [])):
        if stage.get("skill"):  # VISUALIZATION 阶段可能没有 skill
            plan.append({
                "step": i + 1,
                "skill": stage["skill"],
                "purpose": stage.get("purpose", ""),
                "status": "pending",
                "args": {},
                "stage_type": stage.get("type", ""),
            })

    # 使用 SpatialExecutor 执行
    results = execute_plan(plan, data_path=data_path)

    # 同步 stages 状态
    for stage in pipeline.get("stages", []):
        skill = stage.get("skill", "")
        if not skill:
            stage["status"] = "completed"
            continue
        match = [r for r in results if r.get("skill") == skill]
        if match:
            stage["status"] = "completed" if match[0].get("success") else "failed"

    return results
