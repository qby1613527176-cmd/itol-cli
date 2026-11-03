"""场景模板注册表（价值核心：每模板=输入规范→生成脚本→预设参数）。

P0 三模板（agent6 场景库实证）：
- subfamily  亚家族着色主树（6/6 项目，痛点 5）→ TREE_COLORS + COLORSTRIP
- bootstrap  支持率展示（6/6）→ iTOL 内置 metadata 四态，本模块产出导出参数预设
- heatmap    表达热图联树（4/6，痛点 4）→ DATASET_HEATMAP + 行序校验
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Okabe-Ito 色盲安全色板（agent6 建议固化默认审美）
OKABE_ITO = ["#E69F00", "#56B4E9", "#009E73", "#F0E442",
             "#0072B2", "#D55E00", "#CC79A7", "#999999"]

# 扩展色板：Okabe-Ito 8 色 + Tol bright 10 色（>8 分组时用，17 亚家族实证需求）
PALETTE_18 = OKABE_ITO + [
    "#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE",
    "#AA3377", "#BBBBBB", "#333333", "#7FCD9B", "#C9A0DC",
]


def palette_for(n: int) -> list:
    """按分组数给色板：≤8 用 Okabe-Ito，>8 用 18 色扩展，>18 循环（告警由调用方决定）。"""
    return PALETTE_18 if n > len(OKABE_ITO) else OKABE_ITO


@dataclass
class TemplateSpec:
    name: str
    summary: str
    inputs: str           # 输入规范一句话
    outputs: list         # 产出的注解文件类型


TEMPLATES = {
    "subfamily": TemplateSpec(
        "subfamily", "亚家族着色主树（家族论文 Fig1 标配）",
        "分组 tsv：node_id<TAB>group_name（叶名=树文件叶标签；内部节点用 ID1|ID2 LCA 写法）",
        ["TREE_COLORS（枝+标签按组着色）", "DATASET_COLORSTRIP（外圈色带）"],
    ),
    "bootstrap": TemplateSpec(
        "bootstrap", "bootstrap 支持率展示（iTOL 内置 metadata 四态，无需注解文件）",
        "含 UFBoot 节点 label 的 .contree/.treefile（IQ-TREE 输出直接可用）",
        ["导出参数预设（bootstrap_display + 阈值分级）"],
    ),
    "heatmap": TemplateSpec(
        "heatmap", "表达热图联树（行序必须=树叶序，头号事故源已内建校验）",
        "矩阵 tsv：首列基因 ID（=树叶名），其余列=样本表达量（建议 log2 TPM z-score）",
        ["DATASET_HEATMAP"],
    ),
    "domains": TemplateSpec(
        "domains", "域结构联树（蛋白域示意，Pfam/hmmsearch 结果上树）",
        "域表 tsv：gene<TAB>domain<TAB>start<TAB>end<TAB>protein_length（每行一个域命中，同基因多行）",
        ["DATASET_DOMAINS（骨架+域形状，官方原生类型）"],
    ),
    "motif": TemplateSpec(
        "motif", "motif 联树（MEME/FIMO 基序位置按域状结构上树）",
        "motif 表 tsv：gene<TAB>motif_name<TAB>start<TAB>end<TAB>gene_length（MEME/FIMO 输出提取后整理）",
        ["DATASET_DOMAINS（motif 作色块；>8 motif 建议合并相似项防色板爆炸）"],
    ),
    "selection": TemplateSpec(
        "selection", "选择压力标注树（枝按 ω 蓝→白→红渐变，正选择枝高亮）",
        "ω 表 tsv：node<TAB>omega（node=叶名或内部节点 LCA 写法 ID1|ID2；codeml/HyPhy 输出整理）",
        ["TREE_COLORS（branch 按 ω 发散色阶）"],
    ),
    "connections": TemplateSpec(
        "connections", "共线连线树 / tanglegram（两节点间连线，synteny anchors 上树）",
        "配对表 tsv：node1<TAB>node2[<TAB>color][<TAB>label]（color 缺省灰；宽度按 MAXIMUM_LINE_WIDTH 归一）",
        ["DATASET_CONNECTION"],
    ),
    "timescale": TemplateSpec(
        "timescale", "时间树地质年代轴（树下方色带时间标尺）",
        "区间表 tsv：name<TAB>start<TAB>end[<TAB>color]（地质年代或自定义区间，单位与树枝长一致如 Mya）",
        ["DATASET_TIMESCALE"],
    ),
}


def write_subfamily(groups_tsv: Path, outdir: Path, palette: list = None) -> list:
    """亚家族着色：分组 tsv → TREE_COLORS + COLORSTRIP 两个注解文件。"""
    groups: dict = {}
    order: list = []
    for ln in Path(groups_tsv).read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        nid, _, g = ln.partition("\t")
        g = g.strip() or "ungrouped"
        if g not in groups:
            groups[g] = None  # 占位，色板后定
            order.append(g)
        groups.setdefault("_rows", []).append((nid.strip(), g))
    palette = palette or palette_for(len(order))
    for i, g in enumerate(order):
        groups[g] = palette[i % len(palette)]
    rows = groups["_rows"]

    # TREE_COLORS：叶标签+枝按组着色
    tc = ["TREE_COLORS", "SEPARATOR TAB", "DATA"]
    for nid, g in rows:
        c = groups[g]
        tc.append(f"{nid}\tbranch\t{c}\tnormal\t1")   # 枝着色
        tc.append(f"{nid}\tlabel\t{c}")                # 标签着色
    # COLORSTRIP：外圈色带 + 图例
    # 官方 MANDATORY SETTINGS：SEPARATOR / DATASET_LABEL / COLOR 必填（模板实证）
    # 图例规范：每行 legend 需 shape+color+label 三件套
    cs = ["DATASET_COLORSTRIP", "SEPARATOR TAB",
          "DATASET_LABEL\tSubfamily",
          "COLOR\t#ff0000",
          "LEGEND_TITLE\tSubfamily",
          "LEGEND_SHAPES\t" + "\t".join("1" for _ in order),
          "LEGEND_COLORS\t" + "\t".join(groups[g] for g in order),
          "LEGEND_LABELS\t" + "\t".join(order),
          "SHOW_STRIP_LABELS\t0", "DATA"]
    for nid, g in rows:
        cs.append(f"{nid}\t{groups[g]}\t{g}")

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    p1 = outdir / "itol_tree_colors.txt"
    p2 = outdir / "itol_colorstrip.txt"
    p1.write_text("\n".join(tc) + "\n", encoding="utf-8")
    p2.write_text("\n".join(cs) + "\n", encoding="utf-8")
    return [p1, p2]


BOOTSTRAP_EXPORT_PRESET = {
    "bootstrap_display": "1",
    "bootstrap_type": "1",          # 1=Symbol
    "bootstrap_symbol_min_size": "2",
    "bootstrap_symbol_max_size": "6",
    "bootstrap_slider_min": "70",   # <70 隐藏（agent6 审美规则）
    "bootstrap_slider_max": "100",
}


def write_domains(domains_tsv: Path, outdir: Path, label: str = "Domains",
                  palette: list = None, shape: str = "RE") -> list:
    """域结构/基序联树：域表 → DATASET_DOMAINS（官方原生类型）。

    输入 tsv（每行一个域命中，同基因多行）：
        gene<TAB>domain<TAB>start<TAB>end<TAB>protein_length
    输出 DATA 行（官方语法）：
        gene<SEP>length<SEP>SHAPE|START|END|COLOR|LABEL[<SEP>SHAPE|START|END|COLOR|LABEL...]
    """
    genes: dict = {}
    domain_names: list = []
    for i, ln in enumerate(Path(domains_tsv).read_text(encoding="utf-8").splitlines()):
        if not ln.strip() or ln.startswith("#"):
            continue
        parts = ln.split("\t")
        if len(parts) < 5:
            raise ValueError(f"第 {i + 1} 行列数不足（需 5 列：gene/domain/start/end/length）：{ln!r}")
        g, dom = parts[0].strip(), parts[1].strip()
        try:
            s, e, plen = int(parts[2]), int(parts[3]), int(parts[4])
        except ValueError:
            raise ValueError(f"第 {i + 1} 行 start/end/length 必须是整数：{ln!r}") from None
        if s >= e:
            raise ValueError(f"第 {i + 1} 行 start>=end：{ln!r}")
        if e > plen:
            raise ValueError(f"第 {i + 1} 行 end>protein_length：{ln!r}")
        genes.setdefault(g, {"length": plen, "domains": []})["domains"].append((dom, s, e))
        if dom not in domain_names:
            domain_names.append(dom)
    if not genes:
        raise ValueError("输入无任何有效域记录")
    palette = palette or palette_for(len(domain_names))
    colors = {d: palette[i % len(palette)] for i, d in enumerate(domain_names)}

    out = ["DATASET_DOMAINS", "SEPARATOR TAB",
           f"DATASET_LABEL\t{label}", "COLOR\t#ff0000",
           "BACKBONE_COLOR\t#aaaaaa", "BACKBONE_HEIGHT\t10", "BORDER_WIDTH\t1",
           f"LEGEND_TITLE\t{label}",
           "LEGEND_SHAPES\t" + "\t".join(shape for _ in domain_names),
           "LEGEND_COLORS\t" + "\t".join(colors[d] for d in domain_names),
           "LEGEND_LABELS\t" + "\t".join(domain_names),
           "DATA"]
    for g, info in genes.items():
        defs = "\t".join(f"{shape}|{s}|{e}|{colors[d]}|{d}" for d, s, e in info["domains"])
        out.append(f"{g}\t{info['length']}\t{defs}")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / "itol_domains.txt"
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    return [p]


def _omega_color(omega: float) -> str:
    """ω 发散色阶：蓝（强纯化 #2166AC）→ 白（ω=1 #F7F7F7）→ 红（正选择 #B2182B，cap 3）。"""
    def hex2rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

    def rgb2hex(rgb):
        return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)

    def lerp(a, b, t):
        return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

    blue, white, red = hex2rgb("#2166AC"), hex2rgb("#F7F7F7"), hex2rgb("#B2182B")
    w = max(0.0, min(omega, 3.0))
    if w <= 1.0:
        return rgb2hex(lerp(blue, white, w))
    return rgb2hex(lerp(white, red, (w - 1.0) / 2.0))


