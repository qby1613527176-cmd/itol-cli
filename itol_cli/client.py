"""iTOL 三个 CGI 端点的客户端（调研实证规格，workflows/itol_research/agent1_api.md）。

端点事实（2026-11-02 curl 实测）：
- 上传 batch_uploader.cgi：POST，必须 APIkey（付费订阅）→ text/plain 首行 SUCCESS: <treeID> / ERR<code>
- 导出 batch_downloader.cgi：GET/POST，免认证；成功=二进制 MIME，失败=text/html 或 text/plain 错误
- 删除 batch_delete.cgi：POST，APIkey
- 页面型 URL（/tree/<id>）无效 ID 也回 200——必须解析 <title> 含 "Error"
- 官方无速率上限 → 串行 + 间隔 + 指数退避；导出走服务器队列，超时 ≥120s
"""
from __future__ import annotations

import io
import re
import time
import zipfile
from pathlib import Path

import requests

from .errors import auth_required, export_failed, upload_failed

UPLOAD_URL = "https://itol.embl.de/batch_uploader.cgi"
EXPORT_URL = "https://itol.embl.de/batch_downloader.cgi"
DELETE_URL = "https://itol.embl.de/batch_delete.cgi"
LOADTREE_URL = "https://itol.embl.de/ajax/loadTree.cgi"  # 免认证拉公开树结构+元数据（hack4 实证）
TREE_PAGE = "https://itol.embl.de/tree/{tid}"

EXPORT_FORMATS = ("svg", "eps", "pdf", "png", "newick", "nexus", "phyloxml")

# 导出参数预设（2026-11-04 深挖 83 个 batch_downloader 参数后固化，全表见 docs/EXPORT_PARAMS.md）
# --preset 可叠加，--param key=value 优先级更高（后者覆盖前者同键）
EXPORT_PRESETS = {
    "publication": {"align_labels": "1", "dashed_lines": "1", "current_font_size": "14"},
    "circular": {"display_mode": "2"},
    "unrooted": {"display_mode": "3"},
    "cladogram": {"ignore_branch_length": "1"},
    "slanted": {"display_mode": "1", "ignore_branch_length": "1", "slanted_normal": "1"},
    "bootstrap": {"bootstrap_display": "1", "bootstrap_type": "1"},
    "bootstrap-color": {"bootstrap_display": "1", "bootstrap_type": "3",
                        "bootstrap_min_color": "#0000ff", "bootstrap_max_color": "#ff0000"},
    "bootstrap-width": {"bootstrap_display": "1", "bootstrap_type": "4"},
    "timescale": {"internal_scale": "1", "internalScaleAxis": "1", "internalScaleGrid": "1"},
}
# 导出成功时的二进制 MIME（实测规格）；text/html|text/plain = 失败
_EXPORT_OK_MIME = ("image/", "application/pdf", "application/postscript", "application/octet-stream")

SUCCESS_RE = re.compile(r"^SUCCESS:\s*(\d+)", re.MULTILINE)
ERR_RE = re.compile(r"^ERR\s*(\d+)\s*(.*)")


def make_upload_zip(tree_file: Path, annotation_files: list[Path]) -> bytes:
    """打包树+注解为 zip（树文件扩展名必须 .tree/.tree.txt/.jplace——官方规格）。"""
    tree_file = Path(tree_file)
    name = tree_file.name
    if not name.endswith((".tree", ".tree.txt", ".jplace")):
        # 官方硬性要求；自动补 .tree 扩展名
        name = name + ".tree"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(name, tree_file.read_bytes())
        for af in annotation_files:
            zf.writestr(Path(af).name, Path(af).read_bytes())
    return buf.getvalue()


