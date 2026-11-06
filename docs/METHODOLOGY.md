# itol-cli 绘图方法论（2026-11-06，v2 文献锚定版）

> 定位：同行已无参考方向。本文档把「什么是好的树图」编码成 itol-cli 的方法论根基——全部洞见锚定真实文献/官方规格。
> 五大问题：绘图方法论 / 图片迭代方法论 / 绘图美学参数 / 树类型×信息 / 信息密度最大化。

---

## 一、绘图方法论：树图是「论证一个进化主张」

**主张决定注解，不是数据决定注解。** 这不是自造概念——

- **Rougier, Droettboom & Bourne 2014, "Ten Simple Rules for Better Figures", PLoS Comput Biol 10(9):e1003833**：
  - Rule 2 *Identify Your Message*：图为表达一个明确 message 而存在，message 强导向整图设计。→ itol-cli 第一原理「主张决定注解」的权威背书。**可编码：gen 模板头部强制声明 claim 字段，无 claim 不生成。**
  - Rule 9 *Message Trumps Beauty*：message 和 readability 最重要，美观是 option。→ itol iterate 评分函数里 readability 权重高于 aesthetics。
  - Rule 5 *Do Not Trust the Defaults*：默认值「对任何图都够用、对哪个都不最优」。→ itol-cli 默认值应按「树类型×主张」分场景调优的正当性依据。
  - Rule 3 *Adapt to the Support Medium*：期刊图（可细看）vs 演讲图（一瞥）标准不同。→ 输出 profile（journal/slide/poster）切换全局参数基线。

