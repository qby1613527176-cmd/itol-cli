"""美学自适应默认——把文献锚定的树图美学参数经验编码成 itol-cli 的默认与护栏。

文献锚（docs/METHODOLOGY.md）：PLOS/Nature/Elsevier 期刊规格、Okabe-Ito/Paul Tol 色板、
Wilke 视觉通道、Phylo.io 可读性拐点。原则：字号随物理图幅缩放、定性色板分档、超阈值告警。
"""
from __future__ import annotations

# ── 色板（文献锚定）─────────────────────────────────────────────
# Okabe-Ito 色盲安全 8 色（定性色板上限之一，jfly.uni-koeln.de/color）
OKABE_ITO = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000"]
# Paul Tol muted 9 色（定性色板实际上限，sronpersonalpages.nl/~pault）
TOL_MUTED = ["#CC6677", "#332288", "#DDCC77", "#117733", "#88CCEE", "#882255", "#44AA99", "#999933", "#AA4499"]
# Paul Tol bright 7 色
TOL_BRIGHT = ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"]

# 定性色板分档阈值（Tol 官方：>9 类应换 banded sequential）
_PALETTE_TIERS = [(7, "tol_bright"), (9, "okabeito")]  # ≤7 Tol-bright，8-9 Okabe-Ito/Tol-muted


def recommend_palette(n_groups: int) -> tuple[str, list[str], list[str]]:
    """按分组数推荐定性色板（文献锚定分档）。返回 (色板名, 颜色列表, 警告列表)。

    分档（Tol/Okabe-Ito）：≤7 → Tol-bright；8-9 → Okabe-Ito（或 Tol-muted）；>9 → 告警类别过多。
    """
    warnings: list[str] = []
    if n_groups <= 0:
        return "tol_bright", TOL_BRIGHT, warnings
    if n_groups <= 7:
        return "tol_bright", TOL_BRIGHT[:n_groups], warnings
    if n_groups <= 9:
        warnings.append(f"{n_groups} 组接近定性色板上限（Okabe-Ito 8 色 / Tol muted 9 色）——考虑合并小组")
        return "okabeito", (OKABE_ITO * 2)[:n_groups], warnings
    warnings.append(
        f"⚠️ {n_groups} 组超出定性色盲安全色板上限（Tol 官方：>9 类应改用 banded sequential 或合并组）。"
        f"颜色将无法可靠区分——建议合并小组或改用连续/层级编码")
    # 超上限：循环拼接 Tol muted + Okabe-Ito 兜底（用户仍可用，但被明确警告）
    pool = TOL_MUTED + OKABE_ITO
    return "tol_muted", [pool[i % len(pool)] for i in range(n_groups)], warnings


# ── 字号/可读性（字号随物理图幅缩放，pt 是绝对单位）──────────────────
# 期刊规格（实测官方页）：PLOS 图内文字 8-12pt；Nature 90mm 版心下 5-7pt；Elsevier 7pt（下标≥6pt）
# 矩形树：可读标签数 ≈ 图幅高 / (字号对应行高)。1pt ≈ 0.35mm，行距≈1.2×字号

def max_readable_leaves(fig_height_mm: float, font_pt: float) -> int:
    """给定图幅高+字号，估算矩形布局可读的最大叶数（行距≈1.2×字号）。"""
    line_h_mm = font_pt * 0.3528 * 1.2
    usable = fig_height_mm * 0.9  # 留边距
    return max(1, int(usable / line_h_mm))


def readability_warnings(n_leaves: int, layout: str = "rect",
                         fig_width_mm: float = 180.0, fig_height_mm: float = 170.0) -> list[str]:
    """可读性护栏：按叶数/布局/图幅给警告（文献锚：Phylo.io 可读性拐点 + Nature/PLOS 字号）。

    返回警告列表（空=可读）。layout: rect/circular/unrooted。
    """
    w: list[str] = []
    if layout in ("rect", "rectangular"):
        # 矩形布局：标签在右，行数=叶数；图高决定可读叶数
        for pt in (8, 6):  # 先试正文 8pt，再试下限 6pt
            maxl = max_readable_leaves(fig_height_mm, pt)
            if n_leaves <= maxl:
                break
        else:
            w.append(f"⚠️ {n_leaves} 叶在 {fig_height_mm}mm 高矩形布局下，即使 6pt 字号也只能容 "
                     f"~{max_readable_leaves(fig_height_mm, 6)} 叶——标签将不可读。建议：改环形/折叠子树/拆面板")
    if n_leaves > 50 and layout in ("rect", "rectangular"):
        w.append(f"⚠️ {n_leaves} 叶超过并排/细读的可读性拐点（Phylo.io：几十 tip）；建议环形布局或折叠单系群")
    if layout == "circular" and n_leaves < 40:
        w.append(f"💡 {n_leaves} 叶用矩形布局标签可读性更高（环形适合 >60 叶的紧凑展示）")
    return w


