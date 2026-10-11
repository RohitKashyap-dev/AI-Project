from backend.core.config import normalize_api_url


def test_normalize_api_url_adds_api_v1_prefix():
    assert normalize_api_url("http://localhost:8000") == "http://localhost:8000/api/v1"


def test_normalize_api_url_keeps_existing_api_v1_prefix():
    assert normalize_api_url("http://localhost:8000/api/v1") == "http://localhost:8000/api/v1"


def test_normalize_api_url_strips_trailing_slash():
    assert normalize_api_url("http://localhost:8000/") == "http://localhost:8000/api/v1"
