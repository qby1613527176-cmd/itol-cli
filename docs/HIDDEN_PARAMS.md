# iTOL 深挖第三轮成果（2026-11-05，hack3 五代理，超时但增量落盘保住）

> 配套：ATTACK_SURFACE.md（端点面）、BACKEND_ARCHITECTURE.md（后端）、EXPORT_PARAMS.md（batch 参数）、RENDER_INTERNALS.md（渲染机制）。

## 🏆 最大收获 1：数据集隐藏参数 ~200 个（dshidden）

公共头部解析器 `ll1llII`（itol_all.min.js @698371，所有 DATASET_* 共用）**实际读取的键远超官方模板**。官方模板没写但 handler 认的隐藏参数（节选高价值）：

- **色带**：`STRIP_WIDTH` `STRIP_SPACING` `STRIP_BORDER_WIDTH/COLOR` `SHOW_STRIP_LABELS` `STRIP_LABEL_POSITION(top/bottom/center)` `STRIP_LABEL_SIZE_FACTOR` `STRIP_LABEL_COLOR` `STRIP_LABEL_ROTATION` `STRIP_LABEL_SHIFT`
- **图例**：`LEGEND_HORIZONTAL` `LEGEND_POSITION_X/Y` `LEGEND_SCALE` `LEGEND_VISIBLE` `LEGEND_SHAPE_INVERT` `LEGEND_SHAPE_SCALES`（含 12 种形状 RE/HH/HV/EL/DI/TR/TL/PL/PR/PU/PD/OC/GP）
- **标签**：`LABELS_BELOW` `STRAIGHT_LABELS` `ALIGN_TO_TREE` `LABEL_ALIGN_TO_TREE` `ALL_LABEL_ROTATION` `EXTERNAL_LABEL_SHIFT` `LABEL_OUTLINE_WIDTH/COLOR`
- **数据归一化**（热图等）：`DATA_NORMALIZATION(rows)` `NORMALIZATION_TYPE(normal/mean/scaling)` `NORMALIZATION_RANGE` `DISPLAY_VALUES(original/normalized)` `ROUND_VALUES` `AUTO_SCALE` `SCALING_FACTOR` `VALUES_SCI_NOTATION` `VALUE_AUTO_COLOR`
- **值标签**：`SHOW_VALUES` `SHOW_VALUE_LABELS` `VALUE_LABEL_SIZE_FACTOR/ROTATION/SHIFT` `VALUE_AUTO_COLOR`
- **网格/边框**：`HORIZONTAL_GRID` `VERTICAL_GRID` `COMPLETE_BORDER` `BORDER_DASHED` `GRID_WIDTH`
- **连接**：`DEFAULT_CONNECTION_STYLE(dashed/dotted/normal)` `CONNECTION_CURVE` `CONNECTION_MARGIN_LEFT/RIGHT` `CONNECTION_TAIL`
- **范围/括号**：`RANGE_TYPE(box/bracket)` `RANGE_COVER(label/clade/tree)` `BRACKET_STYLE(none/square/curved)` `COVER_LABELS` `COVER_DATASETS`
- **其他**：`HEIGHT_FACTOR` `MARGIN` `SIZE_FACTOR` `LOG_SCALE` `BAR_ZERO` `POLAR_AREA_DIAGRAM` `CUSTOM_COLOR_SCHEME` `UNROOTED_SMOOTH`
- ⚠️ 死参数：`ROTATE_ALIGNED_LABELS`（iTOL 自身 bug，比较 h[1] 而非 h[0]，永不生效）

**全表**：`ll1llII` 解析器实读键约 200 个（完整清单见 /tmp/itol_hack/agent_dshidden.md，已合并进模板引擎参考）。

## 🏆 最大收获 2：export.cgi 队列 = 免费高 DPI 位图路（exportqueue）

`POST /ajax/export.cgi`（JS @843747 实证）参数全录：
| 参数 | 取值 | 作用 |
|---|---|---|
| id | tree_id | 哪棵树 |
| fmt | svg/eps/pdf（矢量）/ **png（唯一位图）** / newick/phyloxml/nexus/colors/collapse（文本） | 输出格式 |
| **dpi** | **0–1000，默认 120** | **位图分辨率——补 batch_downloader 无 dpi 的缺口！** |
| m | 0–100 mm | 边距 |
| a | 0=Screen(可视区) / 1=Full(整树+所有数据集) | 导出范围 |
| nm | 文本 | 导出名 |
| shared | 0=普通 / 1=共享(留存1年) | 共享 |
| q | 客户端序列化的完整 SVG | 渲染内容 |

- 队列制：返回 `{inQueue:位置|-1}` → 每 5s 轮询 `exportQueueCheck.cgi` → `download.cgi?f=` 取件
- 同会话一次只能排一个导出任务
- **结论**：免费账号可经此链出 **1000dpi PNG**——itol-cli 高分辨率位图缺口可补

## 重要发现 3：三类注解只能走编辑器（phylot）

itol_all.min.js 数据集下拉中 `annoOnly` 标记：**Branch/label style、Connections、Protein domains 三类在网页 UI 建不了**，只能经 iTOL annotation editor（itoleditor.letunic.com，Google Sheets/LibreOffice 插件）写入。→ CLI 若要覆盖这三类，需走 editor 通道（待挖其写回 API）。

## 其他
- **视图状态**（vsdecode）：l1I1l 197 键类型分布（颜色~40/布尔~60/数值~60/字符串~20/对象~15）；锚点：III111I=显示模式、lIlI=字体(Arial)、lII1=字号(20)、ll1I11=元数据字段(bootstrap)
- **phyloXML**（phyloxml）：重申前轮结论（分支色/宽/渐变可服务端渲染），未推进
