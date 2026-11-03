#!/usr/bin/env python3
"""gen_metadata.py — 权威数字自动源（tbtools 模式简化版：数字只信自动生成源）。

生成 docs/_generated/counts.md；--check 模式：与现有文件不一致则 exit 1（CI 门禁）。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "docs" / "_generated" / "counts.md"


def collect() -> dict:
    from itol_cli.templates import TEMPLATES
    from itol_cli.errors import ERROR_CODES
    tests = list((ROOT / "tests").glob("test_*.py"))
    return {
        "scenarios": len(TEMPLATES),
        "error_codes": len(ERROR_CODES),
        "test_files": len(tests),
        "lint_keywords": len(__import__("itol_cli.lint", fromlist=["KNOWN_KEYWORDS"]).KNOWN_KEYWORDS),
    }


def render(c: dict) -> str:
    return (
        "# 权威数字（gen_metadata.py 自动生成，勿手改）\n\n"
        f"| 指标 | 数 |\n|---|---|\n"
        f"| 场景模板 | {c['scenarios']} |\n"
        f"| 错误契约 | {c['error_codes']} |\n"
        f"| 测试文件 | {c['test_files']} |\n"
        f"| lint 关键字覆盖 | {c['lint_keywords']} |\n"
    )


def main() -> None:
    content = render(collect())
    if "--check" in sys.argv:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != content:
            print("❌ counts.md 与代码现状不一致——跑 python scripts/gen_metadata.py 刷新")
            sys.exit(1)
        print("✅ counts.md 一致")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(content, encoding="utf-8")
    print(f"已写入 {OUT}")


if __name__ == "__main__":
    main()
