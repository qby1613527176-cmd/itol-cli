"""client 层测试——上传响应解析 + zip 构造 + 导出错误分层（不真打网络）。"""
import io
import zipfile

import pytest

from itol_cli.client import ItolClient, make_upload_zip
from itol_cli.errors import ItolError


def test_parse_upload_success():
    tid, warns = ItolClient._parse_upload_response("SUCCESS: 123456789\n")
    assert tid == "123456789" and warns == []


def test_parse_upload_success_with_warnings():
    tid, warns = ItolClient._parse_upload_response("WARN: dataset X row 3 skipped\nSUCCESS: 42\n")
    assert tid == "42" and len(warns) == 1


def test_parse_upload_err():
    with pytest.raises(ItolError) as ei:
        ItolClient._parse_upload_response("ERR 0: Please provide your iTOL API key\n")
    assert ei.value.code == "IT002"


def test_zip_tree_extension_autofix(tmp_path):
    tree = tmp_path / "t.nwk"
    tree.write_text("(A:1,B:1);")
    ann = tmp_path / "cs.txt"
    ann.write_text("DATASET_COLORSTRIP\nDATA\nA\t#E69F00\n")
    payload = make_upload_zip(tree, [ann])
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = zf.namelist()
    assert "t.nwk.tree" in names and "cs.txt" in names  # 官方硬性扩展名规格


def test_export_rejects_bad_format():
    c = ItolClient()
    with pytest.raises(ItolError) as ei:
        c.export("123", "bmp")
    assert ei.value.code == "IT003"


def test_upload_requires_key(tmp_path):
    tree = tmp_path / "t.tree"
    tree.write_text("(A:1,B:1);")
    c = ItolClient(api_key="")
    with pytest.raises(ItolError) as ei:
        c.upload(tree, [], project="p")
    assert ei.value.code == "IT004"


def test_delete_requires_key():
    with pytest.raises(ItolError) as ei:
        ItolClient(api_key="").delete("123")
    assert ei.value.code == "IT004"
