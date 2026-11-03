# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [0.1.0] - 2026-11-03

首个骨架版（B 路线：差异化自建，文本模板一等公民 + lint 校验 + 上传/导出流水线）。

### 场景模板引擎（9 个）
- subfamily 亚家族着色主树（TREE_COLORS+COLORSTRIP，Okabe-Ito/Tol 18 色板，>8 分组不撞色）
- bootstrap 支持率展示（导出参数预设，≥95 实心点规则）
- heatmap 表达热图联树（行序=树序强制校验）
- domains 域结构联树 / motif 基序联树（DATASET_DOMAINS 官方原生类型）
- selection 选择压力标注树（ω 蓝→白→红发散色阶，cap 3）
- connections 共线连线树/tanglegram（DATASET_CONNECTION）
- timescale 时间树地质年代轴（DATASET_TIMESCALE，零=树顶约定校验）
- pav 泛基因组 PAV 联树（DATASET_BINARY）

### lint 校验器
- 30 关键字全集（30 官方模板校准：CONNECTION 单数/DOMAINS/TIMESCALE/RANGE/TANGLEGRAM/AUTO_TAXONOMY…）
- MANDATORY 字段检查（DATASET_* 缺 DATASET_LABEL=error，用户拖拽报错实证）
- rgb()/rgba() 颜色 / 官方模板注释示例形态 / ALIGNMENT=FASTA 不查列数 / COMMA 下 LCA 写法检查
- DOMAINS 特检（域定义 5 段/坐标合法）/ CONNECTION/RANGE/TIMESCALE 特检

### API 客户端（iTOL 三 CGI，调研实证规格）
- 上传 batch_uploader.cgi（zip 自动补 .tree 扩展名；需订阅+APIkey）
- 导出 batch_downloader.cgi（免认证，9 格式，全显示参数透传；无 dpi 缺口文档化）
- 删除 batch_delete.cgi；分层错误解析（CGI 首行 SUCCESS/ERR + 页面型 URL 无效 ID 也回 200 须解析 title）
- 串行 + 1s 间隔 + 指数退避 + 120s 超时；错误契约 IT001-006

### 验证
- pytest 33/33（生成器正反例 / lint 正反例 / 30 官方模板回归 / client 解析）
- 真实数据闭环：GRAS 12sp 926 叶树 + 17 亚家族分组 → 注解生成 → lint → 匿名上传树 → 网页端图成立（用户实证）
- 公开树导出 SVG 实证（免认证路径）

### 已知限制
- 匿名树注解为客户端级（服务端不存）——程序化挂注解需 iTOL 账号（免费账号登录 or 订阅 batch_uploader）
- 上传/删除代码就绪但未经端到端实测（待订阅 key）
- MSA 大连图/motif>8 为 iTOL 边界场景（建议 ggtree fallback，未实现）

门禁：pytest 33 passed / ruff 0 / mypy 0 / gen_metadata --check 一致
