"""selection/connections/timescale 场景生成器测试。"""
from pathlib import Path

import pytest

from itol_cli.lint import lint_file
from itol_cli.templates import _omega_color, write_connections, write_selection, write_timescale


def _tsv(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "in.tsv"
    p.write_text(text, encoding="utf-8")
    return p


# ---- selection ----
def test_omega_color_scale():
    assert _omega_color(0.0) == "#2166AC"    # 强纯化=蓝
    assert _omega_color(1.0) == "#F7F7F7"    # 中性=白
    assert _omega_color(3.0) == "#B2182B"    # 正选择=红
    assert _omega_color(99) == "#B2182B"     # cap


def test_selection_basic(tmp_path):
    tsv = _tsv(tmp_path, "GeneA\t0.0\nGeneB|GeneC\t1.8\n")
    outs = write_selection(tsv, tmp_path / "out")
    text = outs[0].read_text(encoding="utf-8")
    assert text.startswith("TREE_COLORS\nSEPARATOR TAB\n")
    assert "GeneA\tbranch\t#2166AC" in text          # ω=0 → 纯蓝
    assert "GeneB|GeneC\tbranch\t" in text            # LCA 写法透传
    # ω=1.8 在 1..3 区间插值向红，颜色应在白红之间
    line = [ln for ln in text.splitlines() if ln.startswith("GeneB|GeneC")][0]
    c = line.split("\t")[2]
    r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    assert r > b and g < r                              # 偏红系
    rep = lint_file(outs[0])
    assert rep.ok, rep.summary()


def test_selection_rejects_bad(tmp_path):
    with pytest.raises(ValueError, match="不是数字"):
        write_selection(_tsv(tmp_path, "GeneA\tabc\n"), tmp_path / "o")
    with pytest.raises(ValueError, match="无任何有效"):
        write_selection(_tsv(tmp_path, "# 空\n"), tmp_path / "o2")


# ---- connections ----
def test_connections_basic(tmp_path):
    tsv = _tsv(tmp_path, "G1a\tG1b\t#E69F00\t同源对\nG2a\tG2b\n")
    outs = write_connections(tsv, tmp_path / "out")
    text = outs[0].read_text(encoding="utf-8")
    assert text.startswith("DATASET_CONNECTION\nSEPARATOR TAB\nDATASET_LABEL\t")
    assert "G1a\tG1b\t1.0\t#E69F00\tnormal\t同源对" in text
    assert "G2a\tG2b\t1.0\t#999999\tnormal\t" in text  # 缺省色
    rep = lint_file(outs[0])
    assert rep.ok, rep.summary()


def test_connections_rejects_bad(tmp_path):
    with pytest.raises(ValueError, match="≥2 列"):
        write_connections(_tsv(tmp_path, "onlyone\n"), tmp_path / "o")


# ---- timescale ----
def test_timescale_basic(tmp_path):
    tsv = _tsv(tmp_path, "Cretaceous\t145\t66\t#7FC97F\nNeogene\t23.03\t2.58\n")
    outs = write_timescale(tsv, tmp_path / "out")
    text = outs[0].read_text(encoding="utf-8")
    assert text.startswith("DATASET_TIMESCALE\nSEPARATOR TAB\nDATASET_LABEL\t")
    assert "145\t66\t\t\t#7FC97F\t\tCretaceous\tnormal" in text
    assert "23.03\t2.58\t\t\t#c8c8c8\t\tNeogene\tnormal" in text  # 缺省色
    rep = lint_file(outs[0])
    assert rep.ok, rep.summary()


def test_timescale_rejects_inverted(tmp_path):
    # iTOL 约定 start(老)>end(新)；写反必须拒
    with pytest.raises(ValueError, match="start"):
        write_timescale(_tsv(tmp_path, "Era\t66\t145\n"), tmp_path / "o")


def test_lint_timescale_catches_inverted(tmp_path):
    p = tmp_path / "bad_ts.txt"
    p.write_text("DATASET_TIMESCALE\nSEPARATOR TAB\nDATASET_LABEL\tt\nCOLOR\t#000000\nDATA\n66\t145\n",
                 encoding="utf-8")
    rep = lint_file(p)
    assert not rep.ok
    assert any("start" in i.message for i in rep.errors)
