"""账号通路：iTOL 登录 / 工作区 / 树文本上传（免费账号可用，源码实证端点）。

与 client.py（订阅制 batch 三 CGI）互补：
- 登录：login.cgi {login,pwd,submit} → itolsession cookie（约 2h 有效）
- 工作区：personal_page.cgi 内嵌 `var ws=[...]` JSON（Workspace→Project→Tree 三层）
- 树上传（文本）：POST /ajax/personal/tree_uploader.cgi {pid,tNm,tTxt} → JSON 树 ID

⚠️ 注解挂树无服务端端点（iTOL 渲染引擎全在浏览器端，FileReader 客户端读入）——
本模块不含注解挂树；出带注解图需订阅 batch_uploader 或浏览器自动化。
"""
import json
import re
import time
from http.cookiejar import LoadError, MozillaCookieJar
from pathlib import Path

import requests

from .errors import ItolError

LOGIN_URL = "https://itol.embl.de/login.cgi"
PERSONAL_URL = "https://itol.embl.de/personal_page.cgi"
TREE_UPLOADER_URL = "https://itol.embl.de/ajax/personal/tree_uploader.cgi"
EXPORT_CGI_URL = "https://itol.embl.de/ajax/export.cgi"
EXPORT_QUEUE_URL = "https://itol.embl.de/ajax/exportQueueCheck.cgi"
DOWNLOAD_URL = "https://itol.embl.de/download.cgi"
CONFIG_DIR = Path.home() / ".itol-cli"
CONFIG_FILE = CONFIG_DIR / "config"
SESSION_FILE = CONFIG_DIR / "session_cookies"


def load_config() -> dict:
    """读 ~/.itol-cli/config（KEY=VALUE 行式；权限应 600）。"""
    cfg = {}
    if CONFIG_FILE.is_file():
        for ln in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, _, v = ln.partition("=")
                cfg[k.strip()] = v.strip()
    return cfg


class AccountClient:
    """iTOL 账号会话客户端（免费账号可用部分）。"""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "itol-cli/0.1 (+https://github.com/; academic)"
        if SESSION_FILE.is_file():
            jar = MozillaCookieJar(str(SESSION_FILE))
            try:
                jar.load(ignore_discard=True, ignore_expires=True)
                self.session.cookies = jar  # type: ignore[assignment]
            except (OSError, LoadError):
                pass

    def _save_session(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        jar = MozillaCookieJar(str(SESSION_FILE))
        for c in self.session.cookies:
            jar.set_cookie(c)
        jar.save(ignore_discard=True, ignore_expires=True)
        SESSION_FILE.chmod(0o600)

    # ---- 登录 ----
    def login(self, user: str, password: str) -> str:
        """POST login.cgi → itolsession cookie；返回登录用户名。失败抛 ItolError(IT004)。"""
        self.session.post(LOGIN_URL, data={"login": user, "pwd": password, "submit": "Sign in"},
                          allow_redirects=False, timeout=30)
        if not self.logged_in():
            raise ItolError("IT004", "登录失败：账号或密码错误（响应无会话 cookie）")
        self._save_session()
        return user

    def logged_in(self) -> bool:
        # MozillaCookieJar 迭代出 Cookie 对象而非名字，必须用名字匹配（「in jar」会永远 False）
        return any(c.name == "itolsession" for c in self.session.cookies)

    def whoami(self) -> str:
        """会话里取用户名（personal_page.cgi 顶栏 hdrUname）；未登录返回空串。"""
        if not self.logged_in():
            return ""
        r = self.session.get(PERSONAL_URL, timeout=30)
        m = re.search(r"id='hdrUname'[^>]*>([^<]+)<", r.text)
        return m.group(1).strip() if m else ""

    # ---- 工作区 ----
    def workspaces(self) -> list:
        """解析 personal_page.cgi 内嵌 var ws=[...] JSON → 工作区列表。"""
        if not self.logged_in():
            raise ItolError("IT004", "未登录（先 itol login）")
        r = self.session.get(PERSONAL_URL, timeout=30)
        m = re.search(r"var ws = (\[.*?\]); var views", r.text, re.DOTALL)
        if not m:
            raise ItolError("IT005", "工作区数据解析失败（personal_page.cgi 结构变更？）")
        return json.loads(m.group(1))

    def trees(self) -> list:
        """扁平化全部 (workspace, project, tree) 元组。"""
        out = []
        for w in self.workspaces():
            for p in w.get("p", []):
                for t in p.get("data", []):
                    out.append((w.get("t", ""), p.get("t", ""), p.get("id", ""), t.get("t", ""), t.get("id", "")))
        return out

    # ---- 树上传（文本模式，免费账号可用）----
    def upload_tree_text(self, project_id: str, name: str, newick: str) -> str:
        """POST tree_uploader.cgi {pid,tNm,tTxt} → 树 ID（实证免费账号可用）。"""
        if not self.logged_in():
            raise ItolError("IT004", "未登录（先 itol login）")
        if len(newick.strip()) < 5:
            raise ItolError("IT001", "树文本过短（<5 字符）")
        r = self.session.post(TREE_UPLOADER_URL,
                              data={"pid": project_id, "tNm": name, "tTxt": newick}, timeout=60)
        try:
            d = r.json()
        except ValueError:
            raise ItolError("IT005", f"上传响应非 JSON：{r.text[:120]!r}") from None
        tid = d.get("id") or (d.get("tree") or {}).get("id")
        if not tid:
            raise ItolError("IT005", f"上传未返回树 ID：{d!r}")
        return str(tid)

    # ---- 高分辨率位图导出（export.cgi 异步队列，免费账号实证可用）----
    def export_hires_png(self, svg_text: str, tree_id: str, dpi: int = 300,
                         margin: int = 0, full_image: bool = True, wait: int = 120) -> bytes:
        """POST export.cgi（q=SVG XML, dpi≤1000）→ 轮询队列 → download.cgi 取高 DPI PNG。

        2026-11-05 黑客线 E2E 实证：export.cgi 队列是补 batch_downloader 无 dpi 缺口的路。
        同会话一次只能排一个导出任务；fmt=png 唯一位图格式。
        """
        if not self.logged_in():
            raise ItolError("IT004", "高分辨率导出需登录（先 itol login）")
        r = self.session.post(EXPORT_CGI_URL, data={
            "id": tree_id, "nm": "itol-cli", "shared": "0", "fmt": "png",
            "dpi": str(dpi), "m": str(margin), "a": "1" if full_image else "0",
            "q": svg_text}, timeout=60)
        try:
            j = r.json()
        except ValueError:
            raise ItolError("IT005", f"export.cgi 响应非 JSON：{r.text[:150]!r}") from None
        qid = j.get("queueID")
        if not qid:
            raise ItolError("IT003", f"export.cgi 未入队：{j!r}")
        for _ in range(max(1, wait // 5)):
            time.sleep(5)
            chk = self.session.post(EXPORT_QUEUE_URL, data={"id": qid}, timeout=30)
            try:
                cj = chk.json()
            except ValueError:
                continue
            if cj.get("file"):
                d = self.session.get(DOWNLOAD_URL, params={"f": cj["file"]}, timeout=60)
                if d.content[:4] == b"\x89PNG":
                    return d.content
                raise ItolError("IT003", f"下载结果非 PNG：{d.text[:150]!r}")
            if cj.get("inQueue") == -1:
                raise ItolError("IT003", "export.cgi 转换失败（队列返回 inQueue=-1）")
        raise ItolError("IT003", f"高分辨率导出超时（队列 {wait}s 未完成）")
