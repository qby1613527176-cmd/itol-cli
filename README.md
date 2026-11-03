# itol-cli

iTOL（itol.embl.de）命令行工具：**注解模板生成 + 本地 lint 校验 + 上传/导出流水线**。

设计哲学：**设计即数据**——注解文件是一等公民的纯文本模板（人/AI 可直接手写），CLI 负责生成、校验、上传、导出闭环。

```bash
pip install itol-cli   # （发布后）
# 或源码：pip install -e .
```

## 10 秒上手

```bash
itol doctor                      # 环境自检（API key/端点存活）
itol templates                   # 场景模板库
itol gen subfamily groups.tsv    # 分组 tsv → TREE_COLORS + COLORSTRIP
itol lint itol_colorstrip.txt    # 本地校验注解文件
itol export 123456789 --format svg -o tree.svg   # 导出（免认证）
itol upload tree.tree ann1.txt --project MyProj  # 上传（需订阅+key）
```

## 关键事实（2026-11-02 官方文档+curl 实证）

- **上传/删除**需 iTOL 标准订阅 + APIkey（`userInfo.cgi` 生成；订阅见 pricing.cgi）；`export ITOL_API_KEY=...` 或写 `~/.itol-cli/config`
- **导出免认证**：公开树按数字 ID 即可导出；格式 svg/eps/pdf/png/newick/nexus/phyloxml
- **导出无 dpi/宽高参数**——高分辨率位图是缺口，默认用 SVG/PDF/EPS 矢量
- 官方无速率限制，本工具默认串行+1s 间隔+指数退避
- 分享 URL（/tree/\<id\>）无鉴权，知 ID 即可访问——注意未发表数据

## 场景模板库

| 场景 | 输入 | 产出 |
|:------|:------|:------|
| `subfamily` 亚家族着色主树 | 分组 tsv（node_id TAB group） | TREE_COLORS + COLORSTRIP（Okabe-Ito/Tol 18 色板） |
| `bootstrap` 支持率展示 | IQ-TREE .contree | 导出参数预设（≥95 实心点规则） |
| `heatmap` 表达热图联树 | 矩阵 tsv（首列=树叶名） | DATASET_HEATMAP（内建行序=树序校验） |
| `domains` 域结构联树 | 域表 tsv（gene/domain/start/end/len） | DATASET_DOMAINS（官方原生类型） |
| `motif` 基序联树 | motif 表 tsv（同构） | DATASET_DOMAINS（motif 作色块） |
| `selection` 选择压力标注树 | ω 表 tsv（node TAB omega） | TREE_COLORS（枝按 ω 蓝→白→红渐变） |
| `connections` 共线连线树/tanglegram | 配对表 tsv（node1 TAB node2 [color] [label]） | DATASET_CONNECTION |
| `timescale` 时间树地质年代轴 | 区间表 tsv（name TAB start TAB end [color]） | DATASET_TIMESCALE |
| `pav` 泛基因组 PAV 联树 | 0/1 矩阵 tsv（首列=树叶名） | DATASET_BINARY |

## 错误契约

IT001 INVALID_INPUT / IT002 UPLOAD_FAILED / IT003 EXPORT_FAILED / IT004 AUTH_REQUIRED / IT005 RATE_LIMITED / IT006 INTERNAL——每个错误带 retryable 与诊断建议。

## License

MIT
