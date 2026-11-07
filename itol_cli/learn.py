"""itol learn —— 模板逆向复用（对标 itol.toolkit 主题学习）。

解析已有 iTOL 注解文件 → 抽出 header 区样式参数 → 复用到新数据。
场景：看到别人论文的 iTOL 图想复同样式；或把自己的旧图样式套到新数据。
"""
from __future__ import annotations

import json
from pathlib import Path

from .errors import invalid_input

# 已知的 iTOL 注解关键字（lint.py 同款集合，learn 用它识别首行类型）
_KNOWN_KEYWORDS = {
    "TREE_COLORS", "DATASET_STYLE", "MULTI_STYLE", "LABELS", "POPUP_INFO", "COLLAPSE", "PRUNE", "SPACING",
    "DATASET_COLORSTRIP", "DATASET_BINARY", "DATASET_GRADIENT", "DATASET_HEATMAP", "DATASET_SYMBOL",
    "DATASET_EXTERNALSHAPE", "DATASET_DOMAINS", "DATASET_SIMPLEBAR", "DATASET_MULTIBAR", "DATASET_BOXPLOT",
    "DATASET_LINECHART", "DATASET_PIECHART", "DATASET_ALIGNMENT", "DATASET_CONNECTION", "DATASET_IMAGE",
    "DATASET_TEXT", "DATASET_ARROWS", "DATASET_RANGE", "DATASET_TANGLEGRAM", "DATASET_TIMESCALE", "DATASET_SCALE",
    "DATASET_LABEL", "DATASET_COLORBRANCH", "DATASET_COLORSHAPE", "DATASET_ANNOTATION",
}

_SEP_NAMES = {"TAB": "\t", "SPACE": " ", "COMMA": ","}


def learn_style(path: Path) -> dict:
    """解析 iTOL 注解文件，抽出样式参数（header 区 = DATA 行之前的所有内容）。

    返回 dict：keyword / separator / header_params（有序 list of (key, value)）/ n_data_rows。
    """
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        raise invalid_input(f"{path} 为空")
    keyword = ""
    for ln in lines:
        ls = ln.strip()
        if ls and not ls.startswith("#"):
            keyword = ls.split()[0].upper()
            break
    if keyword not in _KNOWN_KEYWORDS:
        raise invalid_input(f"{path} 首行不是已知 iTOL 关键字（读到 {keyword!r}）——跑 itol lint 看看")
    sep = "\t"
    header: list[tuple[str, str]] = []
    n_data = 0
    in_data = False
    for ln in lines:
        ls = ln.strip()
        if not in_data:
            if ls.upper() == "DATA":
                in_data = True
                continue
            if not ls or ls.startswith("#"):
                continue
            # header 参数行：KEY<sep>value
            parts = ln.split("\t") if "\t" in ln else ln.split(None, 1)
            if not parts:
                continue
            key = parts[0].strip()
            val = parts[1].strip() if len(parts) > 1 else ""
            if key.upper() == "SEPARATOR":
                sep = _SEP_NAMES.get(val.upper(), "\t")
            header.append((key, val))
        else:
            if ls and not ls.startswith("#"):
                n_data += 1
    return {
        "keyword": keyword,
        "separator": {v: k for k, v in _SEP_NAMES.items()}.get(sep, "TAB"),
        "header_params": header,
        "n_data_rows": n_data,
        "source": str(path),
    }


def apply_style(style: dict, new_data: Path, out: Path) -> Path:
    """把学到的 header 样式套到新数据文件（new_data 的每行原样进 DATA 区）。

    new_data 应已符合该数据集类型的列结构（learn 只管样式，不管语义映射）。
    """
    keyword = style["keyword"]
    sep = _SEP_NAMES.get(style.get("separator", "TAB"), "\t")
    lines = [keyword]
    for key, val in style["header_params"]:
        if key == keyword:  # 首行关键字已写
            continue
        lines.append(f"{key}{sep}{val}" if val else key)
    lines.append("DATA")
    data_lines = [ln for ln in Path(new_data).read_text(encoding="utf-8").splitlines()
                  if ln.strip() and not ln.startswith("#")]
    lines.extend(data_lines)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def style_to_json(style: dict) -> str:
    return json.dumps(style, ensure_ascii=False, indent=2)


