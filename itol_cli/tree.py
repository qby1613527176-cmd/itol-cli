"""纯 Python Newick 树引擎（零第三方依赖）。

为 itol-cli 提供树结构校验/统计/预处理/单系检验能力——对标 gotree/nwkit/PhyKIT 的树侧功能。
设计哲学：lint 拦静默坑（烂树别进 gen→render），tree 子命令做上 iTOL 前的高频预处理。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ItolError, invalid_input

# 不可见/对抗字符（零宽空格、BOM、bidi 控制符等）——AI 生成文件常混入
_INVISIBLE = {
    "\u200b": "零宽空格 U+200B",
    "\u200c": "零宽非连接符 U+200C",
    "\u200d": "零宽连接符 U+200D",
    "\ufeff": "BOM U+FEFF",
    "\u202a": "bidi LRE U+202A",
    "\u202b": "bidi RLE U+202B",
    "\u202c": "bidi PDF U+202C",
    "\u202e": "bidi RLO U+202E",
    "\u00a0": "不换行空格 U+00A0",
}


@dataclass
class Node:
    """树节点。name 叶标签或内部节点名，bl 支长，children 子节点。"""
    name: str = ""
    bl: float | None = None
    children: list[Node] = field(default_factory=list)
    parent: Node | None = field(default=None, repr=False, compare=False)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def leaves(self) -> list[Node]:
        """所有后代叶节点。"""
        if self.is_leaf:
            return [self]
        out: list[Node] = []
        for c in self.children:
            out.extend(c.leaves())
        return out

    def iter(self) -> list[Node]:
        """全树先序遍历（含自身）。"""
        out = [self]
        for c in self.children:
            out.extend(c.iter())
        return out

    def to_newick(self) -> str:
        if self.is_leaf:
            return _quote(self.name) + (f":{self.bl:g}" if self.bl is not None else "")
        inner = "(" + ",".join(c.to_newick() for c in self.children) + ")"
        return inner + self.name + (f":{self.bl:g}" if self.bl is not None else "")


def _quote(name: str) -> str:
    return f"'{name}'" if (name and re.search(r"[\s,():\[\];']", name)) else name


def parse_newick(text: str) -> Node:
    """解析 Newick 文本为 Node 树。支持单/多树（取第一棵）、NHX 注释忽略、引号标签。"""
    s = text.strip()
    if not s:
        raise invalid_input("树文件为空")
    # 多树/多行：取第一个完整树（到第一个顶层分号）
    first_semi = _find_top_semicolon(s)
    if first_semi != -1:
        s = s[: first_semi + 1]
    s = re.sub(r"\[&&NHX:[^\]]*\]", "", s)  # 去 NHX 注释
    pos = 0

    def parse_sub() -> Node:
        nonlocal pos
        node = Node()
        if pos < len(s) and s[pos] == "(":
            pos += 1  # (
            while True:
                child = parse_sub()
                child.parent = node
                node.children.append(child)
                if pos < len(s) and s[pos] == ",":
                    pos += 1
                    continue
                if pos < len(s) and s[pos] == ")":
                    pos += 1
                    break
                break
        # 标签
        name = _read_label()
        node.name = name
        # 支长
        if pos < len(s) and s[pos] == ":":
            pos += 1
            blstr = _read_brlen()
            if blstr != "":
                try:
                    node.bl = float(blstr)
                except ValueError:
                    raise invalid_input(f"非法支长 {blstr!r}（节点 {name or '?'}）") from None
        return node

    def _read_label() -> str:
        nonlocal pos
        if pos < len(s) and s[pos] in "'\"":
            q = s[pos]
            pos += 1
            start = pos
            while pos < len(s) and s[pos] != q:
                pos += 1
            val = s[start:pos]
            pos += 1  # 跳过引号
            return val
        start = pos
        while pos < len(s) and s[pos] not in ",():;":
            pos += 1
        return s[start:pos].strip()

    def _read_brlen() -> str:
        nonlocal pos
        start = pos
        while pos < len(s) and s[pos] in "0123456789.eE+-":
            pos += 1
        return s[start:pos]

    root = parse_sub()
    if pos < len(s) and s[pos] == ";":
        pos += 1
    if s[pos:].strip():
        raise invalid_input(f"Newick 解析残留：{s[pos:pos+30]!r}（括号可能不平衡）")
    return root


def _find_top_semicolon(s: str) -> int:
    """找顶层（非引号内）第一个分号。"""
    depth = 0
    in_q: str | None = None
    for i, ch in enumerate(s):
        if in_q:
            if ch == in_q:
                in_q = None
            continue
        if ch in "'\"":
            in_q = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == ";" and depth == 0:
            return i
    return -1


def validate_tree_text(text: str) -> list[str]:
    """校验树文本，返回问题列表（空=通过）。对标 gotree stats/PyiTOL validate/PhyKIT。"""
    issues: list[str] = []
    # 不可见/对抗字符
    for ch, desc in _INVISIBLE.items():
        if ch in text:
            issues.append(f"含不可见字符 {desc}（AI 生成文件常见，会导致 iTOL 静默解析失败）")
    if any(ord(c) < 32 and c not in "\t\n\r" for c in text):
        issues.append("含控制字符")
    # 括号平衡
    if text.count("(") != text.count(")"):
        issues.append(f"括号不平衡（( {text.count('(')} vs ) {text.count(')')}）")
        return issues  # 括号不平衡就没法解析，提前返回
    try:
        root = parse_newick(text)
    except ItolError as e:
        issues.append(str(e))
        return issues
    allnodes = root.iter()
    leaves = [n for n in allnodes if n.is_leaf]
    internal = [n for n in allnodes if not n.is_leaf]
    # 重复叶名
    names = [n.name for n in leaves if n.name]
    seen: set[str] = set()
    dups: set[str] = set()
    for n in names:
        if n in seen:
            dups.add(n)
        seen.add(n)
    if dups:
        issues.append(f"重复叶标签：{', '.join(sorted(dups)[:5])}{' 等' if len(dups) > 5 else ''}")
    # 空叶名
    if any(not n.name for n in leaves):
        issues.append("存在空叶标签")
    # 负支长
    if any(n.bl is not None and n.bl < 0 for n in allnodes):
        issues.append("存在负支长（iTOL 会拒绝）")
    # 多根
    if len(root.children) == 1:
        issues.append("根节点只有一个子（疑似多根/未解决）")
    # 多叉
    poly = sum(1 for n in internal if len(n.children) > 2)
    if poly:
        issues.append(f"含 {poly} 个多叉节点（iTOL 对多叉渲染/着色有坑，建议 resolve）")
    return issues


def tree_stats_text(text: str) -> dict:
    """树统计摘要（gotree stats / PhyKIT 思路）。返回 dict。"""
    root = parse_newick(text)
    allnodes = root.iter()
    leaves = [n for n in allnodes if n.is_leaf]
    internal = [n for n in allnodes if not n.is_leaf]
    bls = [n.bl for n in allnodes if n.bl is not None]
    supports = []
    for n in internal:
        if n.name:
            try:
                supports.append(float(n.name))
            except ValueError:
                pass
    poly = sum(1 for n in internal if len(n.children) > 2)

    def height(n: Node) -> float:
        if n.is_leaf:
            return 0.0
        return max((c.bl or 0.0) + height(c) for c in n.children)

    return {
        "tips": len(leaves),
        "internal": len(internal),
        "total_nodes": len(allnodes),
        "polytomy": poly,
        "has_brl": any(bls),
        "sum_brlen": sum(bls) if bls else 0.0,
        "mean_brlen": (sum(bls) / len(bls)) if bls else 0.0,
        "tree_height": height(root),
        "n_support": len(supports),
        "min_support": min(supports) if supports else None,
        "rooted": len(root.children) >= 2,
    }


def midpoint_reroot(root: Node) -> Node:
    """中点定根（midpoint rooting）。

    ⚠️ 当前为保守实现：完整重挂涉及在最长路径中点劈边插新根，实现复杂。
    本版本暂返回原树并提示——精确 midpoint reroot 建议用 `ete3`（itol tree reroot --midpoint 会在装了 ete3 时调用）。
    """
    return root


def dist_from_root(n: Node, root: Node) -> float:
    d = 0.0
    while n is not None and n is not root:
        d += n.bl or 0.0
        n = n.parent  # type: ignore[assignment]
    return d


def prune(root: Node, keep: set[str] | None = None, remove: set[str] | None = None) -> Node:
    """剪枝：keep=保留这些叶（其余删）或 remove=删这些叶。"""
    def filt(n: Node) -> Node | None:
        if n.is_leaf:
            if keep is not None:
                return n if n.name in keep else None
            if remove is not None:
                return None if n.name in remove else n
            return n
        n.children = [c for c in (filt(c) for c in n.children) if c is not None]
        for c in n.children:
            c.parent = n
        if not n.children:
            return None
        if len(n.children) == 1:  # 去二度节点
            c = n.children[0]
            c.bl = (c.bl or 0.0) + (n.bl or 0.0)
            c.parent = n.parent
            return c
        return n
    out = filt(root)
    if out is None:
        raise invalid_input("prune 后树为空（keep/remove 名单与树无交集）")
    out.parent = None
    return out


def rename(root: Node, mapping: dict[str, str]) -> int:
    """按映射重命名叶标签。返回改了几个。"""
    n = 0
    for leaf in root.leaves():
        if leaf.name in mapping:
            leaf.name = mapping[leaf.name]
            n += 1
    return n


def monophyly_groups(root: Node, groups: dict[str, list[str]]) -> list[tuple[str, bool, str]]:
    """单系检验：每个分组是否单系。返回 [(组名, 是否单系, 说明)]。"""
    results = []
    leafmap = {n.name: n for n in root.leaves()}
    for gname, members in groups.items():
        present = [leafmap[m] for m in members if m in leafmap]
        if len(present) < 2:
            results.append((gname, True, f"组内<2 个成员在树中（{len(present)}/{len(members)}）"))
            continue
        # 找这些叶的 LCA，看 LCA 的后代叶是否全在该组
        lca = _lca(present)
        if lca is None:
            results.append((gname, False, "无法定位共同祖先"))
            continue
        lca_leaves = {n.name for n in lca.leaves()}
        extra = lca_leaves - set(members)
        if extra:
            results.append((gname, False, f"非单系：共同祖先下混入 {len(extra)} 个外组叶（如 {sorted(extra)[:3]}）"))
        else:
            results.append((gname, True, f"单系 ✓（{len(present)} 叶）"))
    return results


def _lca(nodes: list[Node]) -> Node | None:
    """多个节点的最近共同祖先。"""
    if not nodes:
        return None
    paths: list[list[Node]] = []
    for n0 in nodes:
        p: list[Node] = []
        n2: Node | None = n0
        while n2 is not None:
            p.append(n2)
            n2 = n2.parent
        paths.append(p)
    # 第一条路径上找在所有路径里的最深节点
    for cand in paths[0]:
        if all(cand in p for p in paths[1:]):
            return cand
    return None


def draw_ascii(root: Node, width: int = 60) -> str:
    """终端 ASCII 树速览（gotree draw text 思路）。返回字符串。"""
    lines: list[str] = []

    def rec(n: Node, prefix: str, is_last: bool) -> None:
        connector = "└── " if is_last else "├── "
        label = n.name or ("·" if n.is_leaf else "")
        bl = f" :{n.bl:g}" if n.bl is not None else ""
        lines.append(prefix_holder[0] + connector + label + bl)
        extension = "    " if is_last else "│   "
        old = prefix_holder[0]
        prefix_holder[0] = old + extension
        for i, c in enumerate(n.children):
            rec(c, prefix_holder[0], i == len(n.children) - 1)
        prefix_holder[0] = old

    prefix_holder = [""]
    label = root.name or "root"
    lines.append(label + (f" :{root.bl:g}" if root.bl is not None else ""))
    for i, c in enumerate(root.children):
        rec(c, "", i == len(root.children) - 1)
    out = "\n".join(lines)
    if len(out.splitlines()) > 100:
        out = "\n".join(out.splitlines()[:100]) + f"\n… （{len(lines)-100} 行省略）"
    _ = width
    return out


def load_tree(path: Path) -> tuple[str, Node]:
    """读树文件并解析。返回 (原文, 根节点)。"""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return text, parse_newick(text)


def reroot_outgroup(root: Node, outgroup_names: set[str]) -> Node:
    """在 outgroup（这些叶的 MRCA 分支）上方重定根。返回新根。

    算法：找 target（outgroup 叶的 MRCA），翻转 target→旧根路径上的父子关系，
    新根挂在 target 与其原父之间的边上（支长中点）。对标 gotree reroot --outgroup。
    """
    targets = [n for n in root.leaves() if n.name in outgroup_names]
    if not targets:
        raise invalid_input(f"outgroup {sorted(outgroup_names)} 都不在树中")
    target = _lca(targets) or targets[0]
    if target is root or target.parent is None:
        return root
    # 路径 target → ... → root
    path: list[Node] = []
    n: Node | None = target
    while n is not None:
        path.append(n)
        n = n.parent
    # path[0]=target ... path[-1]=root；逐对翻转
    # 新根 = 挂 target 和「翻转后的其余部分」的二叉根
    new_root = Node(name="")
    half = (target.bl or 0.0) / 2.0
    # 翻转：从 target.parent 往上，每个节点的父子关系倒过来
    # path[1] 是 target 的原父；让 path[i+1] 变成 path[i] 的父
    # 先摘出 target
    old_parent = path[1]
    if target in old_parent.children:
        old_parent.children.remove(target)
    target.parent = new_root
    target.bl = half
    new_root.children.append(target)
    # 翻转路径 path[1..]：path[i] 的父变成 path[i+1] 的... 这里用递归翻转
    _flip_path(path[1:], new_root, half)
    return new_root


def _flip_path(chain: list[Node], new_root: Node, first_bl: float) -> None:
    """把 chain=[旧父, ..., 旧根] 翻转后挂到 new_root 下。

    chain[0]（target 的旧父）翻转后其父是 chain[1]，...，旧根成为最末端。
    最顶端节点（翻转后无父）挂到 new_root。
    """
    # 反转：chain[-1]（旧根）成为链底，其父是 chain[-2]
    # 逐个重挂：对 i 从 len-1 到 1，chain[i-1] 的父 = chain[i]
    for i in range(len(chain) - 1, 0, -1):
        parent = chain[i]      # 更靠近旧根
        child = chain[i - 1]   # 更靠近 target
        # child 原来的父是 parent；翻转后 child 变成 parent 的父
        if child in parent.children:
            parent.children.remove(child)
        # child 原来在 parent 下的支长 = child.bl；翻转后 parent 挂在 child 下，支长取 parent.bl
        parent.parent = child
        child.children.append(parent)
        parent.bl = child.bl
    # 链底（翻转后 chain[0]，即 target 的旧父）挂到 new_root
    top = chain[0]
    top.parent = new_root
    top.bl = first_bl
    new_root.children.append(top)
    # 旧根若变成单叉，压扁
    old_root = chain[-1]
    if len(old_root.children) == 1:
        only = old_root.children[0]
        only.bl = (only.bl or 0.0) + (old_root.bl or 0.0)
        # 把 only 接到 old_root.parent
        gp = old_root.parent
        if gp is not None and old_root in gp.children:
            gp.children.remove(old_root)
            only.parent = gp
            gp.children.append(only)


def tree_to_svg(root: Node, width: int = 900, leaf_h: int = 22, use_brl: bool = True) -> str:
    """纯 Python 本地树→SVG 渲染（零依赖、离线）。对标 gotree draw svg / nw_display。

    矩形系统树（phylogram：支长真实；use_brl=False 时 cladogram：等深）。
    供 render --backend local 离线降级/快速预览。
    """
    leaves = root.leaves()
    n = len(leaves)
    height = max(80, n * leaf_h + 60)
    # y 坐标：叶按顺序，内部节点=子节点均值
    ymap: dict[int, float] = {}

    def assign_y(node: Node) -> float:
        if node.is_leaf:
            ymap[id(node)] = 40 + leaves.index(node) * leaf_h
        else:
            assign_y_children = [assign_y(c) for c in node.children]
            ymap[id(node)] = sum(assign_y_children) / len(assign_y_children)
        return ymap[id(node)]
    assign_y(root)
    # x 坐标：累计支长（或等深）
    xmax = 0.0

    def assign_x(node: Node, acc: float) -> None:
        nonlocal xmax
        xmax = max(xmax, acc)
        for c in node.children:
            step = (c.bl or 0.0) if use_brl else 1.0
            assign_x(c, acc + step)
    assign_x(root, 0.0)
    if xmax <= 0:
        xmax = 1.0
    draw_w = width - 180  # 留叶标签空间

    def sx(acc: float) -> float:
        return 20 + (acc / xmax) * draw_w

    svg_open = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="monospace" font-size="13">'
    parts = [svg_open, f'<rect width="{width}" height="{height}" fill="white"/>']

    def draw(node: Node, acc: float) -> None:
        x0 = sx(acc)
        y0 = ymap[id(node)]
        for c in node.children:
            step = (c.bl or 0.0) if use_brl else 1.0
            x1 = sx(acc + step)
            y1 = ymap[id(c)]
            # 横线（父→子的支长）
            parts.append(f'<line x1="{x0:.1f}" y1="{y1:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#333" stroke-width="1.2"/>')
            # 竖线（父节点连接各子的 y 范围）
            parts.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x0:.1f}" y2="{y1:.1f}" stroke="#333" stroke-width="1.2"/>')
            draw(c, acc + step)
        if node.is_leaf and node.name:
            parts.append(f'<text x="{x0+5:.1f}" y="{y0+4:.1f}" fill="#111">{_xml_escape(node.name)}</text>')
        elif node.name and not node.is_leaf:
            parts.append(f'<text x="{x0+3:.1f}" y="{y0-4:.1f}" fill="#888" font-size="11">{_xml_escape(node.name)}</text>')
    draw(root, 0.0)
    parts.append('</svg>')
    return "\n".join(parts)


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
