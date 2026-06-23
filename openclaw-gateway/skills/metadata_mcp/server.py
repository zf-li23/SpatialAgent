#!/usr/bin/env python3
# ============================================================
# Metadata MCP Server — 扫描 data/ 目录，暴露数据集信息
# 参考: Biomni 的 env_desc 数据湖感知思想
# ============================================================

import sys
import os
import json
from pathlib import Path

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
DATA_DIR = os.path.abspath(DATA_DIR)


def scan_h5ad(path: str) -> dict:
    """读取 .h5ad 文件的元数据"""
    try:
        import anndata
        adata = anndata.read_h5ad(path, backed="r")
        info = {
            "path": path,
            "filename": os.path.basename(path),
            "shape": list(adata.shape),
            "n_obs": adata.n_obs,
            "n_vars": adata.n_vars,
            "obs_columns": list(adata.obs.columns),
            "obsm_keys": list(adata.obsm.keys()) if hasattr(adata, 'obsm') else [],
            "has_spatial": "spatial" in adata.obsm if hasattr(adata, 'obsm') else False,
        }
        adata.file.close()
        return info
    except Exception as e:
        return {
            "path": path,
            "filename": os.path.basename(path),
            "error": str(e),
        }


def discover():
    """扫描 DATA_DIR 下的所有数据文件"""
    results = {
        "data_dir": DATA_DIR,
        "datasets": [],
    }

    if not os.path.isdir(DATA_DIR):
        results["error"] = f"数据目录不存在: {DATA_DIR}"
        return results

    for entry in sorted(os.listdir(DATA_DIR)):
        full_path = os.path.join(DATA_DIR, entry)

        if entry.endswith(".h5ad"):
            info = scan_h5ad(full_path)
            results["datasets"].append(info)

        elif entry.endswith(".csv"):
            results["datasets"].append({
                "path": full_path,
                "filename": entry,
                "type": "csv",
            })

        elif entry.endswith(".h5") and not entry.endswith(".h5ad"):
            results["datasets"].append({
                "path": full_path,
                "filename": entry,
                "type": "h5",
            })

    results["n_datasets"] = len(results["datasets"])
    return results


if __name__ == "__main__":
    result = discover()
    print(json.dumps(result, indent=2, ensure_ascii=False))