def style_from_json(text: str) -> dict:
    d = json.loads(text)
    if "keyword" not in d or "header_params" not in d:
        raise invalid_input("样式 JSON 缺 keyword/header_params 字段")
    return d


# ── 图片样式逆向（用户拖入「认为美观」的图，复刻其参数）────────────────────────────
def learn_svg(path: Path) -> dict:
    """从 SVG 矢量图反推样式参数（高保真，零依赖）。

    SVG 是结构化 XML：颜色/字号/几何/布局全在标签里。提取调色板（用频排序）、
    字号、布局（矩形/环形）、叶数、枝色 → style dict（兼容 apply_style）。
    """
    import re
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    # 调色板：收集 fill/stroke 的非黑白灰色，按频次排序
    colors: dict[str, int] = {}
    for m in re.finditer(r'(?:fill|stroke)="([^"]+)"', text):
        c = m.group(1).strip().lower()
        if c.startswith("#") and c not in ("#000", "#000000", "#fff", "#ffffff", "#888888", "#ccc", "#333", "#666", "#999"):
            colors[c] = colors.get(c, 0) + 1
    palette = [c for c, _ in sorted(colors.items(), key=lambda x: -x[1])]
    # 字号：font-size 属性
    fonts = [float(m.group(1)) for m in re.finditer(r'font-size="?([\d.]+)', text)]
    font_pt = round(sum(fonts) / len(fonts), 1) if fonts else None
    # 布局：环形=有圆弧命令或 rotate 变换占多；矩形=直线为主
    n_arc = len(re.findall(r'[d]\s*=\s*"[^"]*[aA][^"]*"', text))
    n_line = text.count("<line") + text.count("<polyline")
    layout = "circular" if n_arc > n_line * 0.3 and n_arc > 3 else "rect"
    # 叶数：<text> 标签数（近似）
    n_labels = len(re.findall(r"<text", text))
    return {
        "source_image": str(path),
        "palette": palette[:12],
        "n_colors": len(palette),
        "font_pt": font_pt,
        "layout": layout,
        "n_labels": n_labels,
        "branch_colors": [c for c in palette if c],
    }


def learn_image(path: Path) -> dict:
    """从图片反推样式参数。.svg → 全解析；.png/.jpg → 主色调色板+布局（需 PIL）。

    返回 style dict + 来源说明。PNG 需 pillow（pip install pillow）。
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".svg":
        d = learn_svg(path)
        d["method"] = "svg 全解析（高保真）"
        return d
    if suffix in (".png", ".jpg", ".jpeg"):
        try:
            from PIL import Image  # type: ignore
        except ImportError:
            raise invalid_input(
                "PNG/JPG 图片样式提取需 pillow（SVG 无需）。装一下：pip install pillow；或改用 SVG 版图片（高保真）") from None
        img = Image.open(path).convert("RGB")
        img.thumbnail((200, 200))  # 缩小加速
        # 主色提取：quantize 聚类
        q = img.quantize(colors=10)
        pal = q.getpalette()[:30]
        counts = sorted(q.getcolors(), reverse=True)
        palette = []
        for cnt, idx in counts:
            r, g, b = pal[idx * 3:idx * 3 + 3]
            if (r, g, b) not in ((255, 255, 255), (0, 0, 0)) and not (r > 230 and g > 230 and b > 230):
                palette.append(f"#{r:02x}{g:02x}{b:02x}")
        w, h = Image.open(path).size
        layout = "circular" if abs(w - h) / max(w, h) < 0.15 else "rect"  # 方形画布≈环形
        return {"source_image": str(path), "method": "png 主色提取（近似）", "palette": palette[:12],
                "n_colors": len(palette), "layout": layout,
                "note": "PNG 只能拿调色板+布局；字号/间距建议用 SVG 版复刻"}
    raise invalid_input(f"不支持的图片格式 {suffix}（支持 .svg / .png / .jpg）")
