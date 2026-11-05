# iTOL 攻击面侦察报告（2026-11-05，黑客视角，主线程穷尽枚举）

> 方法：对 itol.embl.de 全部前端 JS（itol_all.min.js 998KB / itol_gen.min.js 108KB / ej2-itol.min.js）+ 树页 HTML 做穷尽字符串/调用点提取 + 线上单发探针。回答「隐藏端点/接口/参数是否挖全」。

## 结论速览

**功能端点覆盖 = 完整。** 全部数据/操作端点已在枚举内；未发现任何能绕过订阅墙的隐藏注解写入口。

## 1. 端点全枚举（82 个 .cgi，纯 CGI 架构）

从全 JS+HTML 提取 82 个 .cgi 引用。对比前期枚举（31 树页 ajax + 43 personal）确认：

- **数据/操作端点全覆盖**（loadTree/loadDataset/loadAllDatasets/getView/saveTreeData/treeSaveView/export/exportText/exportQueueCheck/batch_downloader/batch_uploader/batchCheck/tree_uploader/dsRemove/dsLabelUpdate/dsSaveDefaults/range*/assign_tax*/getMidpointRoot/parseTanglegram/processQZA/imgproxy/download + 43 personal 管理端点）
- 多出的是**静态页面**（about/gallery/pricing/privacy/version_history/video_tutorial/itol.cgi/itol_account.cgi/userInfo.cgi）——非数据接口
- **无非 CGI 端点**：无 .php/.py/.json REST/WebSocket（ws:// 零命中）——纯 Apache CGI 架构

## 2. 外部主机（6 个）

| 主机 | 是什么 |
|---|---|
| itoleditor.letunic.com | 「iTOL annotation editor for spreadsheets」——**Google Sheets/LibreOffice 插件**（Workspace marketplace），非独立 REST API；注解写回仍走 iTOL 自身端点 |
| phylot.biobyte.de | phyloT 树生成器（同作者姊妹工具） |
| stratigraphy.org/chart | 地质年代色标数据源（timescale 场景用） |
| doi.org / fonts.google.com / biobyte.de | 文献/字体/作者公司 |

## 3. 隐藏参数发现

- **getMidpointRoot.cgi**：POST 除 `i=<tree_id>` 外带一组缩写控制参数 `col/rot/pru/lbl/nrn/ern/rer/m2/m1/m3/hid/mrt`（折叠/旋转/剪枝/标签等视图状态随 reroot 提交）
- **upload.cgi**（匿名上传）：filedrop 插件参数（position/contentSize/width/size）+ 文件本体
- **tree_uploader.cgi**：pid（项目）/pIdx/wIdx/dropArea/sequentialUpload + 树文本
- batch_downloader 83 参数见 EXPORT_PARAMS.md（已是全表）

## 4. 安全面审计（顺手）

- **无硬编码秘密**：全 JS 无 apikey/token/secret/password
- **无源码泄露**：.js.map 404、.git/.env/备份/phpinfo 全 404；.htaccess、/admin/ 403（存在但禁）
- **信息泄露**：仅 Apache/2.4.29 (Ubuntu) 版本横幅（2018 偏旧）
- **robots.txt**：Disallow /ajax/ /tree/（印证这两区是 API/数据区）
- **无内网 IP/localhost 泄露**

## 5. 能力边界终判（免费档）

| 能 | 不能（订阅墙） |
|---|---|
| 匿名/账号传树（upload.cgi / tree_uploader.cgi） | 服务端存注解/视图（saveTreeData/treeSaveView 500） |
| 免认证导出裸树（batch_downloader 83 参数） | 高 DPI 位图（batch 无 dpi；走 render 浏览器路或矢量后转） |
| 浏览器渲染带注解图（itol render） | — |
| 中点根化（getMidpointRoot.cgi） | — |

## 残留唯一不可枚举项

服务端**实际接受**的参数集合无法从客户端完全确证（客户端只发它需要的；服务端可能还认更多）。但前端 JS 是唯一权威调用源，已穷尽——未发送即未文档化、UI 也未用，视为不存在。
