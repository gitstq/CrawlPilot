"""
CrawlPilot - 工具函数测试模块

测试utils模块中的各项工具函数。
"""

import hashlib
import os
import tempfile
import unittest

from crawl_pilot.utils import (
    CrawlPilotError,
    FetchError,
    ParseError,
    StorageError,
    SchedulerError,
    normalize_url,
    join_url,
    get_domain,
    is_same_domain,
    is_valid_url,
    detect_encoding,
    clean_text,
    extract_numbers,
    truncate_text,
    format_size,
    hash_url,
    hash_content,
    ProgressBar,
    setup_logging,
    ColorFormatter,
)


class TestExceptions(unittest.TestCase):
    """自定义异常测试。"""

    def test_crawl_pilot_error(self) -> None:
        """测试基础异常。"""
        err = CrawlPilotError("test error")
        self.assertEqual(err.message, "test error")
        self.assertIn("test error", str(err))

    def test_fetch_error(self) -> None:
        """测试请求异常。"""
        err = FetchError("request failed", status_code=404, url="https://example.com")
        self.assertEqual(err.status_code, 404)
        self.assertEqual(err.url, "https://example.com")
        self.assertIn("404", str(err))
        self.assertIn("example.com", str(err))

    def test_parse_error(self) -> None:
        """测试解析异常。"""
        err = ParseError("parse failed", selector="h1.title")
        self.assertEqual(err.selector, "h1.title")
        self.assertIn("h1.title", str(err))

    def test_storage_error(self) -> None:
        """测试存储异常。"""
        err = StorageError("write failed", path="/tmp/data.json")
        self.assertEqual(err.path, "/tmp/data.json")
        self.assertIn("/tmp/data.json", str(err))

    def test_scheduler_error(self) -> None:
        """测试调度异常。"""
        err = SchedulerError("schedule failed")
        self.assertIn("schedule failed", str(err))


class TestURLUtils(unittest.TestCase):
    """URL处理工具测试。"""

    def test_normalize_url_with_base(self) -> None:
        """测试带基础URL的规范化。"""
        result = normalize_url("/path", "https://example.com")
        self.assertEqual(result, "https://example.com/path")

    def test_normalize_url_absolute(self) -> None:
        """测试绝对URL规范化。"""
        result = normalize_url("https://example.com/path")
        self.assertEqual(result, "https://example.com/path")

    def test_normalize_url_lowercase(self) -> None:
        """测试大小写规范化。"""
        result = normalize_url("HTTPS://EXAMPLE.COM/Path")
        self.assertEqual(result, "https://example.com/Path")

    def test_normalize_url_remove_fragment(self) -> None:
        """测试去除片段标识符。"""
        result = normalize_url("https://example.com/page#section")
        self.assertEqual(result, "https://example.com/page")

    def test_normalize_url_trailing_slash(self) -> None:
        """测试去除末尾斜杠。"""
        result = normalize_url("https://example.com/path/")
        self.assertEqual(result, "https://example.com/path")

    def test_normalize_url_root_path(self) -> None:
        """测试根路径保留斜杠。"""
        result = normalize_url("https://example.com/")
        self.assertEqual(result, "https://example.com/")

    def test_join_url(self) -> None:
        """测试URL拼接。"""
        result = join_url("https://example.com", "/page")
        self.assertEqual(result, "https://example.com/page")

    def test_get_domain(self) -> None:
        """测试域名提取。"""
        result = get_domain("https://www.example.com/path")
        self.assertEqual(result, "www.example.com")

    def test_is_same_domain(self) -> None:
        """测试同域名判断。"""
        self.assertTrue(is_same_domain(
            "https://example.com/page1",
            "https://example.com/page2",
        ))
        self.assertFalse(is_same_domain(
            "https://example.com/page",
            "https://other.com/page",
        ))

    def test_is_valid_url(self) -> None:
        """测试URL有效性检查。"""
        self.assertTrue(is_valid_url("https://example.com"))
        self.assertTrue(is_valid_url("http://example.com/path"))
        self.assertFalse(is_valid_url("not-a-url"))
        self.assertFalse(is_valid_url("ftp://example.com"))
        self.assertFalse(is_valid_url(""))


class TestEncodingDetection(unittest.TestCase):
    """编码检测测试。"""

    def test_detect_utf8_from_meta(self) -> None:
        """测试从meta标签检测UTF-8。"""
        html = b'<html><head><meta charset="UTF-8"></head></html>'
        encoding = detect_encoding(html)
        self.assertEqual(encoding, "utf-8")

    def test_detect_gbk_from_meta(self) -> None:
        """测试从meta标签检测GBK。"""
        html = b'<html><head><meta charset="GBK"></head></html>'
        encoding = detect_encoding(html)
        self.assertEqual(encoding, "gbk")

    def test_detect_from_content_type(self) -> None:
        """测试无meta标签时使用chardet或默认UTF-8。"""
        html = b"<html><body>Hello</body></html>"
        encoding = detect_encoding(html)
        # chardet可能检测为ascii（ascii是utf-8的子集），两者均可接受
        self.assertIn(encoding, ("utf-8", "ascii"))


