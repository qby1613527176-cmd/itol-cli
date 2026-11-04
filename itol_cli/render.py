"""浏览器自动化渲染：Xvfb 虚拟显示 + playwright headful Chrome 驱动 iTOL 树页出带注解图。

突破点（2026-11-04）：iTOL 渲染引擎全在浏览器端，无头 SwiftShader 跑不动树页（~1MB JS），
但 Xvfb 虚拟显示 + headful Chrome 可正常加载并 exportSVG。这是免费档出带注解图的唯一程序化路。

坑位：DATASET_* 注解必须含 DATASET_LABEL 头行，否则 iTOL handler 静默拒绝注册
（错误只进 UI 解析日志面板，无异常无返回值）。本模块注入前自动补 + 注册后校验。
"""
from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .errors import ItolError

CHROME = "/usr/bin/google-chrome"


def ensure_display(argv: list[str]) -> None:
    """有 DISPLAY 直接返回；无则 xvfb-run 重跑本命令（结束后 SystemExit 替换当前进程）。"""
    if os.environ.get("DISPLAY"):
        return
    if not shutil.which("xvfb-run"):
        raise ItolError("IT006", "itol render 需显示环境或 xvfb（虚拟显示）",
                        diagnosis="apt install xvfb；或改在有显示的环境跑")
    code = subprocess.call(["xvfb-run", "-a", "--server-args=-screen 0 1600x1200x24",
                            sys.executable, "-m", "itol_cli.cli", *argv])
    raise SystemExit(code)


def _ensure_dataset_label(path: str) -> str:
    """DATASET_* 文件缺 DATASET_LABEL 则补（生成器本应已带，这里是安全网）。返回文件内容。"""
    txt = Path(path).read_text(encoding="utf-8")
    lines = txt.splitlines()
    if not lines or not lines[0].startswith("DATASET_"):
        return txt  # TREE_COLORS/LABELS 等非数据集类不需要
    if "DATASET_LABEL" in "\n".join(lines[:20]):
        return txt  # 已有
    lines.insert(1, f"DATASET_LABEL\t{Path(path).stem}")
    return "\n".join(lines) + "\n"


def render(tree_id: str, anno_files: list, out_svg: str | Path,
           out_png: str | Path | None = None, wait: int = 60,
           viewport: tuple[int, int] = (1600, 1200)) -> dict:
    """核心渲染：加载树页 → 注入注解 → exportSVG。

    返回 {injected:{文件名:bool}, svg, svg_chars, pageerrors, png?, png_warn?, ok}。
    ok = 全部注解注入确认；单个失败不抛（由 CLI 汇总），硬失败（模型未就绪/导出失败）抛 ItolError。
    """
    try:
        from playwright.sync_api import Error as PWError
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ItolError("IT006", "itol render 需要 playwright（浏览器自动化渲染路）",
                        diagnosis="pip install playwright") from None
    url = f"https://itol.embl.de/tree/{tree_id}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, executable_path=CHROME,
                                    args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(repr(e)[:200]))
        try:
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
            ready = False
            for _ in range(max(1, wait // 2)):
                time.sleep(2)
                try:
                    ready = bool(page.evaluate(
                        "() => typeof project!=='undefined'&&project&&"
                        "typeof project.exportSVG==='function'&&"
                        "typeof treeData!=='undefined'&&typeof lI1lll1==='function'"))
                except PWError:
                    ready = False  # 轮询期间瞬时 JS/上下文错误=未就绪，继续等
                if ready:
                    break
            if not ready:
                raise ItolError("IT003", f"iTOL 树页数据模型 {wait}s 未就绪",
                                diagnosis="查树 ID 有效性/网络；大树（千叶级）可加 --wait")
            injected: dict[str, bool] = {}
            for f in anno_files:
                b64 = base64.b64encode(_ensure_dataset_label(f).encode()).decode()
                pre = page.evaluate("() => Object.keys(currentData.info.datasets||{}).length")
                r = page.evaluate(
                    """(b64) => { try { lI1lll1({name:'a.txt',type:'text/plain',
                         data:'data:text/plain;base64,'+b64}); return 'ok'; }
                       catch(e){ return 'ERR '+e; } }""", b64)
                time.sleep(1.5)
                post = page.evaluate("() => Object.keys(currentData.info.datasets||{}).length")
                tcp = page.evaluate("() => !!tree_changes_pending")
                injected[Path(f).name] = (r == "ok") and (post > pre or tcp)
            time.sleep(2)  # flush 渲染循环
            svg = page.evaluate(
                """() => { try { var a=project.exportSVG();
                     return new XMLSerializer().serializeToString(a); }
                   catch(e){ return 'ERR '+e; } }""")
            if not (isinstance(svg, str) and svg.startswith("<")):
                raise ItolError("IT003", f"exportSVG 失败：{str(svg)[:200]}")
            Path(out_svg).write_text(svg, encoding="utf-8")
            result: dict = {"injected": injected, "svg": str(out_svg),
                            "svg_chars": len(svg), "pageerrors": len(errors),
                            "ok": all(injected.values())}
            if out_png:
                if shutil.which("rsvg-convert"):
                    subprocess.run(["rsvg-convert", "-b", "white", "-w", "1600", str(out_svg), "-o", str(out_png)],
                                   check=True, capture_output=True)
                    result["png"] = str(out_png)
                else:
                    result["png_warn"] = "rsvg-convert 未装，跳过 PNG（apt install librsvg2-bin）"
            return result
        finally:
            browser.close()
