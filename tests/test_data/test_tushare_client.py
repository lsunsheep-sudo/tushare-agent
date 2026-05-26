import pytest
from app.data.tushare_client import TushareClient


class TestTushareClient:
    def test_init_with_token(self):
        client = TushareClient(token="test-token")
        assert client._token == "test-token"

    def test_format_ts_code_with_dot(self):
        client = TushareClient(token="test-token")
        assert client._format_ts_code("600519") == "600519.SH"
        assert client._format_ts_code("000001.SZ") == "000001.SZ"

    def test_format_ts_code_already_formatted(self):
        client = TushareClient(token="test-token")
        assert client._format_ts_code("600519.SH") == "600519.SH"