class TestTextProcessing(unittest.TestCase):
    """文本处理测试。"""

    def test_clean_text_basic(self) -> None:
        """测试基本文本清洗。"""
        result = clean_text("  Hello  World  ")
        self.assertEqual(result, "Hello World")

    def test_clean_text_html(self) -> None:
        """测试HTML标签清洗。"""
        result = clean_text("<p>Hello <em>World</em></p>")
        self.assertEqual(result, "Hello World")

    def test_clean_text_empty(self) -> None:
        """测试空文本。"""
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text(None), "")

    def test_clean_text_whitespace(self) -> None:
        """测试空白规范化。"""
        result = clean_text("Hello\n\nWorld\t\t!")
        self.assertEqual(result, "Hello World !")

    def test_extract_numbers(self) -> None:
        """测试数字提取。"""
        result = extract_numbers("Price: $99.99, Quantity: 42")
        self.assertIn("99.99", result)
        self.assertIn("42", result)

    def test_extract_numbers_negative(self) -> None:
        """测试负数提取。"""
        result = extract_numbers("Temperature: -5.5 degrees")
        self.assertIn("-5.5", result)

    def test_truncate_text(self) -> None:
        """测试文本截断。"""
        result = truncate_text("Hello World", max_length=8)
        self.assertEqual(result, "Hello...")

    def test_truncate_text_no_truncate(self) -> None:
        """测试不截断。"""
        result = truncate_text("Hi", max_length=10)
        self.assertEqual(result, "Hi")


class TestFormatSize(unittest.TestCase):
    """文件大小格式化测试。"""

    def test_bytes(self) -> None:
        """测试字节。"""
        self.assertEqual(format_size(500), "500.00 B")

    def test_kilobytes(self) -> None:
        """测试KB。"""
        self.assertEqual(format_size(1024), "1.00 KB")

    def test_megabytes(self) -> None:
        """测试MB。"""
        self.assertEqual(format_size(1048576), "1.00 MB")

    def test_gigabytes(self) -> None:
        """测试GB。"""
        self.assertEqual(format_size(1073741824), "1.00 GB")

    def test_negative(self) -> None:
        """测试负值。"""
        self.assertEqual(format_size(-1), "0 B")

    def test_zero(self) -> None:
        """测试零值。"""
        self.assertEqual(format_size(0), "0.00 B")


class TestHashFunctions(unittest.TestCase):
    """哈希函数测试。"""

    def test_hash_url_consistent(self) -> None:
        """测试URL哈希一致性。"""
        h1 = hash_url("https://example.com")
        h2 = hash_url("https://example.com")
        self.assertEqual(h1, h2)

    def test_hash_url_different(self) -> None:
        """测试不同URL哈希不同。"""
        h1 = hash_url("https://example.com/page1")
        h2 = hash_url("https://example.com/page2")
        self.assertNotEqual(h1, h2)

    def test_hash_url_normalized(self) -> None:
        """测试URL规范化后哈希相同。"""
        h1 = hash_url("https://example.com")
        h2 = hash_url("https://EXAMPLE.com")
        self.assertEqual(h1, h2)

    def test_hash_content(self) -> None:
        """测试内容哈希。"""
        h1 = hash_content("hello world")
        h2 = hash_content("hello world")
        self.assertEqual(h1, h2)

    def test_hash_sha256(self) -> None:
        """测试SHA256哈希。"""
        h = hash_url("https://example.com", algorithm="sha256")
        self.assertEqual(len(h), 64)


class TestProgressBar(unittest.TestCase):
    """进度条测试。"""

    def test_init(self) -> None:
        """测试初始化。"""
        bar = ProgressBar(total=100)
        self.assertEqual(bar.total, 100)
        self.assertEqual(bar.current, 0)

    def test_update(self) -> None:
        """测试更新。"""
        bar = ProgressBar(total=100)
        bar.update(50)
        self.assertEqual(bar.current, 50)

    def test_update_auto(self) -> None:
        """测试自动递增。"""
        bar = ProgressBar(total=100)
        bar.update()
        bar.update()
        self.assertEqual(bar.current, 2)

    def test_context_manager(self) -> None:
        """测试上下文管理器。"""
        with ProgressBar(total=10) as bar:
            bar.update(10)
        self.assertEqual(bar.current, 10)


class TestSetupLogging(unittest.TestCase):
    """日志配置测试。"""

    def test_setup_logging(self) -> None:
        """测试日志配置。"""
        logger = setup_logging(level="DEBUG")
        self.assertIsNotNone(logger)
        self.assertEqual(logger.level, 10)  # DEBUG = 10

    def test_setup_logging_info(self) -> None:
        """测试INFO级别日志配置。"""
        logger = setup_logging(level="INFO")
        self.assertEqual(logger.level, 20)  # INFO = 20


if __name__ == "__main__":
    unittest.main()
