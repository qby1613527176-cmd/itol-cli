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
