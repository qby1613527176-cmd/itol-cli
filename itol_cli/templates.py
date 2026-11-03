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
}


def write_subfamily(groups_tsv: Path, outdir: Path, palette: list = None) -> list:
    """亚家族着色：分组 tsv → TREE_COLORS + COLORSTRIP 两个注解文件。"""
    palette = palette or OKABE_ITO
    groups: dict = {}
    order: list = []
    for ln in Path(groups_tsv).read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        nid, _, g = ln.partition("\t")
        g = g.strip() or "ungrouped"
        if g not in groups:
            groups[g] = palette[len(groups) % len(palette)]
            order.append(g)
        groups.setdefault("_rows", []).append((nid.strip(), g))
    rows = groups["_rows"]

    # TREE_COLORS：叶标签+枝按组着色
    tc = ["TREE_COLORS", "SEPARATOR TAB", "DATA"]
    for nid, g in rows:
        c = groups[g]
        tc.append(f"{nid}\tbranch\t{c}\tnormal\t1")   # 枝着色
        tc.append(f"{nid}\tlabel\t{c}")                # 标签着色
    # COLORSTRIP：外圈色带 + 图例
    cs = ["DATASET_COLORSTRIP", "SEPARATOR TAB",
          "COLOR\t#ff0000",
          "LEGEND_TITLE\tSubfamily",
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