def recommend_font_pt(n_leaves: int, fig_width_mm: float = 180.0) -> int:
    """按叶数+图幅推荐叶标签字号（钳制在期刊合法区间 5-12pt）。"""
    if n_leaves <= 40:
        pt = 10
    elif n_leaves <= 80:
        pt = 8
    elif n_leaves <= 150:
        pt = 6
    else:
        pt = 5
    return max(5, min(12, pt))


def channel_budget_check(layers: dict[str, str]) -> list[str]:
    """视觉通道预算校验（Wilke Ch2：每通道最多绑 1 变量，单图 ≤5 scale）。

    layers: {通道: 绑定的变量}，如 {'color':'亚家族', 'size':'支持度'}。返回冲突警告。
    """
    w: list[str] = []
    n = len([v for v in layers.values() if v])
    if n > 5:
        w.append(f"⚠️ 单图绑定 {n} 个视觉通道（{layers}）超过清晰上限 5（Wilke）——减少叠加层")
    # 连续数据禁用 shape/linetype 通道
    for ch in ("shape", "linetype"):
        if layers.get(ch) and "连续" in str(layers[ch]):
            w.append(f"⚠️ {ch} 通道只能编码离散数据（Wilke），{layers[ch]} 疑似连续——改用 size/color")
    return w


# ── 迭代评分器（itol iterate 的目标函数）───────────────────────────────────────
def score_variant(*, n_leaves: int, n_groups: int, layout: str, palette: str,
                  font_pt: float, strip_width: int, n_datasets: int = 1,
                  fig_width_mm: float = 180.0, fig_height_mm: float = 170.0) -> tuple[float, list[str]]:
    """对一个出图变体打综合分（0-10，越高越好）+ 评分明细。

    评分维度（文献锚，readability 权重高于 aesthetics——Rougier R9）：
    - 可读性（40%）：叶数×布局×图幅，标签可读
    - 色板适配（25%）：定性色板分档匹配 + 色盲安全
    - 信息密度（20%）：通道预算（≤5 scale）
    - 布局合理（15%）：布局与叶数匹配
    """
    notes: list[str] = []
    score = 10.0
    # 可读性（权重 4）
    rw = readability_warnings(n_leaves, layout, fig_width_mm, fig_height_mm)
    read_pen = 4.0 if rw else 0.0
    if rw:
        notes.append(f"可读性 -{read_pen}（{rw[0][:30]}…）")
    score -= read_pen
    # 色板适配（权重 2.5）
    _, _, pwarn = recommend_palette(n_groups)
    if any("超出" in w for w in pwarn):
        score -= 2.5
        notes.append("色板 -2.5（超定性色板上限）")
    elif pwarn:
        score -= 1.0
        notes.append("色板 -1.0（接近上限）")
    # 通道预算（权重 2）
    if n_datasets > 5:
        score -= 2.0
        notes.append(f"密度 -2.0（{n_datasets} 数据集 >5 scale 上限）")
    elif n_datasets > 3:
        score -= 1.0
        notes.append(f"密度 -1.0（{n_datasets} 数据集，接近上限）")
    # 布局合理（权重 1.5）
    if layout == "circular" and n_leaves < 40:
        score -= 1.0
        notes.append("布局 -1.0（小叶数环形不如矩形可读）")
    if layout in ("rect", "rectangular") and n_leaves > 200:
        score -= 1.5
        notes.append("布局 -1.5（千叶级矩形标签糊）")
    return max(0.0, round(score, 1)), notes