- **Wilke《Fundamentals of Data Visualization》(O'Reilly) Ch2/Ch4**：
  - 颜色只有三个正当用途：qualitative 区分无序组 / sequential 表数值 / highlight 强调。→ **可编码成颜色用途校验器**：分类→Okabe-Ito qualitative、dN/dS 连续→viridis sequential、±选择压力→红蓝 diverging、强调某支→highlight+余者置灰。数据类型错配（分类数据用连续色）直接报错。

---

## 二、图片迭代方法论：好图是迭代收敛，瓶颈是迭代成本

出版级图是迭代收敛出来的。把用户的自评分美学循环固化成命令。

**迭代闭环**：`生成 N 变体 → 对照标准评分 → 选最优 → 调参 → 再生成`。

文献锚点：
- **Sandve et al. 2013 "Ten Simple Rules for Reproducible Computational Research" (PLoS CB 10(9):e1003285)**：Rule 2 手工操作不可复现、Rule 6 记录随机种子、Rule 7 图背后的原始数据+绘图代码必须一并存档、Rule 8 输出分层。→ **replay 的学术规范依据**：itol replay 自动写 sidecar（参数+输入 hash+版本），不做 sidecar 不算可复现。
- **Snakemake（Mölder 2021）**：可复现=workflow 定义+参数显式+版本锁定+一键 re-run。
- **Vega-Lite（Satyanarayan 2017）**：图即数据（声明式 spec），改一个字段就是一个变体，变体 diff 可读可审。→ itol 的 annotation/display 参数做成**声明式 YAML spec**，iterate 接收结构化 patch。
- **Papermill**：同一模板×不同参数=N 个变体。→ `itol iterate --sweep sweep.yaml`（参数网格写 YAML 不是 CLI flag）。
- **matplotlib.compare**：像素级回归测试——图是可测试的。→ `itol replay --verify` 与 baseline 做 perceptual diff。
- **ggtree（Yu, treedata-book）**：传统树图工具产出的图不可复现，必须 Illustrator 后加工；ggtree 的解=ggplot2 图层叠加语法（图=代码可重建的层叠结构）。→ **iterate 的心智模型=ggplot 的 `+`**：base spec + 层 patch，变体=声明式 diff。

**ColorBrewer（Harrower & Brewer 2003）**：配色是约束求解（数据类型+类别数+colorblind/print 约束→配色方案），把「好不好看」翻译成「满不满足可验证约束」。→ iterate 的美学默认=约束检查器（colorblind 模拟 + WCAG 对比度 ≥4.5 + print-friendly），失败给具体修复建议。

---

## 三、绘图美学参数经验（期刊规格 + 色板，全部实证）

### 期刊硬性规格（官方页实测）

| 来源 | 关键参数 | itol-cli 编码 |
|:---|:---|:---|
| **PLOS ONE** figure 要求 | 300-600 dpi；宽 ≤5.2in（单栏）；**图内文字仅限 Arial/Times/Symbol，8-12pt**；TIFF/EPS，RGB | `--font-size` 钳制 8-12pt 告警越界；宽度预设 single-column/full-page；字体白名单 |
| **Nature** 终版 | 版心 90mm(单栏)/180mm(双栏)，高 ≤170mm；**此尺寸下字号 5-7pt**；统一 Arial/Helvetica；**禁 rainbow/jet，避免红绿对比**；矢量层 | 字号随物理图幅缩放（pt 是绝对单位，叶标签字号=目标物理宽度÷叶数）；`--journal nature` 预设 |
| **Elsevier** | 图内文字 7pt（上下标 ≥6pt）；**line art（树图属此类）1000 dpi**；版心 90/140/190mm；色盲可达性 5 条 | 树=line art → `--dpi 1000` 印刷级默认（或矢量免 dpi）；字号下限 6/7pt；三档版心预设 |

### 色板（色盲+打印双安全，官方）

| 色板 | 参数 | itol-cli 编码 |
|:---|:---|:---|
| **Okabe-Ito CUD**（色盲设计原文） | 8 色：black/orange #E69F00/sky blue #56B4E9/bluish green #009E73/yellow #F0E442/blue #0072B2/vermillion #D55E00/reddish purple #CC79A7；**冗余编码**（颜色+形状双通道，禁纯颜色单通道）；直接标注>分离图例；色编码对象要粗要大；3 个白人男审稿人至少 1 人色盲概率 22% | 默认分类色板=Okabe-Ito（≤8 组）；>8 组告警+建议合并/shape 编码；支持度符号默认颜色+大小双编码 |
| **Paul Tol**（SRON 官方，CIEDE2000 ΔE00 设计） | bright 7 色 / **muted 9 色（定性色板实际上限）** / high-contrast 3 色 / dark 11 色；**>9 类官方建议换 banded sequential** | 定性色板分档：≤7 Tol-bright / 8-9 Tol-muted 或 Okabe-Ito / >9 自动切策略+告警"类别过多" |

### iTOL 官方显示选项（可编码默认值直接来源）
- 6 布局：Rectangular/Slanted/Circular/Curved/Unrooted equal-angle/equal-daylight（equal-daylight 减拥挤，引 doi:10.1109/tcbb.2007.1046）
- Circular 默认 arc=350°；叶排序默认小叶群置顶（阶梯状更好看）
- bootstrap 4 种可视化：Symbol（大小线性）/Text/Color 渐变/**Width（枝宽映射）**
- 文字标签可加背景框提高可读性

---

## 四、各种树要展现什么信息（树类型×主张×注解集）

| 树类型 | 主张 | 主注解 | 支撑 | 别加 | 依据 |
|:---|:---|:---|:---|:---|:---|
| **基因家族树**（主战场） | 亚家族划分/扩张 | 亚家族色带（COLORSTRIP） | 支持度、物种来源色、结构域（DOMAINS）、表达热图（HEATMAP） | 别堆 5+ 层 | ggtree Ch7 facet_plot |
| **物种树/chronogram** | 分歧时间+拓扑可信度 | 时间轴 + node bars（95% HPD）+ posterior | 化石标定点高亮 | bootstrap（BEAST 用 posterior） | FigTree/BEAST 管线 |
| **基因树vs物种树调和** | 复制/转移/丢失事件史 | 节点事件符号（D红方块/T箭头/L灰虚线）+ 物种树背景骨架 | 事件计数/支 | bootstrap 次要 | Notung/ALE 管线 |
| **系统发育地理/群体树** | 谱系地理/时间扩散聚类 | 时间轴（tip-dated）+ 离散性状着色（地点→枝+叶）+ posterior | 地图面板（另图） | 结构域/表达/亚家族 | MASCOT/Nextstrain Auspice |

**itol-cli 编码**：gen 场景从「注解类型」升级为「树类型×主张」预设（gene-family-expansion / species-tree-timescale / reconciliation / phylogeography）。

---

## 五、信息密度最大化（信噪比约束下）

**Tufte 1983《The Visual Display of Quantitative Information》**：data-ink ratio——改进图的方向是「移除」而非「添加」；但 Stephen Few 提醒适度冗余（双编码）常更有效。

**可编码的密度护栏**：
1. **视觉通道预算表**（Wilke Ch2 + iTOL 官方）：color/shape/size/text/width 每通道最多绑 1 个变量；单图 ≤5 个 scale 是清晰上限。lint 校验通道冲突。
2. **共享叶轴对齐**（ggtree facet / patchwork）：树+对齐数据面板共享叶序轴。面板宽度/间距（gheatmap offset）是一等参数；热图 width=0.2-0.5 相对树宽。
3. **大树的可读性拐点**（Phylo.io, MBE 2016）：**几十 tip 是并排比较的可读性拐点**；大树策略=交互缩放+子树折叠+**自动最优 rooting 与叶序对齐**。
4. **超大树=密度交给缩放层级**（Taxonium, eLife 2022）：overview 只画骨架，zoom-in 才渲染局部。→ 静态导出对应「overview 层」，>N tip 默认不画全标签只画骨架+高亮关键支。

**iter/数据墨比指标**：iterate 每轮 diff 统计「新增墨水/新增信息」比值作为质量指标。

---

## 六、落地为 itol-cli 的方法论编码（突破方向，护城河）

| # | 方法论 | itol-cli 落地 | 文献锚 |
|:--|:--|:--|:--|
| 1 | 主张决定注解 | gen 模板强制 claim 字段 + `itol plan --claim` | Rougier R2 |
| 2 | 迭代闭环 | `itol iterate`（sweep YAML→变体→约束评分）+ replay sidecar | Vega-Lite/Papermill/Sandve |
| 3 | 美学参数默认 | 字号随物理图幅缩放；定性色板分档（≤7 Tol/8-9 OI/>9 告警）；色盲模拟+WCAG 校验 | PLOS/Nature/Elsevier/ColorBrewer |
| 4 | 树类型×主张 | gen 场景升级为预设（gene-family/species-tree/reconciliation/phylogeography） | ggtree/FigTree/Notung/Auspice |
| 5 | 密度护栏 | lint/plan 校验通道预算（≤5 scale、每通道1变量）+ 叶数阈值 + 长枝截断建议 | Wilke/iTOL/Phylo.io |
| 6 | 可读性硬约束 | render 前查叶数×字号×图幅→报「标签将不可读」；默认 ladderize/叶序优化/scale bar | ggtree/iTOL |

**核心转向：itol-cli 从「iTOL 的壳」升级为「编码了树图方法论的工具」——它知道什么是好图，并默认把你往好图推。** 这是同行（itolapi/PyiTOL/itol.toolkit）都没占的生态位。
