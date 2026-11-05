# iTOL 深挖第四轮成果（2026-11-06，hack4 五代理，超时但增量落盘保住）

> 配套：ATTACK_SURFACE.md / BACKEND_ARCHITECTURE.md / EXPORT_PARAMS.md / RENDER_INTERNALS.md / HIDDEN_PARAMS.md。

## 🏆 新发现 1：loadTree.cgi —— 免费拉公开树完整结构+元数据（dataload）

- `POST /ajax/loadTree.cgi`，data=`tree=<tree_id>`（可选 `batch=1&ds=<ids>`）
- **公开树免认证**（实测 mini 树 200，CT text/x-json）
- 响应顶层键：`node`（节点索引表，含 par/kids/bl/lf）/ `param`（tree_height/root/has_brl/min/max_bootstrap）/ `info`（names/newIDs/label_color/style/background/node_metadata/node_style/tree_name/datasets/views/display_defaults）/ `leaf`（叶序）
- **价值**：可直接拉公开树的完整结构+元数据做分析/转 Newick，免认证——可成为 `itol fetch`/`itol info` 新命令

## 🏆 新发现 2：exportText.cgi 全参数（exporttext）

文本/颜色/折叠导出端点（**同步 AJAX，非队列**），两条路径：
- **路径 A（fmt=colors|collapse）**：id/nm/fmt + rt + pr(prune 保留叶) + ndl/rot/cdl/nmv/col（节点状态 JSON）+ st(node_style)/fs(font_style)/lc(label_color)/lb(label_background)/rng(ranges)
- **路径 B（文本 newick/nexus/phyloxml）**：id/nm/fmt + intNd（内部节点导出开关）+ mFmt（元数据格式）+ sort + rot/rt/pr/ndl/cdl/nmv
- 用途：免 SVG 的文本/注解导出；export.cgi（位图/矢量）走队列，exportText.cgi 走同步

## 新发现 3：视图状态逐键解码批次1（vsdecode）

l1I1l 197 键开始解码（控件 change handler 直证）。已解锚点：

| 键 | 语义 | 键 | 语义 |
|---|---|---|---|
| III111I | 显示模式(1矩/2环/3无根) | lIlI | 字体族(Arial) |
| lII1 | 字号(20) | l11IllI1 | 字号锁定flag |
| IIlI | 默认标签色(#000) | lI1I1l | 标签位移px |
| lIl1llII | 枝线宽(1) | l1IIIIll | 默认枝色(#000) |
| l1IIl | 虚线宽系数(.3) | l11I | 虚线色(#aaa) |
| III11/Il1Illl/lI1lll | 三模式旋转角 | l1l1IlI | 曲线枝开关 |

**重渲函数 = `I1llII1l()`**（改键后调它即可重绘）→ `itol render --param` 可行的基础

## 新发现 4：专用导入端点（importers）

- **processQZA.cgi**：QIIME2 .qza 服务端处理（FormData 上传）
- **assign_tax.cgi 系列（4 个）**：免费自动分类学注解！`assign_tax.cgi` 只要 `tree=<id>`（叶标签是 NCBI taxid 即可）→ 自动 NCBI 分类注解；GTDB 版同理；`assign_tax_from_anno.cgi` 从已有注释提分类
- **parseTanglegram.cgi**：tanglegram 数据集解析
- TAXONOMY 型数据集格式：TAXONOMY_TYPE(NCBI|GTDB) + LABEL_FORMAT(1-5) + REPLACE_LEAF_LABELS

## 新发现 5：annotation editor（editor）

- itoleditor.letunic.com = 官方注解编辑器（Excel/LibreOffice/Google Sheets）
- `annoOnly` 三类注解（Branch/label style、Connections、Protein domains）**网页 UI 建不了，只能走 editor 写回**——CLI 要覆盖这三类需挖 editor 的写回 API（待续）

## 本轮对 itol-cli 的可执行增量
1. `itol fetch`/`itol info`（loadTree.cgi 免认证拉树结构+元数据）——新增命令候选
2. `assign_tax.cgi` 免费自动分类注解——新增能力候选
3. exportText.cgi 全参数 → 扩展 export 命令
4. 视图状态键映射 → `itol render --param` 的基础（重渲函数 I1llII1l 已定位）
