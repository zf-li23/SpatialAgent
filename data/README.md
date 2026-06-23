# 示例数据说明

## cosmx_combined.h5ad

- **来源**: GSE263791 — NanoString CosMX 空间转录组数据
- **样本**: ID61-ID62 (S10) + ID67-ID68 (S18)，合并
- **技术**: CosMX (NanoString)，靶向基因面板
- **Cells**: 43,117 (21,713 + 21,404)
- **Genes**: 960 (靶向基因面板)
- **格式**: AnnData (h5ad)
- **空间坐标**: 真实细胞质心坐标 (CenterX/Y_global_px，来自 metadata)
- **矩阵密度**: 37%（靶向面板正常高密度）
- **表达值范围**: 0 ~ 3,678 (raw counts)
- **大小**: 162 MB

### 为什么原始 tar 是 2GB 而 h5ad 只有 162MB？

这是正常的，因为 tar 包包含大量**分析非必需**数据：

| 内容 | 大小 | 说明 |
|:---|:---|:---|
| `tx_file.csv.gz` (×2) | **1.26 GB** | 7817万条单独转录本坐标——空间组学的"原始底片"，聚合到 cell 后不再需要 |
| `CellOverlay/CellComposite` (×2) | **~640 MB** | 高分辨组织荧光图像——仅用于可视化展示 |
| 表达矩阵+元数据 | **~15 MB** | 这才是分析核心 |
| 其他 | ~100 MB | 标签图、隔室标签等 |

**h5ad 只存分析必需**：43,117 cells × 960 genes 的计数矩阵。float32 理论大小 = 43,117 × 960 × 4 = **158 MB**，加元数据和 hdf5 开销 ≈ **162 MB** ✓

## 可复现性：从头获取数据

```bash
# 1. 下载原始数据 (约 2.0 GB)
wget -O GSE263791_RAW.tar "https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE263791&format=file"

# 2. 解压
mkdir -p GSE263791 && tar -xf GSE263791_RAW.tar -C GSE263791

# 3. 重建 h5ad（需要以下 Python 脚本）
cd GSE263791 && python build_anndata.py
```

构建脚本 `build_anndata.py` 位于 `data/GSE263791/build_anndata.py`，它会：
- 读取两个样本的 `exprMat_file.csv.gz`（表达矩阵）
- 从 `metadata_file.csv.gz` 提取细胞质心坐标 (`CenterX/Y_global_px`)
- 按 `(fov, cell_ID)` 复合键对齐数据
- 输出 `cosmx_combined.h5ad`（43,117 cells × 960 genes）
- 预计算 PCA + UMAP + Leiden 聚类

## 原始数据

原始的 `GSE263791_RAW.tar` (2.0 GB) 位于 `data/`，已解压至 `data/GSE263791/`。

