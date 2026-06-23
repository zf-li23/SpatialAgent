#!/usr/bin/env python3
# ============================================================
# st_trajectory — 空间轨迹推断与伪时间分析
# 复用: stlearn (pseudotime) / scanpy (PAGA + DPT)
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


def compute_trajectory(data_path: str, root_index: int | None = None) -> dict:
    """计算空间伪时间和轨迹"""

    print(f"[st_trajectory] 正在读取: {data_path}", file=sys.stderr)
    adata = sc.read_h5ad(data_path)
    adata.var_names_make_unique()

    n_spots = adata.n_obs

    # 1. 预处理
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sc.pp.highly_variable_genes(adata, n_top_genes=2000, flavor="seurat_v3")
    adata = adata[:, adata.var.highly_variable].copy()

    # 2. PCA + 邻域图
    sc.pp.scale(adata, max_value=10)
    sc.tl.pca(adata, n_comps=30, svd_solver="arpack")
    sc.pp.neighbors(adata, n_neighbors=15, n_pcs=30)

    # 3. UMAP (用于可视化参考)
    sc.tl.umap(adata)

    # 4. PAGA 图
    sc.tl.leiden(adata, resolution=0.5)
    sc.tl.paga(adata)

    # 5. 扩散伪时间 (DPT)
    if root_index is None:
        # 自动选择根节点：选 Leiden 0 簇的中心
        cluster_0_mask = adata.obs["leiden"] == "0"
        if cluster_0_mask.sum() > 0:
            root_index = int(np.where(cluster_0_mask)[0][0])
        else:
            root_index = 0

    adata.uns["iroot"] = root_index
    sc.tl.diffmap(adata)
    sc.tl.dpt(adata)

    # 6. 提取结果
    pseudotime = adata.obs["dpt_pseudotime"].values

    # 按伪时间分 3 个分支（简化版）
    pt_min, pt_max = float(pseudotime.min()), float(pseudotime.max())
    third = (pt_max - pt_min) / 3
    branches = []
    for pt in pseudotime:
        if pt < pt_min + third:
            branches.append("early")
        elif pt < pt_min + 2 * third:
            branches.append("mid")
        else:
            branches.append("late")

    # 构建 spots 列表（采样 500 个避免过大）
    sample_indices = np.linspace(0, n_spots - 1, min(n_spots, 500), dtype=int)
    spots = []
    for i in sample_indices:
        spots.append({
            "index": int(i),
            "pseudotime": round(float(pseudotime[i]), 4),
            "branch": branches[i],
            "leiden": str(adata.obs["leiden"].values[i]),
        })

    # 统计分支
    from collections import Counter
    branch_counts = dict(Counter(branches))

    result = {
        "n_spots": n_spots,
        "pseudotime_range": [pt_min, pt_max],
        "n_branches": 3,
        "root_spot_index": root_index,
        "branch_distribution": branch_counts,
        "spots_sample": spots,
    }

    print(f"[st_trajectory] 完成: 伪时间范围 [{pt_min:.3f}, {pt_max:.3f}]",
          file=sys.stderr)
    return result


def main():
    parser = argparse.ArgumentParser(description="空间轨迹推断")
    parser.add_argument("--data_path", type=str, required=True)
    parser.add_argument("--root_index", type=int, default=None)
    args = parser.parse_args()

    if not os.path.exists(args.data_path):
        alt = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data",
                           os.path.basename(args.data_path))
        if os.path.exists(alt):
            args.data_path = alt
        else:
            print(json.dumps({"error": f"文件不存在: {args.data_path}"}))
            sys.exit(1)

    result = compute_trajectory(args.data_path, args.root_index)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
