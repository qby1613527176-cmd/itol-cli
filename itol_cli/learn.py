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
