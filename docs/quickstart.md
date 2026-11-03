# Quickstart — 10 秒上手

```bash
pip install -e .          # 源码安装（发布后 pip install itol-cli）
itol --version            # 版本
itol doctor               # 环境自检（API key/端点存活）
itol templates            # 场景模板库（9 个）
```

## 最小工作流（亚家族着色树）

```bash
# 1. 准备分组表：node_id<TAB>group_name（叶名=树文件叶标签）
printf 'GeneA\tSubfamily_I\nGeneB\tSubfamily_II\n' > groups.tsv

# 2. 生成注解文件
itol gen subfamily groups.tsv -o out/
# → out/itol_tree_colors.txt（枝+标签着色）
# → out/itol_colorstrip.txt（外圈色带+图例）

# 3. 本地校验（手写/AI 修改后必跑）
itol lint out/itol_colorstrip.txt out/itol_tree_colors.txt

# 4. 上传（需 iTOL 标准订阅 + APIkey；无订阅时手动拖进树页即可）
export ITOL_API_KEY=xxx   # userInfo.cgi 生成
itol upload tree.tree out/itol_tree_colors.txt out/itol_colorstrip.txt --project MyProj

# 5. 导出（免认证，公开树按 ID 即可）
itol export <tree_id> --format svg -o tree.svg
# 圆形树：--param display_mode=2；bootstrap 展示：itol gen bootstrap 看参数预设
```

## 关键坑（官方实证）

- 注解文件首行关键字是模板锚（`DATASET_COLORSTRIP`/`TREE_COLORS`…），文件名随意
- 内部节点用 LCA 写法 `ID1|ID2`；叶名含 `|` 会与 LCA 语法撞车（重命名规避）
- 导出无 dpi/宽高参数——要矢量（SVG/PDF/EPS）别要位图高分辨率
- 匿名树注解是客户端级（不存服务端）；程序化挂注解需账号（免费账号或订阅）
