# 示例数据说明

## visium_lymph_node.h5ad

- **来源**: `scanpy.datasets.visium_sge()` 模拟数据
- **组织**: Human Lymph Node (模拟)
- **Spots**: 4,035
- **Genes**: 36,601
- **格式**: AnnData (h5ad)

## 预期用途

用于快速验证 SpatialAgent 各技能的基础功能：
1. `st_preprocess` — 数据加载与 QC
2. `st_spatial_pattern` — 空间可变基因分析
3. `st_region_query` — 区域表达量查询
4. `st_trajectory` — 空间轨迹推断
5. `st_cell_comm` — 细胞通讯分析

## 添加更多数据

将 `.h5ad` 文件放入此目录，MCP 服务器会自动扫描并注册到可用数据集列表。
