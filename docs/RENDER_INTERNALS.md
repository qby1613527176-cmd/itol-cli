# iTOL 内部机制与程序化接口（2026-11-04 深挖两轮代理成果）

> 来源：itol_all.min.js（998KB）静态逆向 + CGI 端点枚举实证。字节偏移可复核。
> 配套：EXPORT_PARAMS.md（batch_downloader 83 参数全表）。

## 一、渲染核心机制（浏览器端）

- iTOL 渲染 **100% 在浏览器**（paper.js 场景图），服务端只存裸树 + 转格式
- 注解解析：FileReader 读文件 → `lI1lll1` 分发器按首行关键字分发到各 handler
- 导出：`project.exportSVG()` 序列化整个 paper.js 场景图（含 datasetHolder Group），**导出端零过滤**
- **关键坑**：DATASET_* 注解缺 `DATASET_LABEL` 头行 → handler 静默拒绝注册（错误只进 UI 日志面板，无异常无返回值）
- 浏览器渲染路已固化：`itol render`（Xvfb+playwright headful Chrome，itol_cli/render.py）

## 二、视图状态对象 l1I1l（全局单例，~150 键）

- 位置：itol_all.min.js 字节偏移 ~534630（`var l1I1l={ll11I:1,...`），全文 3013 处引用
- 这是控制树页一切显示参数的总开关（视图/色带/分组/阈值）
- 持久化：treeSaveView.cgi 存 `feat=JSON.stringify(l1I1l)`（订阅墙）；数据集内容走 saveTreeData.cgi（订阅墙）
- **显示模式键**：`l1I1l.III111I`（1=矩形 2=环形 3=无根）

## 三、树操作 JS 函数（出图形态控制）

| 操作 | 函数（混淆名） | 偏移 | 重渲 |
|---|---|---|---|
| reroot 重定根 | `l1IlII(nodeID, silent)` | @612897 | 自带全量重算+重绘 |
| 删除节点 | `IIl11ll(nodeID, silent)` | @612553 | 外层调 llII1ll |
| collapse 折叠 | `I1I1I11l(nodeID, silent)` | @605845 | silent=false 自动重渲 |
| 执行 prune | `lIIl1l1l()`（先填 `l1I1l.I1llIl=[leafIDs]`） | @609k | — |
| 一键展开+清旋转 | `IlIIl(datasetID)` | @526317 | 末尾 III1llI+llIlI1 |
| 旋转标记 | 节点属性 `d.rot` | — | — |

- 重渲铁律：collapse/清除走 `III1llI()` + `llIlI1()` 双调用；prune 取消走 `view.draw()`

## 四、程序化 CGI 接口（cgi_all.txt 31 + cgi_gen.txt 43 全枚举）

### 注解/范围写入口（需登录+树所有权，订阅墙部分）
- `/ajax/dsRemove.cgi` — 删数据集：POST `tid=<tree_id>&i=<dataset_idx>` **实锤可用**
- `/ajax/dsLabelUpdate.cgi` — 改数据集 label（inplace editor）
- `/ajax/dsSaveDefaults.cgi` — 存数据集参数为默认
- `/ajax/rangeLabelUpdate.cgi` / `rangeRemove.cgi` / `rangeSaveDefaults.cgi` — 色带 range 改/删/存
- ⚠️ `saveTreeData.cgi` / `treeSaveView.cgi` — 存数据集内容/视图：**500 订阅墙**

### 树操作端点
- `/ajax/getMidpointRoot.cgi` — **中点根化免费路**：POST `i=<tree_id>` 返回新树文本
- `/ajax/assign_tax.cgi` / `assign_tax_gtdb.cgi` — NCBI/GTDB 分类自动注释：POST `tree=<tree_id>`
- `/ajax/assign_tax_from_anno.cgi` — 从既有注解提分类

### 导出链路
- `/ajax/export.cgi` — 位图/PDF 导出（队列制）：POST `id&nm&fmt&dpi&m(margin)&a(area)&q=SVG XML`；inQueue→poll
- `/ajax/exportQueueCheck.cgi` — POST `id=exportID` 轮询；`/ajax/cancelQueueJob.cgi` 取消
- `/download.cgi?f=<file>` — 取文件口
- `/ajax/exportText.cgi` — 文本导出（带 label_background/ranges JSON/元数据格式/排序/旋转参数）

### 账号/管理（43 个 /ajax/personal/）
- workspace_add/edit/remove/order、project_add/remove/settings/sharing、tree_uploader/tree_edit/tree_remove/tree_lock/tree_star、privateSharing、copySharedTree、duplicate_tree、treeSearchGrid 等
- 已实证可用：login.cgi、personal_page.cgi（var ws）、tree_uploader.cgi

## 五、数据集类型（23 种 DATASET_*）

- JS 共 23 种 DATASET_*；官方模板 30 个（含非 dataset 类型）
- **新发现 2 种 survey3 未覆盖**：`DATASET_LABEL`、`DATASET_SCALE`
- 内部节点引用语法：`ID1|ID2`（LCA）