class ItolClient:
    """iTOL API client。serial 请求 + 指数退避；错误分层解析。"""

    def __init__(self, api_key: str | None = None, min_interval: float = 1.0, timeout: float = 120.0):
        self.api_key = api_key or ""
        self.min_interval = min_interval
        self.timeout = timeout
        self._last_call = 0.0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "itol-cli/0.1 (+https://github.com/; academic)"
    # ---- 内部 ----
    def _throttle(self) -> None:
        delta = time.time() - self._last_call
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last_call = time.time()

    def _retry(self, fn, attempts: int = 3):
        delay = 2.0
        last_exc: Exception | None = None
        for i in range(attempts):
            try:
                return fn()
            except requests.RequestException as e:  # 网络层错误可重试
                last_exc = e
                if i < attempts - 1:
                    time.sleep(delay)
                    delay *= 2
        raise last_exc  # type: ignore[misc]

    @staticmethod
    def _parse_upload_response(text: str) -> tuple[str, list[str]]:
        """返回 (tree_id, warnings)；失败抛 IT002。"""
        m = SUCCESS_RE.search(text)
        if m:
            warnings = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("SUCCESS")]
            return m.group(1), warnings
        em = ERR_RE.search(text)
        if em:
            raise upload_failed(f"iTOL ERR {em.group(1)}: {em.group(2).strip()}",
                                diagnosis="检查 zip 内容（树扩展名/注解语法）与 projectName（大小写敏感、须 Web UI 预建）")
        raise upload_failed(f"未知上传响应：{text[:200]!r}")

    # ---- 上传（需订阅） ----
    def upload(self, tree_file: Path, annotation_files: list[Path], project: str,
               tree_name: str = "", description: str = "") -> tuple[str, list[str]]:
        if not self.api_key:
            raise auth_required("批量上传")
        payload = make_upload_zip(Path(tree_file), [Path(p) for p in annotation_files])

        def call():
            self._throttle()
            return self.session.post(
                UPLOAD_URL,
                files={"zipFile": ("upload.zip", payload, "application/zip")},
                data={"APIkey": self.api_key, "projectName": project,
                      "treeName": tree_name, "treeDescription": description},
                timeout=self.timeout,
            )

        resp = self._retry(call)
        return self._parse_upload_response(resp.text)

    # ---- 导出（免认证） ----
    def export(self, tree_id: str, fmt: str, out: Path | None = None, **params) -> bytes:
        """导出树图。fmt ∈ EXPORT_FORMATS；params 透传 batch_downloader 全部显示参数。

        注意（调研实证）：无 dpi/宽高参数——高分辨率位图是缺口，默认引导矢量格式。
        """
        fmt = fmt.lower()
        if fmt not in EXPORT_FORMATS:
            raise export_failed(f"格式 {fmt!r} 不支持", diagnosis=f"可用：{','.join(EXPORT_FORMATS)}")
        q = {"tree": tree_id, "format": fmt}
        q.update(params)

        def call():
            self._throttle()
            return self.session.get(EXPORT_URL, params=q, timeout=self.timeout)

        resp = self._retry(call)
        ct = resp.headers.get("Content-Type", "")
        if any(ct.startswith(m) for m in _EXPORT_OK_MIME):
            data = resp.content
            if out:
                Path(out).write_bytes(data)
            return data
        # 失败：text/html 或 text/plain 错误文本
        text = resp.text[:300]
        raise export_failed(f"导出失败（HTTP {resp.status_code}）：{text.strip()[:160]}",
                            diagnosis="确认 tree ID 存在（itol status <id>）；格式见 itol export --help")

    # ---- 删除（需订阅） ----
    def delete(self, tree_id: str) -> None:
        if not self.api_key:
            raise auth_required("删除树")

        def call():
            self._throttle()
            return self.session.post(DELETE_URL, data={"APIkey": self.api_key, "tree": tree_id},
                                     timeout=self.timeout)

        resp = self._retry(call)
        if not SUCCESS_RE.search(resp.text):
            em = ERR_RE.search(resp.text)
            msg = em.group(2).strip() if em else resp.text[:200]
            raise upload_failed(f"删除失败：{msg}")

    # ---- 状态检查（页面型 URL 陷阱：无效 ID 也 200，须解析 title） ----
    def fetch_tree(self, tree_id: str, dataset_ids: str | None = None) -> dict:
        """POST loadTree.cgi 拉公开树的完整结构+元数据（免认证，hack4 实证）。

        返回 JSON：node（节点索引 par/kids/bl/lf）/ param（root/has_brl/tree_height）/
        info（names/label_color/node_metadata/tree_name/datasets/...）/ leaf（叶序）。
        """
        def call():
            data = {"tree": tree_id}
            if dataset_ids:
                data["batch"] = "1"
                data["ds"] = dataset_ids
            return self.session.post(LOADTREE_URL, data=data, timeout=self.timeout)
        r = self._retry(call)
        try:
            return r.json()
        except ValueError:
            raise export_failed(f"loadTree 响应非 JSON：{r.text[:150]!r}") from None

    def tree_exists(self, tree_id: str) -> bool:
        def call():
            self._throttle()
            return self.session.get(TREE_PAGE.format(tid=tree_id), timeout=self.timeout)

        resp = self._retry(call)
        m = re.search(r"<title>(.*?)</title>", resp.text, re.DOTALL)
        title = m.group(1) if m else ""
        return "Error" not in title and "Invalid tree ID" not in resp.text
