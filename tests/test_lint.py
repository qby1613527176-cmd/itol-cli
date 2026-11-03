"""lint 校验器测试——官方模板必须全过 + 人造坑必须被抓。"""
from pathlib import Path

from itol_cli.lint import KNOWN_KEYWORDS, lint_file

TPL_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "ann.txt"
    p.write_text(text, encoding="utf-8")
    return p


def test_colorstrip_ok(tmp_path):
    p = _write(tmp_path, "DATASET_COLORSTRIP\nSEPARATOR TAB\nDATASET_LABEL\tsub\nCOLOR\t#ff0000\nDATA\nGeneA\t#E69F00\tSub1\nGeneB\t#56B4E9\tSub2\n")
    assert lint_file(p).ok


def test_colorstrip_missing_dataset_label_is_error(tmp_path):
    """DATASET_LABEL 是官方模板 MANDATORY 字段（用户拖拽报错实证）——缺它必须被抓。"""
    rep = lint_file(_write(tmp_path, "DATASET_COLORSTRIP\nSEPARATOR TAB\nDATA\nGeneA\t#E69F00\tSub1\n"))
    assert not rep.ok
    assert any("DATASET_LABEL" in i.message for i in rep.errors)


def test_unknown_keyword_with_hint(tmp_path):
    p = _write(tmp_path, "DATASET_CONNECTIONS\nDATA\nA\tB\n")
    rep = lint_file(p)
    assert not rep.ok
    assert any("单数" in i.message for i in rep.errors)


def test_missing_data_section(tmp_path):
    rep = lint_file(_write(tmp_path, "DATASET_HEATMAP\nSEPARATOR TAB\n"))
    assert not rep.ok
    assert any("DATA" in i.message for i in rep.errors)


def test_colorstrip_bad_hex(tmp_path):
    rep = lint_file(_write(tmp_path, "DATASET_COLORSTRIP\nDATA\nGeneA\tred\n"))
    assert not rep.ok
    assert any("hex" in i.message for i in rep.errors)


def test_heatmap_field_labels_mismatch(tmp_path):
    rep = lint_file(_write(tmp_path, "DATASET_HEATMAP\nSEPARATOR TAB\nFIELD_LABELS\ts1,s2\nDATA\nG1\t1\t2\t3\n"))
    assert not rep.ok
    assert any("FIELD_LABELS" in i.message for i in rep.errors)


def test_heatmap_ok(tmp_path):
    rep = lint_file(_write(tmp_path, "DATASET_HEATMAP\nSEPARATOR TAB\nDATASET_LABEL\thm\nFIELD_LABELS\ts1,s2\nDATA\nG1\t1\t2\n"))
    assert rep.ok


def test_tree_colors_ok(tmp_path):
    rep = lint_file(_write(tmp_path, "TREE_COLORS\nSEPARATOR TAB\nDATA\nGeneA\tbranch\t#E69F00\tnormal\t1\n"))
    assert rep.ok


def test_official_templates_all_pass():
    """30 个官方模板必须全过（用它们当回归——官方语法即真相）。"""
    official = Path("tests/fixtures/official_templates")
    if not official.is_dir():
        return  # 模板不在的环境跳过（CI）
    failures = []
    for f in sorted(official.glob("*.txt")):
        rep = lint_file(f)
        if not rep.ok:
            failures.append(f"{f.name}: {[i.message for i in rep.errors][:2]}")
    assert not failures, f"{len(failures)} 官方模板未过 lint：\n" + "\n".join(failures[:8])


def test_all_known_keywords_are_first_line_of_official_templates():
    """官方模板首行 ⊆ 我们的关键字表（防关键字表漏新类型）。"""
    official = Path("tests/fixtures/official_templates")
    if not official.is_dir():
        return
    for f in sorted(official.glob("*.txt")):
        first = next((ln.strip() for ln in f.read_text(encoding="utf-8").splitlines()
                      if ln.strip() and not ln.strip().startswith("#")), "")
        assert first in KNOWN_KEYWORDS, f"{f.name} 首行 {first!r} 不在 KNOWN_KEYWORDS"
