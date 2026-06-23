#!/usr/bin/env python3
# ============================================================
# st_spatial_pattern — 空间可变基因 (SVG) 分析
# 复用: squidpy (spatial_neighbors + spatial_autocorr)
#       stlearn 的空间模式函数作为参考
# ============================================================

import sys
import os
import json
import argparse
import warnings

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "repos")
sys.path.insert(0, REPO_ROOT)

import scanpy as sc
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


def find_svg(data_path: str, method: str = "morans_i", n_top_genes: int = 10) -> dict:
    """识别空间可变基因"""

    print(f"[st_spatial_pattern] 正在读取: {data_path}", file=sys.stderr)
    adata = sc.read_h5ad(data_path)
    adata.var_names_make_unique()

    n_spots = adata.n_obs

    # 预过滤低表达基因 + 选高变基因加速（Moran's I 排列检验很慢）
    sc.pp.filter_genes(adata, min_cells=50)
    sc.pp.highly_variable_genes(adata, n_top_genes=500, flavor="seurat_v3")
    adata = adata[:, adata.var.highly_variable].copy()
    print(f"[st_spatial_pattern] 筛选后: {adata.n_vars} 个高变基因", file=sys.stderr)

    if method == "morans_i":
        try:
            import squidpy as sq

            # 构建空间邻域图
            print("[st_spatial_pattern] 构建空间邻域图...", file=sys.stderr)
            sq.gr.spatial_neighbors(adata, coord_type="generic", delaunay=False, n_neighs=6)

            # 计算 Moran's I
            print("[st_spatial_pattern] 计算 Moran's I...", file=sys.stderr)
            sq.gr.spatial_autocorr(
                adata,
                mode="moran",
                n_perms=100,
                n_jobs=1,  # 单核避免资源问题
            )

            # 提取结果
            moran_df = adata.uns["moranI"]
            moran_df = moran_df.sort_values("I", ascending=False)

            top_genes = []
            for i, (gene, row) in enumerate(moran_df.head(n_top_genes).iterrows()):
                top_genes.append({
                    "gene": str(gene),
                    "moran_i": round(float(row["I"]), 4),
                    "p_value": round(float(row.get("pval", row.get("p-value", 0))), 6),
                })

            n_sig = int((moran_df["pval"] < 0.05).sum() if "pval" in moran_df.columns else len(moran_df))

            result = {
                "top_svg_genes": top_genes,
                "n_significant_genes": n_sig,
                "method": "morans_i",
                "n_spots": n_spots,
            }

        except ImportError:
            # 回退到基于方差的方法
            print("[st_spatial_pattern] squidpy 不可用，使用方差方法", file=sys.stderr)
            result = _fallback_svg(adata, n_top_genes, n_spots)

    else:
        result = _fallback_svg(adata, n_top_genes, n_spots)

    print(f"[st_spatial_pattern] 完成: 发现 {result['n_significant_genes']} 个 SVG",
          file=sys.stderr)
    return result


def _fallback_svg(adata, n_top_genes: int, n_spots: int) -> dict:
    """回退方案：基于基因表达方差选择高变基因"""
    from scipy.stats import zscore

    # 计算每个基因的表达方差
    if hasattr(adata.X, "toarray"):
        X = adata.X.toarray()
    else:
        X = adata.X

    variances = np.var(X, axis=0)
    var_indices = np.argsort(variances)[::-1][:n_top_genes]

    top_genes = []
    for rank, idx in enumerate(var_indices):
        top_genes.append({
            "gene": str(adata.var_names[idx]),
            "variance_rank": rank + 1,
            "variance": round(float(variances[idx]), 4),
        })

    return {
        "top_svg_genes": top_genes,
        "n_significant_genes": n_top_genes,
        "method": "variance_fallback",
        "n_spots": n_spots,
    }


def main():
    parser = argparse.ArgumentParser(description="空间可变基因分析")
    parser.add_argument("--data_path", type=str, required=True)
    parser.add_argument("--method", type=str, default="morans_i")
    parser.add_argument("--n_top_genes", type=int, default=10)
    args = parser.parse_args()

    if not os.path.exists(args.data_path):
        alt = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data",
                           os.path.basename(args.data_path))
        if os.path.exists(alt):
            args.data_path = alt
        else:
            print(json.dumps({"error": f"文件不存在: {args.data_path}"}))
            sys.exit(1)

    result = find_svg(args.data_path, args.method, args.n_top_genes)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