# 迭代变体搜索空间（美学参数轴）
SWEEP_AXES: dict[str, list] = {
    "layout": ["rect", "circular"],
    "palette": ["npg", "okabeito", "tol_bright", "tol_muted"],
    "font_pt": [6, 8, 10],
    "strip_width": [30, 50, 80],
}


# ── 色板评分（iterate 闭环的约束评分器；ColorBrewer「配色是约束求解」思想）─────────
NAMED_PALETTES = {
    "npg": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85"],
    "okabeito": OKABE_ITO,
    "tol_bright": TOL_BRIGHT,
    "tol_muted": TOL_MUTED,
}


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _srgb_linear(v: float) -> float:
    v /= 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _rgb_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """sRGB → CIELAB（D65）。返回 (L, a, b)。"""
    r, g, b = (_srgb_linear(c) for c in rgb)
    # linear RGB → XYZ (D65)
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505
    # 归一到 D65 白点
    xn, yn, zn = x / 0.95047, y / 1.0, z / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(xn), f(yn), f(zn)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _sim_deuteranopia_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """Deuteranopia（绿色盲）模拟（linear RGB 矩阵）→ CIELAB。"""
    r, g, b = (_srgb_linear(c) for c in rgb)
    # Machado 2009 近似（linear RGB 域）
    dr = 0.625 * r + 0.375 * g
    dg = 0.7 * r + 0.3 * g
    db = 0.3 * g + 0.7 * b
    sim_rgb: tuple[int, int, int] = (round(dr * 255), round(dg * 255), round(db * 255))
    return _rgb_lab(sim_rgb)


def _delta_e(lab1: tuple, lab2: tuple) -> float:
    """CIE76 ΔE（CIELAB 欧氏距离，感知均匀）。"""
    return sum((x - y) ** 2 for x, y in zip(lab1, lab2)) ** 0.5


def score_palette(colors: list[str], n_groups: int) -> dict:
    """给一组色板打分（约束求解，非美学评判）。返回 {score, issues, min_sim_dist}。

    约束：①绿色盲模拟（CIELAB ΔE）两两可区分 ②组数不超色板安全上限 ③与白底对比度。
    分数 0-10。CIELAB ΔE：≥20 大致可区分，<12 难区分。
    """
    issues: list[str] = []
    use = [colors[i % len(colors)] for i in range(n_groups)]
    sim = [_sim_deuteranopia_lab(_hex_rgb(c)) for c in use]
    mind = min((_delta_e(sim[i], sim[j]) for i in range(len(sim)) for j in range(i + 1, len(sim))), default=999)
    cb_ok = mind >= 12.0  # CIELAB ΔE≥12 绿色盲下可区分（经验阈值）
    if not cb_ok:
        issues.append(f"绿色盲模拟下有两色难区分（min CIELAB ΔE={mind:.1f}<12）")
    if n_groups > 9:
        issues.append(f"{n_groups} 组超定性色板上限（Tol：>9 应换 banded sequential）")
    def lum(c: str) -> float:
        return _rgb_lab(_hex_rgb(c))[0]
    lowcontrast = [c for c in use if lum(c) > 92]  # CIELAB L* 太接近白(100)
    if lowcontrast:
        issues.append(f"{len(lowcontrast)} 色与白底对比不足（太浅：{lowcontrast[:2]}）")
    score = 10.0
    if not cb_ok:
        score -= 4
    if n_groups > 9:
        score -= 3
    if lowcontrast:
        score -= 1.5 * len(lowcontrast)
    return {"score": max(0.0, round(score, 1)), "issues": issues, "min_sim_dist": round(mind, 1),
            "colorblind_ok": cb_ok, "n_colors": n_groups}


def iterate_palettes(n_groups: int, palettes: dict[str, list[str]] | None = None) -> list[dict]:
    """对全部命名色板打分并排序（iterate 的色板维度）。返回按分数降序的变体列表。"""
    pals = palettes or NAMED_PALETTES
    out = []
    for name, colors in pals.items():
        s = score_palette(colors, n_groups)
        out.append({"palette": name, **s, "colors": [colors[i % len(colors)] for i in range(n_groups)]})
    out.sort(key=lambda x: -x["score"])
    return out
