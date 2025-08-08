from scripts.io_utils import get_default_io, DEFAULT_LOCAL_ROOT


def test_get_default_io_local_fallback():
    inp, out = get_default_io()
    assert str(inp).startswith(str(DEFAULT_LOCAL_ROOT))
    assert inp.exists() and out.exists()
