# iTOL batch_downloader.cgi 全参数表（免认证服务端导出）

> 来源：2026-11-04 深挖代理从 help 页（L2459-2595 batchExp 节）+ JS 逆向提取，共 **2 必填 + 81 可选 = 83 参数**。
> 端点 `https://itol.embl.de/batch_downloader.cgi`，GET/POST 均可，**免认证**（上传才要订阅）。
> 全部可通过 `itol export <tree_id> <fmt> --param key=value` 透传，或用 `--preset` 预设组合。

## 必填（2）
| 参数 | 取值 | 作用 |
|---|---|---|
| tree | 数值树ID | 导出哪棵树 |
| format | svg/eps/pdf/png/newick/nexus/phyloxml | 输出格式 |

- 错误→Content-type: text/html；成功→对应 mime
- `newick_format=ID`：仅 newick——内部节点 ID 也导出

## 树几何/画布（14）
| 参数 | 取值 | 作用 |
|---|---|---|
| display_mode | 1/2/3 | **1=矩形 2=环形 3=无根** |
| slanted_normal | 0/1 | 斜三角模式；须同设 display_mode=1 + ignore_branch_length=1 |
| ignore_branch_length | 0/1 | 忽略枝长（cladogram） |
| arc | 0-360° | 环形树展开角 |
| rotation | 0-360° | 环形树旋转 |
| normal_rotation | 0-360° | 矩形树旋转 |
| unrooted_rotation | 0-360° | 无根树旋转 |
| inverted | 0/1 | 反转显示（仅环形+矩形） |
| circle_size_inverted | px | 反转环形内半径加大量 |
| leaf_sorting | 1/2 | 1=正常排序 2=不排序 |
| tree_x / tree_y | ±px | 树水平/垂直平移 |
| vertical_shift_factor | 正数 | 垂直缩放因子 |
| horizontal_scale_factor | 正数 | 水平缩放因子 |

## 叶标签（8）
| 参数 | 取值 | 作用 |
|---|---|---|
| label_display | 0/1 | 显/隐叶标签 |
| align_labels | 0/1 | 标签对齐 |
| label_shift | ±px | 叶标签平移量 |
| dashed_lines | 0/1 | 枝到标签虚线 |
| current_font_size | px int | 主标签字号 |
| current_font_name | Arial/Courier/Verdana/Impact/Georgia/Times New Roman/... | 字体 |
| current_font_style | normal/bold/bold italic | 字样式 |
| default_label_color | hex/RGB/RGBA | 默认标签色 |

## 枝线条（3）
| 参数 | 取值 | 作用 |
|---|---|---|
| line_width | px | 枝线宽 |
| line_gradient | 1 | 枝色=祖先→节点渐变 |
| default_branch_color | hex/RGB/RGBA | 默认枝色 |

## 枝长标签（6）
| 参数 | 取值 | 作用 |
|---|---|---|
| branchlength_display | 0/1 | 枝上显示枝长文本 |
| branchlength_label_size | px int≥0 | 字号 |
| branchlength_label_position | %（默认50） | 沿枝位置 |
| branchlength_label_sci | 1 | 科学计数法 |
| branchlength_label_rounding | int≥0 | 小数位 |
| branchlength_label_age | 1 | 显示节点 age 而非原始枝长 |

## bootstrap/元数据（23）——"bootstrap_*" 实为任意元数据源，metadata_source 切换
| 参数 | 取值 | 作用 |
|---|---|---|
| metadata_source | 默认 bootstrap，看树内元数据 | 用哪个元数据源 |
| bootstrap_display | 0/1 | 显示元数据值 |
| bootstrap_type | 1/2/3/4 | **1=符号 2=文本标签 3=枝色渐变 4=枝宽** |
| bootstrap_symbol | 1/2/3/4 | 1=圆 2=三角 3=方块 4=星 |
| bootstrap_symbol_min/max | px | 符号尺寸范围 |
| bootstrap_symbol_position | %（默认50） | 符号沿枝位置 |
| bootstrap_symbol_color | hex | 符号色 |
| bootstrap_slider_min/max | 数值 | 显示值域 |
| bootstrap_label_position | %（默认50） | 文本沿枝位置 |
| bootstrap_label_size | px int≥9 | 文本字号 |
| bootstrap_label_sci / _rounding | 1 / int | 科学计数 / 小数位 |
| bootstrap_label_percent_factor | 数值 | 文本×此因子（如×100 转百分） |
| bootstrap_width_default/min/max | px | type=4 时枝宽 |
| bootstrap_min_color/max_color | hex | type=3 渐变两端色 |
| bootstrap_use_mid_color / _mid_color | 0/1 / hex | 三色渐变 |
| **delete_nodes_below_bootstrap** | 数值 | ⚠️ **删除低于此值的节点——结构性修改，导出即生效** |

## 色带/图例（3）
| 参数 | 取值 | 作用 |
|---|---|---|
| range_mode | 0/1/2 | 0=关 1=只盖标签 2=盖全 clade |
| include_ranges_legend | 0/1 | 含色带图例 |
| ranges_legend_title | 文本 | 图例标题 |

## 内标尺 internal scale（22，internal_scale=1 才生效）——时间树地质轴
| 参数 | 取值 | 作用 |
|---|---|---|
| internal_scale | 0/1 | 总开关 |
| internal_scale_inverted | 0/1 | 从最远离根叶起算 |
| internalScaleRootValue | 数值 | 根的时间/数值零点 |
| internalScaleTimeScaling | 数值 | 枝长×此数显示标尺 |
| internalScaleAxis / Grid | 0/1 | 画轴 / 画网格 |
| internalScaleFontSize | px | 标尺字号 |
| internalScale1 / 2 | 枝长值 | 两组重复线间隔 |
| internalScaleFixed | 逗号分隔枝长值 | 固定位置线 |
| internalScale{1,2,Fixed}Color | hex | 三组线色 |
| internalScale{1,2,Fixed}Label | 0/1 | 三组线标签开关 |
| internalScale{1,2,Fixed}Dashed | 0/1 | 三组虚线开关 |
| internalScale{1,2,Fixed}Wid | px | 三组线宽 |

## 数据集可见性（1）
| 参数 | 取值 | 作用 |
|---|---|---|
| datasets_visible | 逗号分隔索引从0起，如 0,2,5 | 哪些 DATASET 显示（注意：免费账号服务端无数据集存储，此参数对服务端导出无效，注解要走 itol render 浏览器路） |

## 配套场景映射
- **bootstrap 展示树**：`bootstrap_display=1&bootstrap_type=1`（符号）或 `3`（枝色渐变）
- **时间树地质轴**：`internal_scale=1&internalScaleAxis=1&internalScaleGrid=1&internalScaleRootValue=<t0>`
- **cladogram**：`ignore_branch_length=1`；**slanted**：+`slanted_normal=1&display_mode=1`
- **出版级标签**：`align_labels=1&dashed_lines=1&current_font_size=<≥10>`
