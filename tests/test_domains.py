"""domains/motif 场景生成器测试（DATASET_DOMAINS 语法 = 官方模板实证）。"""
from pathlib import Path

import pytest

from itol_cli.lint import lint_file
from itol_cli.templates import write_domains


def _tsv(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "domains.tsv"
    p.write_text(text, encoding="utf-8")
    return p


def test_domains_basic(tmp_path):
    tsv = _tsv(tmp_path, "GeneA\tResponse_reg\t5\t120\t894\nGeneA\tMyb\t300\t380\t894\nGeneB\tResponse_reg\t10\t130\t700\n")
    outs = write_domains(tsv, tmp_path / "out")
    assert len(outs) == 1
    text = outs[0].read_text(encoding="utf-8")
    assert text.startswith("DATASET_DOMAINS\nSEPARATOR TAB\nDATASET_LABEL\tDomains\n")
    assert "GeneA\t894\tRE|5|120|" in text
    assert "RE|300|380|" in text  # 同基因双域同行
    # 生成物必须过 lint（自产自销一致性）
    rep = lint_file(outs[0])
    assert rep.ok, rep.summary()


def test_domains_two_genes_independence(tmp_path):
    tsv = _tsv(tmp_path, "G1\tD1\t1\t50\t300\nG2\tD2\t10\t60\t500\n")
    outs = write_domains(tsv, tmp_path / "out")
    text = outs[0].read_text(encoding="utf-8")
    assert "G1\t300\t" in text and "G2\t500\t" in text


def test_domains_rejects_bad_rows(tmp_path):
    # 列数不足
    with pytest.raises(ValueError, match="列数不足"):
        write_domains(_tsv(tmp_path, "G1\tD1\t1\t50\n"), tmp_path / "o1")
    # start >= end
    with pytest.raises(ValueError, match="start>=end"):
        write_domains(_tsv(tmp_path, "G1\tD1\t50\t50\t300\n"), tmp_path / "o2")
    # end > 蛋白长度
    with pytest.raises(ValueError, match="超蛋白长度|end>protein_length"):
        write_domains(_tsv(tmp_path, "G1\tD1\t1\t500\t300\n"), tmp_path / "o3")
    # 空输入
    with pytest.raises(ValueError, match="无任何有效域记录"):
        write_domains(_tsv(tmp_path, "# 只有注释\n"), tmp_path / "o4")


def test_lint_domains_catches_bad_def(tmp_path):
    p = tmp_path / "bad_domains.txt"
    p.write_text(
        "DATASET_DOMAINS\nSEPARATOR TAB\nDATASET_LABEL\td\nCOLOR\t#ff0000\nDATA\n"
        "G1\t300\tRE|1|500|#E69F00|D1\n",  # END=500 > 蛋白长 300
        encoding="utf-8")
    rep = lint_file(p)
    assert not rep.ok
    assert any("超蛋白长度" in i.message for i in rep.errors)


def test_lint_domains_ok(tmp_path):
    p = tmp_path / "ok_domains.txt"
    p.write_text(
        "DATASET_DOMAINS\nSEPARATOR TAB\nDATASET_LABEL\td\nCOLOR\t#ff0000\nDATA\n"
        "G1\t300\tRE|1|50|#E69F00|D1\tHH|100|180|#56B4E9|D2\n",
        encoding="utf-8")
    rep = lint_file(p)
    assert rep.ok, rep.summary()