def write_selection(omega_tsv: Path, outdir: Path) -> list:
    """选择压力标注树：ω 表 → TREE_COLORS（枝按 ω 蓝→白→红渐变）。

    输入 tsv：node<TAB>omega（node=叶名或内部节点 LCA 写法 ID1|ID2）
    """
    rows = []
    for i, ln in enumerate(Path(omega_tsv).read_text(encoding="utf-8").splitlines()):
        if not ln.strip() or ln.startswith("#"):
            continue
        nid, _, w = ln.partition("\t")
        try:
            w = float(w.strip())
        except ValueError:
            raise ValueError(f"第 {i + 1} 行 ω 不是数字：{ln!r}") from None
        rows.append((nid.strip(), w))
    if not rows:
        raise ValueError("输入无任何有效 ω 记录")

    out = ["TREE_COLORS", "SEPARATOR TAB",
           "# ω 发散色阶：蓝(纯化)→白(ω=1)→红(正选择,cap 3)",
           "DATA"]
    for nid, w in rows:
        out.append(f"{nid}\tbranch\t{_omega_color(w)}\tnormal\t2")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / "itol_selection.txt"
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    return [p]


def write_connections(pairs_tsv: Path, outdir: Path, width: float = 1.0,
                      style: str = "normal") -> list:
    """共线连线树 / tanglegram：配对表 → DATASET_CONNECTION。

    输入 tsv：node1<TAB>node2[<TAB>color][<TAB>label]
    官方行：NODE1,NODE2,WIDTH,COLOR,STYLE,LABEL（宽度按 MAXIMUM_LINE_WIDTH 归一；STYLE normal/dashed）
    """
    rows = []
    for i, ln in enumerate(Path(pairs_tsv).read_text(encoding="utf-8").splitlines()):
        if not ln.strip() or ln.startswith("#"):
            continue
        parts = [p.strip() for p in ln.split("\t")]
        if len(parts) < 2:
            raise ValueError(f"第 {i + 1} 行需 ≥2 列（node1 node2）：{ln!r}")
        color = parts[2] if len(parts) >= 3 and parts[2] else "#999999"
        label = parts[3] if len(parts) >= 4 else ""
        rows.append((parts[0], parts[1], color, label))
    if not rows:
        raise ValueError("输入无任何有效配对")
    out = ["DATASET_CONNECTION", "SEPARATOR TAB",
           "DATASET_LABEL\tConnections", "COLOR\t#999999",
           "DRAW_ARROWS\t0", "MAXIMUM_LINE_WIDTH\t10", "CENTER_CURVES\t1",
           "DATA"]
    for n1, n2, c, lab in rows:
        out.append(f"{n1}\t{n2}\t{width}\t{c}\t{style}\t{lab}")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / "itol_connections.txt"
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    return [p]


