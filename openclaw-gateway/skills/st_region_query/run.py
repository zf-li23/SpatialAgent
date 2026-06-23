#!/usr/bin/env python3
# ============================================================
# st_region_query — 空间区域表达量查询
# 参考: qust 的 LLM-空间交互模式（纯函数，无 GUI 依赖）
# ============================================================

import sys
import os
import json
import argparse

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "repos")
sys.path.insert(0, REPO_ROOT)

import scanpy as sc
import numpy as np
import pandas as pd


def query_region(
    data_path: str,
    x_min: float, x_max: float,
    y_min: float, y_max: float,
    gene_list: list[str] | None = None,
    top_n_genes: int = 5,
) -> dict:
    """查询空间区域内的基因表达"""

    print(f"[st_region_query] 正在读取: {data_path}", file=sys.stderr)
    adata = sc.read_h5ad(data_path)
    adata.var_names_make_unique()

    # 1. 获取空间坐标
    spatial_key = None
    if "spatial" in adata.obsm:
        spatial_key = "spatial"
    elif "X_spatial" in adata.obsm:
        spatial_key = "X_spatial"
    else:
        return {"error": "数据中没有空间坐标 (adata.obsm['spatial'])"}

    coords = adata.obsm[spatial_key]

    # 自动缩放坐标范围（若用户未提供合理范围）
    coord_x_min, coord_x_max = float(coords[:, 0].min()), float(coords[:, 0].max())
    coord_y_min, coord_y_max = float(coords[:, 1].min()), float(coords[:, 1].max())

    # 如果用户范围明显超出数据范围，自动调整到中央 60% 区域
    if x_max - x_min > coord_x_max - coord_x_min or x_max < coord_x_min:
        margin_x = (coord_x_max - coord_x_min) * 0.2
        margin_y = (coord_y_max - coord_y_min) * 0.2
        x_min = coord_x_min + margin_x
        x_max = coord_x_max - margin_x
        y_min = coord_y_min + margin_y
        y_max = coord_y_max - margin_y
        print(f"[st_region_query] 自动调整范围为: X[{x_min:.0f},{x_max:.0f}] Y[{y_min:.0f},{y_max:.0f}]", file=sys.stderr)

    # 2. 筛选区域内的 spots
    mask = (
        (coords[:, 0] >= x_min) & (coords[:, 0] <= x_max) &
        (coords[:, 1] >= y_min) & (coords[:, 1] <= y_max)
    )
    region_adata = adata[mask]

    n_spots_in_region = region_adata.n_obs
    if n_spots_in_region == 0:
        return {
            "region": {"x_range": [x_min, x_max], "y_range": [y_min, y_max]},
            "n_spots_in_region": 0,
            "message": "区域内没有 spots",
            "coord_info": {"data_x_range": [coord_x_min, coord_x_max], "data_y_range": [coord_y_min, coord_y_max]},
        }

    # 3. 查询指定基因或 Top N 高表达基因
    if hasattr(region_adata.X, "toarray"):
        X = region_adata.X.toarray()
    else:
        X = region_adata.X

    gene_expression = {}

    if gene_list:
        # 用户指定的基因
        for gene in gene_list:
            if gene in region_adata.var_names:
                idx = list(region_adata.var_names).index(gene)
                expr = X[:, idx]
                gene_expression[gene] = {
                    "mean": round(float(np.mean(expr)), 4),
                    "std": round(float(np.std(expr)), 4),
                    "pct_expressed": round(float(np.sum(expr > 0) / n_spots_in_region * 100), 2),
                }
    else:
        # 自动选 Top N 高表达基因
        mean_expr = np.mean(X, axis=0)
        top_indices = np.argsort(mean_expr)[::-1][:top_n_genes]
        for idx in top_indices:
            gene = str(region_adata.var_names[idx])
            gene_expression[gene] = {
                "mean": round(float(mean_expr[idx]), 4),
                "pct_expressed": round(float(np.sum(X[:, idx] > 0) / n_spots_in_region * 100), 2),
            }

    result = {
        "region": {"x_range": [x_min, x_max], "y_range": [y_min, y_max]},
        "n_spots_in_region": int(n_spots_in_region),
        "gene_expression": gene_expression,
    }

    print(f"[st_region_query] 区域内 {n_spots_in_region} spots, {len(gene_expression)} 基因",
          file=sys.stderr)
    return result


def main():
    parser = argparse.ArgumentParser(description="空间区域表达量查询")
    parser.add_argument("--data_path", type=str, required=True)
    parser.add_argument("--x_min", type=float, required=True)
    parser.add_argument("--x_max", type=float, required=True)
    parser.add_argument("--y_min", type=float, required=True)
    parser.add_argument("--y_max", type=float, required=True)
    parser.add_argument("--gene_list", type=str, default=None,
                        help="逗号分隔的基因列表")
    parser.add_argument("--top_n_genes", type=int, default=5)
    args = parser.parse_args()

    if not os.path.exists(args.data_path):
        alt = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data",
                           os.path.basename(args.data_path))
        if os.path.exists(alt):
            args.data_path = alt
        else:
            print(json.dumps({"error": f"文件不存在: {args.data_path}"}))
            sys.exit(1)

    gene_list = None
    if args.gene_list:
        gene_list = [g.strip() for g in args.gene_list.split(",")]

    result = query_region(
        args.data_path,
        args.x_min, args.x_max,
        args.y_min, args.y_max,
        gene_list,
        args.top_n_genes,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
