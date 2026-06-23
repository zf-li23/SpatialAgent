#!/usr/bin/env python3
# ============================================================
# st_cell_comm — 细胞通讯分析（配体-受体互作）
# 复用: omicverse Commot 集成 / LIANA
# 简化版：基于空间邻域的基因共表达相关性
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


# 已知配体-受体对（简化参考数据库）
KNOWN_LR_PAIRS = [
    ("Lgals9", "Cd44"), ("Lgals9", "Havcr2"),
    ("Apoe", "Lrp1"), ("Apoe", "Ldlr"),
    ("Ccl5", "Ccr5"), ("Ccl5", "Ccr1"),
    ("Cxcl12", "Cxcr4"), ("Cxcl12", "Cxcr7"),
    ("Il16", "Cd4"),
    ("Vegfa", "Flt1"), ("Vegfa", "Kdr"),
    ("Tgfb1", "Tgfbr1"), ("Tgfb1", "Tgfbr2"),
    ("Egf", "Egfr"),
    ("Fgf2", "Fgfr1"),
    ("Wnt3a", "Fzd1"),
    ("Bmp2", "Bmpr1a"),
    ("Sema3a", "Nrp1"),
    ("Ephb2", "Ephb4"),
    ("Notch1", "Dll1"), ("Notch1", "Jag1"),
    ("Hbegf", "Erbb4"),
    ("Pdgfa", "Pdgfra"),
    ("Igf1", "Igf1r"),
    ("Hgf", "Met"),
    ("Cntf", "Cntfr"),
    ("Bdnf", "Ntrk2"),
    ("Ntf3", "Ntrk3"),
    ("Gdnf", "Gfra1"),
]


def analyze_cell_communication(data_path: str, method: str = "correlation") -> dict:
    """分析细胞通讯"""

    print(f"[st_cell_comm] 正在读取: {data_path}", file=sys.stderr)
    adata = sc.read_h5ad(data_path)
    adata.var_names_make_unique()

    # 尝试使用 LIANA
    if method == "liana":
        try:
            result = _run_liana(adata)
            if result:
                return result
        except Exception as e:
            print(f"[st_cell_comm] LIANA 不可用 ({e})，回退到相关性方法", file=sys.stderr)

    # 回退方案：基于空间邻域的共表达相关性
    return _run_correlation(adata)


def _run_liana(adata) -> dict | None:
    """使用 LIANA 进行分析"""
    try:
        import liana as li
        # LIANA 需要 cell type labels，尝试从 leiden 聚类获取
        if "leiden" not in adata.obs:
            sc.pp.neighbors(adata)
            sc.tl.leiden(adata, resolution=0.5)

        li.mt.rank_aggregate(
            adata,
            groupby="leiden",
            resource_name="consensus",
            expr_prop=0.1,
            verbose=True,
        )

        # 提取结果
        lr_df = adata.uns["liana_res"]
        top_pairs = []
        for _, row in lr_df.head(10).iterrows():
            top_pairs.append({
                "ligand": str(row["ligand_complex"]),
                "receptor": str(row["receptor_complex"]),
                "score": round(float(row.get("magnitude_rank", row.get("lrscore", 0))), 4),
            })

        return {
            "n_significant_pairs": int(len(lr_df)),
            "top_interactions": top_pairs,
            "method": "liana",
        }
    except Exception:
        return None


