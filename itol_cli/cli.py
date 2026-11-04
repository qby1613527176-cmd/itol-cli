"""itol — iTOL 命令行工具（模板生成 / lint 校验 / 上传导出流水线）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from . import __version__
from . import render as _render
from .account import AccountClient, load_config
from .client import EXPORT_FORMATS, ItolClient
from .errors import ItolError
from .lint import lint_paths
from .templates import (
    BOOTSTRAP_EXPORT_PRESET,
    TEMPLATES,
    write_connections,
    write_domains,
    write_heatmap,
    write_pav,
    write_selection,
    write_subfamily,
    write_timescale,
)


def _load_key() -> str:
    """APIkey 解析：环境变量 ITOL_API_KEY > ~/.itol-cli/config（key=value 行）。"""
    k = os.environ.get("ITOL_API_KEY", "").strip()
    if k:
        return k
    cfg = Path.home() / ".itol-cli" / "config"
    if cfg.is_file():
        for ln in cfg.read_text(encoding="utf-8").splitlines():
            if ln.strip().upper().startswith("ITOL_API_KEY"):
                return ln.split("=", 1)[1].strip()
    return ""


def _client() -> ItolClient:
    return ItolClient(api_key=_load_key())


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="itol")
def main() -> None:
    """itol — iTOL 注解模板生成 + 校验 + 上传/导出流水线。"""


@main.command()
def doctor() -> None:
    """环境自检：API key / 端点存活 / 导出探测。"""
    key = _load_key()
    click.echo(f"{'✅' if key else '⚠️ '} API key: {'已配置' if key else '未配置（上传/删除不可用，导出不受影响）'}")
    # 端点探活：无参 GET batch_uploader → 预期 ERR 0（key 缺失）即端点通（调研实证形态）
    try:
        import requests
        r = requests.get("https://itol.embl.de/batch_uploader.cgi", timeout=15)
        alive = "ERR 0" in r.text or "API key" in r.text
        click.echo(f"{'✅' if alive else '❌'} 上传端点存活: {alive}（HTTP {r.status_code}）")
    except requests.RequestException as e:
        click.echo(f"❌ 上传端点不可达: {e}")
    click.echo("导出端点免认证（公开树按 ID 导出）：itol export <tree_id> --format svg --out tree.svg")


@main.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
def lint(files: list) -> None:
    """本地校验 iTOL 注解文件（手写/AI 生成模板的第一道关）。"""
    if not files:
        raise click.UsageError("itol lint <注解文件...>")
    reports = lint_paths(list(files))
    for r in reports:
        click.echo(r.summary())
    if any(not r.ok for r in reports):
        sys.exit(1)
    click.echo(f"\n全部通过（{len(reports)} 文件）")


@main.command()
@click.argument("scenario", type=click.Choice(sorted(TEMPLATES)))
@click.argument("input_file", required=False, type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--outdir", type=click.Path(path_type=Path), default=Path.cwd(), show_default=True)
@click.option("--tree", type=click.Path(exists=True, path_type=Path), default=None,
              help="树文件（newick）；heatmap 场景用于行序校验重排")
def gen(scenario: str, input_file: Path, outdir: Path, tree: Path) -> None:
    """场景模板生成（itol templates 看全量场景与输入规范）。"""
    spec = TEMPLATES[scenario]
    if scenario == "bootstrap":
        click.echo("bootstrap 展示无需注解文件——iTOL 内置 metadata 四态。导出时带以下参数：")
        for k, v in BOOTSTRAP_EXPORT_PRESET.items():
            click.echo(f"  --param {k}={v}")
        return
    if not input_file:
        raise click.UsageError(f"itol gen {scenario} <输入文件>\n输入规范：{spec.inputs}")
    if scenario == "subfamily":
        outs = write_subfamily(input_file, outdir)
        click.echo("已生成：")
        for p in outs:
            click.echo(f"  {p}")
    elif scenario in ("domains", "motif"):
        outs = write_domains(input_file, outdir,
                             label="Domains" if scenario == "domains" else "Motifs")
        click.echo("已生成：")
        for p in outs:
            click.echo(f"  {p}")
    elif scenario == "selection":
        outs = write_selection(input_file, outdir)
        click.echo("已生成：")
        for p in outs:
            click.echo(f"  {p}")
    elif scenario == "connections":
        outs = write_connections(input_file, outdir)
        click.echo("已生成：")
        for p in outs:
            click.echo(f"  {p}")
    elif scenario == "timescale":
        outs = write_timescale(input_file, outdir)
        click.echo("已生成：")
        for p in outs:
            click.echo(f"  {p}")
    elif scenario == "pav":
        leaves = None
        if tree:
            import re
            text = tree.read_text(encoding="utf-8")
            leaves = [t.strip().strip("'\"") for t in re.findall(r"([A-Za-z0-9_.\-|]+):[0-9.eE\-]+", text)]
        outs, missing = write_pav(input_file, outdir, leaves)
        click.echo("已生成：")
        for p in outs:
            click.echo(f"  {p}")
        if missing:
            click.echo(f"⚠️ 树中 {len(missing)} 个叶在矩阵里找不到（已跳过）", err=True)
    elif scenario == "heatmap":
        leaves = None
        if tree:
            import re
            text = tree.read_text(encoding="utf-8")
            leaves = [t.strip().strip("'\"") for t in re.findall(r"([A-Za-z0-9_.\-]+):[0-9.eE\-]+", text)]
        outs, missing = write_heatmap(input_file, outdir, leaves)
        click.echo("已生成：")
        for p in outs:
            click.echo(f"  {p}")
        if missing:
            click.echo(f"⚠️ 树中 {len(missing)} 个叶在矩阵里找不到（已跳过）：{missing[:5]}{'...' if len(missing) > 5 else ''}",
                       err=True)


@main.command()
@click.argument("tree_file", type=click.Path(exists=True, path_type=Path))
@click.argument("annotations", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--project", required=True, help="iTOL 项目名（大小写敏感，须 Web UI 预先建好）")
@click.option("--name", "tree_name", default="")
def upload(tree_file: Path, annotations: list, project: str, tree_name: str) -> None:
    """上传树+注解（⚠️ 需 iTOL 标准订阅 + APIkey）。上传前自动 lint。"""
    reports = lint_paths(list(annotations))
    bad = [r for r in reports if not r.ok]
    if bad:
        for r in bad:
            click.echo(r.summary(), err=True)
        click.echo("❌ lint 未过，上传中止（先修复再传）", err=True)
        sys.exit(1)
    try:
        tid, warnings = _client().upload(tree_file, list(annotations), project, tree_name)
    except ItolError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    for w in warnings:
        click.echo(f"⚠️ {w}", err=True)
    click.echo(f"tree_id: {tid}")
    click.echo(f"url: https://itol.embl.de/tree/{tid}")
    click.echo("⚠️ 提醒：该 URL 知道 ID 即可访问（无鉴权）——未发表数据注意分享范围", err=True)


@main.command()
@click.argument("tree_id")
@click.option("--format", "fmt", type=click.Choice(EXPORT_FORMATS), default="svg", show_default=True)
@click.option("-o", "--out", type=click.Path(path_type=Path), default=None)
@click.option("--param", multiple=True, help="透传显示参数 key=value（如 --param display_mode=2 圆形树）")
def export(tree_id: str, fmt: str, out: Path, param: list) -> None:
    """导出树图（免认证）。默认 SVG——批量导出无 dpi 参数，位图高分辨率是缺口。"""
    params = {}
    for kv in param:
        if "=" not in kv:
            raise click.UsageError(f"--param 需要 key=value 形态：{kv!r}")
        k, v = kv.split("=", 1)
        params[k] = v
    if out is None:
        out = Path(f"itol_{tree_id}.{fmt}")
    try:
        data = _client().export(tree_id, fmt, out=out, **params)
    except ItolError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    click.echo(f"✅ {out}（{len(data)} bytes）")


@main.command()
@click.argument("tree_id")
def status(tree_id: str) -> None:
    """检查树 ID 是否存在于 iTOL。"""
    exists = _client().tree_exists(tree_id)
    click.echo(("✅ 存在" if exists else "❌ 不存在或已过期") + f"：https://itol.embl.de/tree/{tree_id}")
    if not exists:
        sys.exit(1)


@main.command()
@click.argument("tree_id")
@click.confirmation_option(prompt="删除不可恢复，确认？")
def delete(tree_id: str) -> None:
    """删除 iTOL 上的树（⚠️ 需订阅+key；不可恢复）。"""
    try:
        _client().delete(tree_id)
    except ItolError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    click.echo(f"已删除 {tree_id}")


@main.command()
def templates() -> None:
    """场景模板库（每模板=输入规范+生成脚本+预设参数）。"""
    for name in sorted(TEMPLATES):
        t = TEMPLATES[name]
        click.echo(f"\n■ {t.name} — {t.summary}")
        click.echo(f"  输入：{t.inputs}")
        click.echo(f"  产出：{'；'.join(t.outputs)}")


# ---------------- 账号通路（免费账号可用，2026-11-03 破解登录/文本上传）----------------


@main.command()
@click.option("--user", default=None, help="iTOL 账号（缺省读 ~/.itol-cli/config 的 ITOL_USER 或提示输入）")
@click.option("--password", default=None, help="密码（缺省读 config 的 ITOL_PASSWORD 或提示输入）")
def login(user: str | None, password: str | None) -> None:
    """登录 iTOL 账号（会话 cookie 存 ~/.itol-cli/session_cookies，600 权限，约 2h 有效）。"""
    cfg = load_config()
    user = user or cfg.get("ITOL_USER") or click.prompt("iTOL 账号")
    password = password or cfg.get("ITOL_PASSWORD") or click.prompt("密码", hide_input=True)
    acc = AccountClient()
    try:
        name = acc.login(user, password)
        click.echo(f"✅ 已登录：{name}（会话已保存到 ~/.itol-cli/session_cookies）")
    except ItolError as e:
        click.echo(f"❌ {e}", err=True)
        raise SystemExit(1) from None


@main.command()
def whoami() -> None:
    """查看当前登录账号。"""
    acc = AccountClient()
    if not acc.logged_in():
        click.echo("❌ 未登录（先 itol login）", err=True)
        raise SystemExit(1)
    name = acc.whoami()
    click.echo(f"✅ {name}" if name else "⚠️ 会话可能已过期，重新 itol login")


@main.command()
def workspaces() -> None:
    """列出账号的工作区/项目/树（工作区→项目→树三层）。"""
    acc = AccountClient()
    try:
        ws = acc.workspaces()
        for w in ws:
            click.echo(f"■ 工作区 {w.get('t', '?')} (id={w.get('id', '?')})")
            for p in w.get("p", []):
                n = len(p.get("data", []))
                click.echo(f"  └ 项目 {p.get('t', '?')} (id={p.get('id', '?')})：{n} 棵树")
                for t in p.get("data", []):
                    click.echo(f"      └ {t.get('t', '?')} (id={t.get('id', '?')})")
    except ItolError as e:
        click.echo(f"❌ {e}", err=True)
        raise SystemExit(1) from None


@main.command(name="upload-tree")
@click.argument("tree_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--project", "project_id", required=True, help="目标项目 ID（itol workspaces 查）")
@click.option("--name", default=None, help="树名（缺省用文件名）")
def upload_tree(tree_file: Path, project_id: str, name: str | None) -> None:
    """把树文本上传到账号项目（免费账号可用；注解挂树需订阅 batch_uploader 或浏览器自动化）。"""
    acc = AccountClient()
    name = name or tree_file.stem
    try:
        tid = acc.upload_tree_text(project_id, name, tree_file.read_text(encoding="utf-8"))
        click.echo(f"✅ 树已上传：id={tid}\n   查看：https://itol.embl.de/tree/{tid}")
    except ItolError as e:
        click.echo(f"❌ {e}", err=True)
        raise SystemExit(1) from None


@main.command()
@click.argument("tree_id")
@click.option("--anno", multiple=True, required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="注解文件（可多个；DATASET_* 缺 DATASET_LABEL 会自动补）")
@click.option("--out", required=True, type=click.Path(path_type=Path), help="输出 SVG 路径")
@click.option("--png", "png", default=None, type=click.Path(path_type=Path), help="可选 PNG 路径（需 rsvg-convert）")
@click.option("--wait", default=60, show_default=True, help="iTOL 数据模型等待超时（秒）")
def render(tree_id: str, anno: tuple, out: Path, png: Path | None, wait: int) -> None:
    """浏览器渲染路：注入注解到 iTOL 树页出带注解图（免费账号可用；Xvfb+playwright，自动套虚拟显示）。

    需本机有 Chrome/Chromium；无显示环境自动 xvfb-run 包裹。出带 colorstrip 等真数据集的图唯一程序化路。
    """
    _render.ensure_display(sys.argv[1:])  # 无 DISPLAY 自动 xvfb-run 重跑本命令
    try:
        result = _render.render(tree_id, list(anno), out, png, wait)
    except ItolError as e:
        click.echo(f"❌ {e}", err=True)
        raise SystemExit(1) from None
    for f, ok in result["injected"].items():
        click.echo(f"{'✅' if ok else '⚠️ '} 注入 {f}")
    click.echo(f"✅ SVG 已出：{result['svg']}（{result['svg_chars']} 字符）")
    if "png" in result:
        click.echo(f"✅ PNG 已出：{result['png']}")
    if "png_warn" in result:
        click.echo(f"⚠️ {result['png_warn']}", err=True)
    if not result["ok"]:
        click.echo("⚠️ 部分注解未确认注入（可能静默拒绝——查 DATASET_LABEL 是否缺失）", err=True)
        raise SystemExit(3)


if __name__ == "__main__":
    main()