def write_timescale(intervals_tsv: Path, outdir: Path, scaling: float = 1.0) -> list:
    """时间树地质年代轴：区间表 → DATASET_TIMESCALE（树下方色带时间标尺）。

    输入 tsv：name<TAB>start<TAB>end[<TAB>color]
    ⚠️ iTOL 约定：零=树顶（现今），值向根递增——start（老，大值）> end（新，小值）。
    官方行：RANGE_START,RANGE_END,START_LABEL,END_LABEL,FILL_COLOR,GRADIENT_COLOR,LABEL_TEXT,LABEL_STYLE
    """
    rows = []
    for i, ln in enumerate(Path(intervals_tsv).read_text(encoding="utf-8").splitlines()):
        if not ln.strip() or ln.startswith("#"):
            continue
        parts = [p.strip() for p in ln.split("\t")]
        if len(parts) < 3:
            raise ValueError(f"第 {i + 1} 行需 ≥3 列（name start end）：{ln!r}")
        try:
            start, end = float(parts[1]), float(parts[2])
        except ValueError:
            raise ValueError(f"第 {i + 1} 行 start/end 须为数字：{ln!r}") from None
        if start <= end:
            raise ValueError(f"第 {i + 1} 行 iTOL 约定 start(老)>end(新)，此行 start={start} end={end}：{ln!r}")
        color = parts[3] if len(parts) >= 4 and parts[3] else "#c8c8c8"
        rows.append((parts[0], start, end, color))
    if not rows:
        raise ValueError("输入无任何有效区间")
    out = ["DATASET_TIMESCALE", "SEPARATOR TAB",
           "DATASET_LABEL\tTimescale", "COLOR\t#000000",
           f"SCALING_FACTOR\t{scaling}", "AUTO_SCALE\t1", "SHOW_VALUE_LABELS\t1",
           "DATA"]

    def _num(x: float) -> str:
        return str(int(x)) if float(x).is_integer() else str(x)

    for name, start, end, color in rows:
        out.append(f"{_num(start)}\t{_num(end)}\t\t\t{color}\t\t{name}\tnormal")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / "itol_timescale.txt"
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    return [p]


def write_heatmap(matrix_tsv: Path, outdir: Path, tree_leaves: list = None) -> list:
    """表达矩阵 → DATASET_HEATMAP。行序校验：给了 tree_leaves 就强制按树序重排+查漏。"""
    lines = Path(matrix_tsv).read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    samples = header[1:]
    rows = {ln.split("\t")[0]: ln for ln in lines[1:] if ln.strip()}
    missing, ordered = [], []
    if tree_leaves:
        for leaf in tree_leaves:
            if leaf in rows:
                ordered.append(rows.pop(leaf))
            else:
                missing.append(leaf)
        ordered.extend(rows.values())  # 树外多余行挂尾（会告警）
    else:
        ordered = list(rows.values())

    out = ["DATASET_HEATMAP", "SEPARATOR TAB",
           "FIELD_LABELS\t" + ",".join(samples),
           "COLOR_MIN\t#2166AC", "COLOR_MID\t#F7F7F7", "COLOR_MAX\t#B2182B",
           "AUTO_SCALE\t1", "DATA"]
    out.extend(ordered)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / "itol_heatmap.txt"
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    return [p], missing
