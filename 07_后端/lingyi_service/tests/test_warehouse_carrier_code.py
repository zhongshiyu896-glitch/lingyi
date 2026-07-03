from app.routers.warehouse import _build_carrier_code


def test_build_carrier_code_uses_utf8_fixed_vectors() -> None:
    vectors = [
        ("默认仓库", "CC4DBED5", "ED5"),
        ("中文物料名", "0B7EC171", "171"),
        ("Z003-WAREHOUSE-20260616-101:purchase:中文", "81DAFCBC", "CBC"),
        ("ACC-000004 / 晓云里布", "56BFFD09", "D09"),
        ("WH-A", "9CF7D31C", "31C"),
    ]

    for value, full, short in vectors:
        assert _build_carrier_code(value, length=8) == full
        assert _build_carrier_code(value) == short
