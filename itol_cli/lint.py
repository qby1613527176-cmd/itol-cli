"""itol lint — iTOL 注解文件本地校验器（差异化护城河：人/AI 手写模板的第一道关）。

校验规则基于官方模板实证（workflows/itol_research/agent2_formats.md + downloads/templates/）：
- 首行关键字是模板锚（不是文件名！）
- 官方 CONNECTION 是单数；DOMAINS 不是 PROTEINDOMAINS
- 默认 SPACE 分隔；SEPARATOR 行可改 TAB/COMMA
- 内部节点一律 LCA 写法 ID1|ID2
- DATA 段前全是 KEY VALUE 控制行
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# 官方模板类型（首行关键字，单一权威）——以 30 个官方模板实测全集为准（2026-11-02 校准）
KNOWN_KEYWORDS = {
    # 树本身控制
    "TREE_COLORS", "DATASET_STYLE", "MULTI_STYLE", "LABELS", "POPUP_INFO", "COLLAPSE", "PRUNE", "SPACING",
    "AUTO_TAXONOMY", "METADATA",
    # 数据集
    "DATASET_COLORSTRIP", "DATASET_BINARY", "DATASET_GRADIENT", "DATASET_HEATMAP",
    "DATASET_SYMBOL", "DATASET_EXTERNALSHAPE", "DATASET_DOMAINS", "DATASET_SIMPLEBAR",
    "DATASET_MULTIBAR", "DATASET_BOXPLOT", "DATASET_LINECHART", "DATASET_PIECHART",
    "DATASET_ALIGNMENT", "DATASET_CONNECTION", "DATASET_IMAGE", "DATASET_TEXT",
    "DATASET_ARROWS", "DATASET_RANGE", "DATASET_TANGLEGRAM", "DATASET_TIMESCALE",
}
# 常见写错/别名（给诊断建议）
ALIASES = {
    "DATASET_CONNECTIONS": "DATASET_CONNECTION（官方是单数！）",
    "DATASET_PROTEINDOMAINS": "DATASET_DOMAINS",
    "DATASET_COLOR_STRIP": "DATASET_COLORSTRIP",
    "TREE_COLOR": "TREE_COLORS",
}
SEPARATORS = {"SPACE": None, "TAB": "\t", "COMMA": ","}  # None = 任意空白
# 官方允许 hex / rgb() / rgba()（COLORSTRIP 模板实证：rgba(0,255,0,0.5) 合法）
HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
RGB_RE = re.compile(r"^rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*(?:,\s*[\d.]+\s*)?\)$", re.I)


def _is_color(s: str) -> bool:
    return bool(HEX_RE.match(s) or RGB_RE.match(s))


@dataclass
class LintIssue:
    level: str  # "error" | "warning"
    line: int   # 0-based；-1 = 文件级
    message: str


@dataclass
class LintReport:
    path: str
    keyword: str = ""
    issues: list = field(default_factory=list)

    @property
    def errors(self):
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self):
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, level: str, line: int, message: str) -> None:
        self.issues.append(LintIssue(level, line, message))

    def summary(self) -> str:
        head = f"{'✅' if self.ok else '❌'} {self.path}  (类型: {self.keyword or '未知'})"
        lines = [f"  L{i.line + 1}: [{i.level}] {i.message}" for i in self.issues]
        return "\n".join([head] + lines)


def _detect_separator(header_lines: list[str]) -> tuple[str, object]:
    for ln in header_lines:
        parts = ln.split(None, 1)
        if parts and parts[0].upper() == "SEPARATOR" and len(parts) == 2:
            val = parts[1].strip().upper()
            if val in SEPARATORS:
                return val, SEPARATORS[val]
            return val, None  # 未知分隔符 → 按 SPACE 处理但告警
    return "SPACE", None


def lint_file(path: Path) -> LintReport:
    path = Path(path)
    rep = LintReport(path=str(path))
    if not path.is_file():
        rep.add("error", -1, "文件不存在")
        return rep
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()

    # 1. 首行关键字
    first = next((ln.strip() for ln in lines if ln.strip()), "")
    if not first:
        rep.add("error", -1, "空文件")
        return rep
    rep.keyword = first
    if first not in KNOWN_KEYWORDS:
        hint = ALIASES.get(first)
        rep.add("error", 0, f"未知首行关键字 {first!r}" + (f"——你是不是想要 {hint}？" if hint else ""))

    # 2. 找 DATA 段（官方模板示例形态可能连 DATA 标记行本身也被注释）
    try:
        data_idx = next(i for i, ln in enumerate(lines) if ln.strip().upper() == "DATA")
    except StopIteration:
        commented_data = next((i for i, ln in enumerate(lines) if ln.strip().lstrip("#").strip().upper() == "DATA"), None)
        if commented_data is not None:
            data_idx = commented_data
            rep.add("warning", data_idx, "DATA 标记行被注释（官方模板示例形态）")
        else:
            rep.add("error", -1, "缺 DATA 段标记行（独立一行 'DATA'）")
            return rep
    header = [ln for ln in lines[1:data_idx] if ln.strip() and not ln.strip().startswith("#")]
    data = [ln for ln in lines[data_idx + 1:] if ln.strip() and not ln.strip().startswith("#")]
    if not data:
        # 官方模板形态：示例数据行全部被 # 注释——是模板示例不是真数据，降级 warning
        commented = [ln for ln in lines[data_idx + 1:] if ln.strip().startswith("#")]
        if commented:
            rep.add("warning", data_idx, "DATA 段数据行全部被注释（官方模板示例形态；实数据文件须有非注释数据行）")
        else:
            rep.add("error", data_idx, "DATA 段为空")

    # 3. 分隔符一致性
    sep_name, sep = _detect_separator(header)
    if sep_name not in SEPARATORS:
        rep.add("warning", -1, f"未知 SEPARATOR {sep_name!r}（官方只有 SPACE/TAB/COMMA），按 SPACE 校验")
        sep_name, sep = "SPACE", None

    def split_row(ln: str) -> list[str]:
        return ln.split(sep) if sep else ln.split()

    # 4. 数据行校验（ALIGNMENT 的 DATA 是 FASTA 序列，不做表格列数检查）
    widths = set()
    if rep.keyword != "DATASET_ALIGNMENT":
        for i, ln in enumerate(data):
            row = split_row(ln)
            lineno = data_idx + 1 + i
            if len(row) < 2:
                rep.add("error", lineno, f"数据行列数不足（{len(row)} 列）：{ln[:60]!r}")
                continue
            widths.add(len(row))
            # 节点 ID 列非空 + 内部节点 LCA 写法检查
            nid = row[0]
            if not nid:
                rep.add("error", lineno, "节点 ID 为空")
            if sep == "," and "|" not in nid and " " in nid:
                rep.add("error", lineno, f"COMMA 分隔下节点 ID 含空格：{nid!r}——内部节点请用 LCA 写法 ID1|ID2")

    # 4.5 类型必填项（官方模板 MANDATORY SETTINGS 区实证：20/20 dataset_* 模板全有 DATASET_LABEL）
    header_keys = {re.split(r"[\s,]+", ln, maxsplit=1)[0].upper() for ln in header}
    if rep.keyword.startswith("DATASET_") and "DATASET_LABEL" not in header_keys:
        rep.add("error", -1, f"{rep.keyword} 缺 MANDATORY 字段 DATASET_LABEL（官方模板必填）")
    if rep.keyword == "DATASET_COLORSTRIP" and "COLOR" not in header_keys:
        rep.add("warning", -1, "COLORSTRIP 建议带 COLOR（图例/默认色，官方模板 MANDATORY 区）")
    if ("LEGEND_COLORS" in header_keys or "LEGEND_LABELS" in header_keys) and "LEGEND_SHAPES" not in header_keys:
        rep.add("warning", -1, "图例规范=每行 shape+color+label：有 LEGEND_COLORS/LABELS 建议补 LEGEND_SHAPES")

    # 5. 类型特定校验
    if rep.keyword == "DATASET_COLORSTRIP":
        for i, ln in enumerate(data):
            row = split_row(ln)
            if len(row) >= 2 and not _is_color(row[1]):
                rep.add("error", data_idx + 1 + i, f"COLORSTRIP 第 2 列应为颜色（hex/rgb/rgba）：{row[1]!r}")
    if rep.keyword in ("DATASET_HEATMAP", "DATASET_MULTIBAR", "DATASET_BINARY"):
        labels = None
        for ln in header:
            if ln.upper().startswith("FIELD_LABELS"):
                labels = split_row(ln)[1:] if sep is None else ln.split(sep)[1].split(",")
        if labels is None:
            rep.add("warning", -1, f"{rep.keyword} 建议带 FIELD_LABELS（图例列名）")
        elif widths and len(widths) == 1:
            ncol = next(iter(widths)) - 1
            if ncol != len(labels):
                rep.add("error", -1, f"FIELD_LABELS 数（{len(labels)}）≠ 数据列数（{ncol}）")
    if rep.keyword == "DATASET_CONNECTION":
        for i, ln in enumerate(data):
            row = split_row(ln)
            if len(row) >= 2 and ("|" in row[0] or "|" in row[1]):
                rep.add("warning", data_idx + 1 + i, "CONNECTION 的节点通常是叶名对，LCA 写法确认是否符合预期")
    if rep.keyword == "DATASET_DOMAINS":
        for i, ln in enumerate(data):
            row = split_row(ln)
            lineno = data_idx + 1 + i
            if len(row) < 3:
                rep.add("error", lineno, f"DOMAINS 数据行需 ≥3 列（ID/蛋白长度/域定义…）：{ln[:60]!r}")
                continue
            try:
                plen = int(row[1])
            except ValueError:
                rep.add("error", lineno, f"DOMAINS 第 2 列须为蛋白长度整数：{row[1]!r}")
                continue
            for d in row[2:]:
                parts = d.split("|")
                if len(parts) != 5:
                    rep.add("error", lineno, f"域定义需 5 段 SHAPE|START|END|COLOR|LABEL：{d!r}")
                    continue
                try:
                    s, e = int(parts[1]), int(parts[2])
                    if s >= e:
                        rep.add("error", lineno, f"域 START>=END：{d!r}")
                    elif e > plen:
                        rep.add("error", lineno, f"域 END>{plen}（超蛋白长度）：{d!r}")
                except ValueError:
                    rep.add("error", lineno, f"域 START/END 须为整数：{d!r}")
                if not _is_color(parts[3]):
                    rep.add("error", lineno, f"域颜色非 hex/rgb/rgba：{parts[3]!r}")

    return rep


def lint_paths(paths: list[Path]) -> list[LintReport]:
    return [lint_file(p) for p in paths]
