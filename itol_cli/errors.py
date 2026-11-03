"""itol-cli 错误契约（裁剪自 tbtools-cli TB001-012 模式）。

每个错误码带 retryable 布尔 + 诊断字段。Agent/人都能据此决策下一步。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ItolError(Exception):
    code: str
    message: str
    retryable: bool = False
    diagnosis: str = ""
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover
        base = f"[{self.code}] {self.message}"
        return f"{base}（建议：{self.diagnosis}）" if self.diagnosis else base


# 错误码注册表（单一权威，文档/测试从这里生成）
ERROR_CODES = {
    "IT001": "INVALID_INPUT — 输入文件/注解文件不合法（lint 可本地拦截）",
    "IT002": "UPLOAD_FAILED — 上传失败（ERR<code> 或网络）；订阅/key 问题归 IT004",
    "IT003": "EXPORT_FAILED — 导出失败（无效树 ID / 格式不支持 / 服务器队列超时）",
    "IT004": "AUTH_REQUIRED — 功能需 iTOL 标准订阅 + APIkey（userInfo.cgi 生成）",
    "IT005": "RATE_LIMITED — 触发服务端限速（官方未明示阈值；串行+退避规避）",
    "IT006": "INTERNAL — 内部错误（框架 bug；带 traceback 报 issue）",
}


def invalid_input(message: str, diagnosis: str = "") -> ItolError:
    return ItolError("IT001", message, retryable=False, diagnosis=diagnosis or "跑 itol lint <文件> 定位")


def upload_failed(message: str, retryable: bool = False, diagnosis: str = "") -> ItolError:
    return ItolError("IT002", message, retryable=retryable, diagnosis=diagnosis)


def export_failed(message: str, retryable: bool = False, diagnosis: str = "") -> ItolError:
    return ItolError("IT003", message, retryable=retryable, diagnosis=diagnosis)


def auth_required(what: str = "此功能") -> ItolError:
    return ItolError(
        "IT004",
        f"{what}需要 iTOL 标准订阅 + APIkey",
        retryable=False,
        diagnosis="订阅见 https://itol.embl.de/pricing.cgi；key 在 userInfo.cgi 生成；配置 ITOL_API_KEY 环境变量或 ~/.itol-cli/config",
    )


def rate_limited(message: str = "疑似触发服务端限速") -> ItolError:
    return ItolError("IT005", message, retryable=True, diagnosis="串行请求 + 间隔≥1s + 指数退避")
