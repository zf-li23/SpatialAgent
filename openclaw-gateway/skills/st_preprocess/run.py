#!/usr/bin/env python3
# ============================================================
# st_preprocess — 空间转录组数据加载与质控
# 复用: scanpy 核心功能
# ============================================================

import sys
import os
import json
import argparse

# 添加 repos 路径，以便复用现有仓库代码
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "repos")
sys.path.insert(0, REPO_ROOT)

import scanpy as sc
import numpy as np
import pandas as pd


def preprocess(data_path: str) -> dict:
    """加载 .h5ad 数据，执行基本质控，返回 QC 指标"""

    # 1. 读取数据
    print(f"[st_preprocess] 正在读取: {data_path}", file=sys.stderr)
    adata = sc.read_h5ad(data_path)

    # 确保 var_names 唯一
    adata.var_names_make_unique()

    # 2. 提取空间坐标
    spatial_key = None
    if "spatial" in adata.obsm:
        spatial_key = "spatial"
    elif "X_spatial" in adata.obsm:
        spatial_key = "X_spatial"

    spatial_shape = list(adata.obsm[spatial_key].shape) if spatial_key else None

    # 3. 计算 QC 指标
    # 标注线粒体和核糖体基因
    adata.var["mt"] = adata.var_names.str.startswith("MT-")
    adata.var["ribo"] = adata.var_names.str.startswith(("RPS", "RPL"))

    sc.pp.calculate_qc_metrics(
        adata,
        qc_vars=["mt", "ribo"],
        inplace=True,
        percent_top=None,
        log1p=False,
    )

    # 4. 汇总 QC 报告
    qc_report = {
        "n_spots": int(adata.n_obs),
        "n_genes": int(adata.n_vars),
        "median_genes_per_spot": float(adata.obs["n_genes_by_counts"].median()),
        "median_umi_per_spot": float(adata.obs["total_counts"].median()),
        "pct_mito": float(adata.obs["pct_counts_mt"].mean()),
        "pct_ribo": float(adata.obs["pct_counts_ribo"].mean()),
        "spatial_coords_shape": spatial_shape,
    }

    # 添加 min/max
    qc_report["min_genes_per_spot"] = int(adata.obs["n_genes_by_counts"].min())
    qc_report["max_genes_per_spot"] = int(adata.obs["n_genes_by_counts"].max())

    print(f"[st_preprocess] QC 完成: {qc_report['n_spots']} spots × {qc_report['n_genes']} genes",
          file=sys.stderr)

    return qc_report


def main():
    parser = argparse.ArgumentParser(description="空间数据加载与质控")
    parser.add_argument("--data_path", type=str, required=True,
                        help=".h5ad 文件路径")
    args = parser.parse_args()

    data_path = args.data_path
    if not os.path.exists(data_path):
        # 尝试相对于项目根目录
        alt_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data",
            os.path.basename(data_path)
        )
        if os.path.exists(alt_path):
            data_path = alt_path
        else:
            print(json.dumps({"error": f"文件不存在: {args.data_path}"}))
            sys.exit(1)

    result = preprocess(data_path)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
