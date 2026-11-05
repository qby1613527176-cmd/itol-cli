# itol-cli 错误码（公开文档）

itol-cli 所有错误带统一错误码（对标 PyiTOL docs/error_codes.md / Rust 编译器 error[EXXXX]）。
报错后按本表「触发条件→修法」自助排查。

## IT001 — INVALID_INPUT
输入文件/注解文件不合法（lint 可本地拦截）

## IT002 — UPLOAD_FAILED
上传失败（ERR<code> 或网络）；订阅/key 问题归 IT004

## IT003 — EXPORT_FAILED
导出失败（无效树 ID / 格式不支持 / 服务器队列超时）

## IT004 — AUTH_REQUIRED
功能需 iTOL 标准订阅 + APIkey（userInfo.cgi 生成）

## IT005 — RATE_LIMITED
触发服务端限速（官方未明示阈值；串行+退避规避）

## IT006 — INTERNAL
内部错误（框架 bug；带 traceback 报 issue）
