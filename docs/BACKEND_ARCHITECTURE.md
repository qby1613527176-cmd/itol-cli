# iTOL 后端架构推断（2026-11-05，黑客线 5 代理侦察，附置信度）

> 方法：发各种请求看响应特征反推后端。证据=HTTP 响应原文/JS 静态分析。置信度标注【确证/很可能/推测】。
> 配套：ATTACK_SURFACE.md（端点面）、EXPORT_PARAMS.md（参数面）、RENDER_INTERNALS.md（前端渲染）。

## 🎯 重大发现：服务端 SVG 导出 = headless browser 渲染

`GET batch_downloader.cgi?tree=abc&format=svg`（非法树）返回 400 + body：
```
Invalid SVG received from headless browser.
TypeError: undefined is not a function (evaluating 'Object.assign')   ← 无 ES6
ReferenceError: Can't find variable: ej                                ← JSCore 措辞
```

- **服务端导出走 headless browser 加载树页 → JS 渲染 → 抓 SVG DOM**【确证：错误原文】
- **引擎极老（不支持 Object.assign）+ "Can't find variable:" 措辞 = JavaScriptCore 系 → 高度疑似 PhantomJS（QtWebKit，2016 停更）**【很可能】
- CGI 把 headless 浏览器 console 错误直接回传客户端 = 信息泄露面【确证】
- **含义**：iTOL 服务端自己就用 headless browser 渲染——这和 itol-cli 的 `itol render`（Xvfb+playwright）同构，印证我们的路是对的（而且我们的 Chrome 比它的 PhantomJS 新得多，能跑它跑不动的现代 JS）

## 语言/框架指纹

| 信号 | 证据 | 推断 |
|---|---|---|
| `charset=utf8`（无连字符） | 全站响应头复现 | **Perl CGI.pm `$q->header(-charset=>'utf8')` 标志输出**【很可能，强信号】 |
| 无 X-Powered-By | 响应头 | 非 PHP；Perl/mod_perl 或裸 CGI 不主动暴露【确证】 |
| 缺参/404 → 统一自定义错误页 | `/nonexistent.cgi`、`/getMidpointRoot.cgi` 缺参、`/loadTree.cgi` 缺参全走同一模板 | **共享中央错误处理/分发模块（modulino 风格）**【很可能】 |
| 错误不泄堆栈/路径/模块名 | 错误 body 简短纯文本 | 生产模式，CGI::Carp fatalsToBrowser 未开【确证】 |
| Transfer-Encoding: chunked + Connection: close | batch_downloader 响应 | CGI 流式输出，边 print 边 flush【很可能】 |
| `Server: Apache/2.4.29 (Ubuntu)` | 响应头 | Apache 2.4.29（2018，偏旧）【确证】 |
| 版本横幅 | 错误页 `ver=7.0078` | **iTOL v7 build 0078**【确证】 |

## 前端堆栈【确证，树页 script 标签】
jQuery 3.5.1 + Bootstrap 4 + jsPanel + Syncfusion EJ2（定制 build）+ Sortable.js + paper.js + biojs-io-newick

## 导出队列机制（process 线，JS 静态分析确证）
- `POST /ajax/export.cgi`（含 export_margin/exportAreaB 等）→ JSON `{inQueue, queueID, shared, file}`
- `inQueue>=0` → 前端每 5s 轮询 `exportQueueCheck.cgi`（id=queueID）→ 完成给 `download.cgi?f=<file>` 或兜底 `/export/<file>`
- **导出是后台 worker 队列**（CGI 只入队不渲染）；`cancelQueueJob.cgi` 可取消
- ⚠️ 导出文件落地在 web 可直达的 `/export/` 路径

## 会话/认证内部（session 线，确证）
- `Set-Cookie: itolsession=<32 hex>; path=/; secure; HttpOnly; SameSite=Lax` + HSTS preload
- **会话 ID = 128bit**，登录即轮换（防 session fixation），绝对过期 +2h
- 登录成功纯 302 → personal_page.cgi，无 body
- userInfo.cgi 免登录访问 302→login.cgi（cookie 控制点）

## 树 ID 空间（storage 线，本地分析）
- 25 位十进制，前 10 位 `0000000000` 疑似用户命名空间段（两棵同属 a_free_account 的树共享）
- 后 15 位不连续、不像 epoch/自增 → **大概率随机/哈希截断**
- 含义：树 ID 不可枚举 → 分享链接（知 ID 即访问）靠不可猜测性保护，ID 不泄就安全
