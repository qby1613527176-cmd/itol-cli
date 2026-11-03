"""itol-cli: iTOL annotation template generation + upload/export pipeline."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("itol-cli")
except PackageNotFoundError:  # 未安装态（源码直跑）
    __version__ = "0.1.0"
