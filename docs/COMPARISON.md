# itol-cli 同类项目对比分析（2026-11-06，5 路调研）

> 目的：对照同类型项目找 itol-cli 的可改进点。5 路调研（iTOL 专用工具 / 树 CLI / 可视化库 / CLI 工程 / 注解自动化）。

## 一句话定位

**iTOL 专用工具里没有比 itol-cli 更全的**——itolapi 只是传输层，PyiTOL 偏模板+taxonomy，itol.toolkit 无传输层。itol-cli 的 gen/lint/render/fetch/account 全链路已领先直接竞品。改进空间在**树侧校验**和**工程打磨**。

## 🥇 高价值（几乎全工具都有、唯独我们缺）

### 1. lint 只查注解、不查树文件本身
- 证据：gotree stats / nwkit validate / phyx pxlstr / PhyKIT 统计 / newick_utils nw_stats——5 个工具全都有树结构校验；PyiTOL validate 连负枝长/重名/多根/对抗字符都查。
- 现状：itol-cli lint 只查 30 个注解关键字，不查输入 newick（括号平衡/重复名/方言/支长异常）。烂树直接进 gen→render 静默坑。
- 改进：lint 加树文件体检（纯 Python 解析，高价值低风险）。

### 2. 本地渲染 fallback
- 证据：gotree draw / nw_display / ete view / PhyKIT print_tree / toytree 全都不依赖远程。
- 现状：render 必须 Xvfb+playwright+联网。
- 改进：轻量本地渲染后端（ete3/toytree）做离线降级 + ASCII 终端速览（CI/快速预览）。

## 🥈 差异化/生态

### 3. 树预处理子命令（reroot/prune/rename map/支长缩放）
- 上 iTOL 前最高频手工步骤；gotree/nwkit 全套有，可用 ete3 内核。

### 4. gen 亚家族着色自动验单系
- phyx pxmono / PhyKIT monophyly_check / PyiTOL 单系判定。基因家族论文图硬质量门，非单系就警告。

### 5. AI skill / MCP server
- 先例：iTOL-annotation-skill。itol-cli 的 gen 模板+lint 校验天然适配 LLM（模板即 schema、lint 即反馈回路）——「AI 生成→lint 校验→自动修正」闭环。

### 6. 主题学习 / 逆向复用（itol.toolkit 杀手功能）
- 解析已有 iTOL 注解文件 → 抽出样式参数 → 套到新数据。改进项：`itol learn <template.txt>`（复现别人论文图样式，纯文本解析成本低）。

### 7. 机器可读命令目录
- PhyKIT 的 llms.txt/commands.json。从 click 元数据导出，几乎零成本。

## 🥉 工程打磨（seqkit/csvtk/MultiQC 标配、我们缺）

8. shell 补全（`itol completion`，click 内置，零成本）
9. `--dry-run`（upload/render，snakemake/nextflow 一等公民功能，补最危险+最重操作）
10. render/export 进度反馈（数十秒静默是当前最大 UX 痛点）
11. IT001-006 错误码公开文档页 + 报错附 URL（错误契约已是差异化优势，只差给用户看）
12. `uv tool install` 首推安装 + CITATION.cff/DOI
13. session 快照 + replay（PyiTOL 卖点：改一个参数重放全流水线）
14. upload-and-export 一键流水线 + --wait 轮询（订阅档）

## 反直觉的好消息（差异化卖点，需在文档讲清）
- **PyiTOL 的 export --dpi 疑似无效**：官方 batch_downloader.cgi 无 dpi 参数，PyiTOL 这些选项疑似透传无效或本地放大；**itol-cli render --dpi 走浏览器截图才是真高分辨率**——这是卖点不是差距。

## 覆盖广度
- itol.toolkit 23 类型 / PyiTOL 31 类型 vs itol-cli 9 场景。优先补：DATASET_STYLE / DATASET_TEXT / POPUP_INFO / DATASET_IMAGE / DATASET_ALIGNMENT / BOXPLOT / LINECHART（按 survey3 模板手册逐个加）。
