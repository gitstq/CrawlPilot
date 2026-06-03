"""
CrawlPilot - FetchEngine 测试模块

测试HTTP请求引擎的各项功能。
"""

import json
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from urllib.parse import urlparse

from crawl_pilot.fetcher import (
    FetchEngine,
    FetchResponse,
    USER_AGENTS,
    DEFAULT_HEADERS,
)
from crawl_pilot.utils import FetchError


class TestFetchResponse(unittest.TestCase):
    """FetchResponse 响应对象测试。"""

    def test_basic_response(self) -> None:
        """测试基本响应属性。"""
        response = FetchResponse(
            url="https://example.com",
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"<html><body>Hello</body></html>",
            encoding="utf-8",
            elapsed=0.5,
        )

        self.assertEqual(response.url, "https://example.com")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.ok)
        self.assertEqual(response.content_length, 31)
        self.assertEqual(response.text, "<html><body>Hello</body></html>")

    def test_response_ok_property(self) -> None:
        """测试ok属性。"""
        ok_response = FetchResponse(
            url="https://example.com",
            status_code=200,
            headers={},
            content=b"",
        )
        self.assertTrue(ok_response.ok)

        not_found = FetchResponse(
            url="https://example.com",
            status_code=404,
            headers={},
            content=b"",
        )
        self.assertFalse(not_found.ok)

        server_error = FetchResponse(
            url="https://example.com",
            status_code=500,
            headers={},
            content=b"",
        )
        self.assertFalse(server_error.ok)

    def test_response_json(self) -> None:
        """测试JSON解析。"""
        response = FetchResponse(
            url="https://example.com/api",
            status_code=200,
            headers={},
            content=b'{"name": "test", "value": 42}',
            encoding="utf-8",
        )
        data = response.json()
        self.assertEqual(data["name"], "test")
        self.assertEqual(data["value"], 42)

    def test_response_size(self) -> None:
        """测试大小格式化。"""
        response = FetchResponse(
            url="https://example.com",
            status_code=200,
            headers={},
            content=b"x" * 1024,
        )
        self.assertEqual(response.size, "1.00 KB")

    def test_response_repr(self) -> None:
        """测试字符串表示。"""
        response = FetchResponse(
            url="https://example.com",
            status_code=200,
            headers={},
            content=b"hello",
        )
        repr_str = repr(response)
        self.assertIn("200", repr_str)
        self.assertIn("example.com", repr_str)


class TestFetchEngine(unittest.TestCase):
    """FetchEngine 请求引擎测试。"""

    def test_init_defaults(self) -> None:
        """测试默认初始化。"""
        engine = FetchEngine()
        self.assertEqual(engine.timeout, 30)
        self.assertEqual(engine.max_retries, 3)
        self.assertTrue(engine.rotate_ua)
        self.assertTrue(engine.verify_ssl)

    def test_init_custom(self) -> None:
        """测试自定义初始化。"""
        engine = FetchEngine(
            timeout=15,
            max_retries=1,
            proxy="http://127.0.0.1:7890",
            rotate_ua=False,
        )
        self.assertEqual(engine.timeout, 15)
        self.assertEqual(engine.max_retries, 1)
        self.assertEqual(engine.proxy, "http://127.0.0.1:7890")
        self.assertFalse(engine.rotate_ua)

    def test_user_agent_rotation(self) -> None:
        """测试UA轮换。"""
        engine = FetchEngine(rotate_ua=True)
        uas = set()
        for _ in range(100):
            uas.add(engine._get_user_agent())
        # 100次调用应该产生多个不同的UA
        self.assertGreater(len(uas), 1)

    def test_fixed_user_agent(self) -> None:
        """测试固定UA。"""
        engine = FetchEngine(user_agent="MyBot/1.0")
        self.assertEqual(engine._get_user_agent(), "MyBot/1.0")

    def test_build_headers(self) -> None:
        """测试请求头构建。"""
        engine = FetchEngine()
        headers = engine._build_headers("https://example.com/page")
        self.assertIn("User-Agent", headers)
        self.assertIn("Accept", headers)
        self.assertIn("Referer", headers)
        self.assertEqual(headers["Referer"], "https://example.com/")

    def test_build_headers_with_extra(self) -> None:
        """测试带额外请求头的构建。"""
        engine = FetchEngine()
        headers = engine._build_headers(
            "https://example.com",
            extra_headers={"X-Custom": "value"},
        )
        self.assertEqual(headers["X-Custom"], "value")

    def test_context_manager(self) -> None:
        """测试上下文管理器。"""
        with FetchEngine() as engine:
            self.assertIsNotNone(engine)
        # 退出后Cookie应被清除
        self.assertEqual(len(engine.session_cookies), 0)

    def test_repr(self) -> None:
        """测试字符串表示。"""
        engine = FetchEngine()
        repr_str = repr(engine)
        self.assertIn("FetchEngine", repr_str)

    def test_user_agents_list(self) -> None:
        """测试内置UA列表。"""
        self.assertGreaterEqual(len(USER_AGENTS), 20)
        for ua in USER_AGENTS:
            self.assertIn("Mozilla", ua)

    def test_default_headers(self) -> None:
        """测试默认请求头。"""
        self.assertIn("Accept", DEFAULT_HEADERS)
        self.assertIn("Accept-Language", DEFAULT_HEADERS)
        self.assertIn("Connection", DEFAULT_HEADERS)


if __name__ == "__main__":
    unittest.main()