def _run_correlation(adata) -> dict:
    """基于共表达相关性的简化配体-受体分析"""

    # 1. 过滤已知配体-受体对中在数据中存在的基因
    # 注意：基因名可能是大写/小写/Ensembl 格式，做不区分大小写匹配
    available_genes = set(adata.var_names)
    available_upper = {g.upper(): g for g in available_genes}

    valid_pairs = []
    for lig, rec in KNOWN_LR_PAIRS:
        lig_match = lig if lig in available_genes else available_upper.get(lig.upper())
        rec_match = rec if rec in available_genes else available_upper.get(rec.upper())
        if lig_match and rec_match:
            valid_pairs.append((lig_match, rec_match))

    # 若无已知配对，基于高变基因做全对全相关性
    if not valid_pairs:
        print("[st_cell_comm] 无已知LR配对，基于Top100高变基因做共表达分析", file=sys.stderr)
        return _run_correlation_top_genes(adata)

    # 2. 计算表达矩阵
    if hasattr(adata.X, "toarray"):
        X = adata.X.toarray()
    else:
        X = adata.X

    gene_to_idx = {g: i for i, g in enumerate(adata.var_names)}

    # 3. 计算每个配体-受体对的 Spearman 相关性
    from scipy.stats import spearmanr

    pair_scores = []
    for lig, rec in valid_pairs:
        lig_idx = gene_to_idx[lig]
        rec_idx = gene_to_idx[rec]
        lig_expr = X[:, lig_idx]
        rec_expr = X[:, rec_idx]

        # 只考虑两者都有表达的 spots
        mask = (lig_expr > 0) & (rec_expr > 0)
        if mask.sum() < 10:
            continue

        corr, pval = spearmanr(lig_expr[mask], rec_expr[mask])
        pair_scores.append({
            "ligand": lig,
            "receptor": rec,
            "score": round(float(abs(corr)), 4),
            "p_value": round(float(pval), 6),
            "n_spots_coexpressed": int(mask.sum()),
        })

    # 4. 排序
    pair_scores.sort(key=lambda x: x["score"], reverse=True)

    n_sig = sum(1 for p in pair_scores if p["p_value"] < 0.05)

    result = {
        "n_significant_pairs": n_sig,
        "top_interactions": pair_scores[:15],
        "method": "spearman_correlation",
        "total_pairs_checked": len(valid_pairs),
    }

    print(f"[st_cell_comm] 完成: 发现 {n_sig} 个显著互作对",
          file=sys.stderr)
    return result


def _run_correlation_top_genes(adata) -> dict:
    """基于 Top 100 高变基因的共表达相关性分析"""
    from scipy.stats import spearmanr

    sc.pp.highly_variable_genes(adata, n_top_genes=100, flavor="seurat_v3")
    adata = adata[:, adata.var.highly_variable].copy()

    if hasattr(adata.X, "toarray"):
        X = adata.X.toarray()
    else:
        X = adata.X

    n_genes = adata.n_vars
    pair_scores = []

    # 限制配对数量：取前 30 个高变基因做配对
    top_n = min(30, n_genes)
    for i in range(top_n):
        for j in range(i + 1, top_n):
            lig_expr = X[:, i]
            rec_expr = X[:, j]
            mask = (lig_expr > 0) & (rec_expr > 0)
            if mask.sum() < 20:
                continue
            corr, pval = spearmanr(lig_expr[mask], rec_expr[mask])
            pair_scores.append({
                "ligand": str(adata.var_names[i]),
                "receptor": str(adata.var_names[j]),
                "score": round(float(abs(corr)), 4),
                "p_value": round(float(pval), 6),
                "n_spots_coexpressed": int(mask.sum()),
            })

    pair_scores.sort(key=lambda x: x["score"], reverse=True)
    n_sig = sum(1 for p in pair_scores if p["p_value"] < 0.05)

    return {
        "n_significant_pairs": n_sig,
        "top_interactions": pair_scores[:15],
        "method": "top_hvg_correlation",
        "total_pairs_checked": len(pair_scores),
    }


def main():
    parser = argparse.ArgumentParser(description="细胞通讯分析")
    parser.add_argument("--data_path", type=str, required=True)
    parser.add_argument("--method", type=str, default="correlation")
    args = parser.parse_args()

    if not os.path.exists(args.data_path):
        alt = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data",
                           os.path.basename(args.data_path))
        if os.path.exists(alt):
            args.data_path = alt
        else:
            print(json.dumps({"error": f"文件不存在: {args.data_path}"}))
            sys.exit(1)

    result = analyze_cell_communication(args.data_path, args.method)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
