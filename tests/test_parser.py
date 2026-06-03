"""
CrawlPilot - HTMLParser 测试模块

测试HTML解析引擎的各项功能。
"""

import unittest

from crawl_pilot.parser import HTMLParser, SelectorResult
from crawl_pilot.utils import ParseError


# 测试用HTML
SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="description" content="Test page description">
    <meta name="keywords" content="test, html, parser">
    <meta property="og:title" content="OG Test Title">
    <meta property="og:description" content="OG Description">
    <title>Test Page Title</title>
</head>
<body>
    <h1 class="main-title" id="title">Hello World</h1>
    <div class="content">
        <p class="intro">This is a test paragraph.</p>
        <p class="body-text">Another paragraph with <strong>bold</strong> text.</p>
        <a href="/page1" class="link internal">Page 1</a>
        <a href="/page2" class="link internal">Page 2</a>
        <a href="https://external.com" class="link external">External Link</a>
    </div>
    <div class="sidebar">
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
    </div>
    <table class="data-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>Age</th>
                <th>City</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Alice</td>
                <td>30</td>
                <td>Beijing</td>
            </tr>
            <tr>
                <td>Bob</td>
                <td>25</td>
                <td>Shanghai</td>
            </tr>
        </tbody>
    </table>
    <script type="application/ld+json">
    {"@type": "Article", "name": "Test Article"}
    </script>
</body>
</html>
"""


class TestHTMLParserBasic(unittest.TestCase):
    """HTMLParser 基础功能测试。"""

    def setUp(self) -> None:
        """设置测试。"""
        self.parser = HTMLParser(SAMPLE_HTML, url="https://example.com")

    def test_init(self) -> None:
        """测试初始化。"""
        self.assertIsNotNone(self.parser.html)
        self.assertEqual(self.parser.url, "https://example.com")

    def test_title(self) -> None:
        """测试标题提取。"""
        self.assertEqual(self.parser.title, "Test Page Title")

    def test_meta_description(self) -> None:
        """测试meta描述提取。"""
        self.assertEqual(self.parser.meta_description, "Test page description")

    def test_meta_keywords(self) -> None:
        """测试meta关键词提取。"""
        self.assertEqual(self.parser.meta_keywords, "test, html, parser")


class TestCSSSelector(unittest.TestCase):
    """CSS选择器测试。"""

    def setUp(self) -> None:
        """设置测试。"""
        self.parser = HTMLParser(SAMPLE_HTML, url="https://example.com")

    def test_tag_selector(self) -> None:
        """测试标签选择器。"""
        result = self.parser.css("h1")
        self.assertTrue(result)
        self.assertEqual(len(result), 1)
        self.assertIn("Hello World", result.text)

    def test_class_selector(self) -> None:
        """测试类选择器。"""
        result = self.parser.css("p.intro")
        self.assertTrue(result)
        self.assertEqual(len(result), 1)
        self.assertIn("test paragraph", result.text)

    def test_id_selector(self) -> None:
        """测试ID选择器。"""
        result = self.parser.css("#title")
        self.assertTrue(result)
        self.assertEqual(len(result), 1)

    def test_multiple_class(self) -> None:
        """测试多类选择器。"""
        result = self.parser.css("a.internal")
        self.assertTrue(result)
        self.assertEqual(len(result), 2)

    def test_descendant_selector(self) -> None:
        """测试后代选择器。"""
        result = self.parser.css("div.content p")
        self.assertTrue(result)
        self.assertGreaterEqual(len(result), 2)

    def test_no_match(self) -> None:
        """测试无匹配。"""
        result = self.parser.css(".nonexistent")
        self.assertFalse(result)
        self.assertEqual(len(result), 0)

    def test_attr_selector(self) -> None:
        """测试属性选择器。"""
        result = self.parser.css('meta[name="description"]')
        self.assertTrue(result)

    def test_selector_result_first(self) -> None:
        """测试first属性。"""
        result = self.parser.css("p")
        first = result.first
        self.assertIsNotNone(first)

    def test_selector_result_last(self) -> None:
        """测试last属性。"""
        result = self.parser.css("p")
        last = result.last
        self.assertIsNotNone(last)

    def test_selector_result_texts(self) -> None:
        """测试texts属性。"""
        result = self.parser.css("li")
        texts = result.texts
        self.assertEqual(len(texts), 3)
        self.assertIn("Item 1", texts)

    def test_selector_result_bool(self) -> None:
        """测试布尔值。"""
        self.assertTrue(self.parser.css("h1"))
        self.assertFalse(self.parser.css(".nonexistent"))

    def test_selector_result_getitem(self) -> None:
        """测试索引访问。"""
        result = self.parser.css("li")
        self.assertTrue(result[0])
        self.assertTrue(result[1])


class TestLinkExtraction(unittest.TestCase):
    """链接提取测试。"""

    def setUp(self) -> None:
        """设置测试。"""
        self.parser = HTMLParser(SAMPLE_HTML, url="https://example.com")

    def test_all_links(self) -> None:
        """测试所有链接提取。"""
        links = self.parser.links
        self.assertGreater(len(links), 0)
        # 应包含绝对URL
        self.assertIn("https://example.com/page1", links)
        self.assertIn("https://external.com", links)

    def test_internal_links(self) -> None:
        """测试内部链接提取。"""
        internal = self.parser.internal_links
        self.assertGreater(len(internal), 0)
        for link in internal:
            self.assertIn("example.com", link)

    def test_external_links(self) -> None:
        """测试外部链接提取。"""
        external = self.parser.external_links
        self.assertGreater(len(external), 0)
        for link in external:
            self.assertNotIn("example.com", link)

    def test_unique_links(self) -> None:
        """测试去重链接。"""
        # 确保没有重复
        unique = self.parser.unique_links
        self.assertEqual(len(unique), len(set(unique)))


class TestTableExtraction(unittest.TestCase):
    """表格提取测试。"""

    def setUp(self) -> None:
        """设置测试。"""
        self.parser = HTMLParser(SAMPLE_HTML, url="https://example.com")

    def test_extract_table(self) -> None:
        """测试表格提取。"""
        rows = self.parser.extract_table("table.data-table")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Name"], "Alice")
        self.assertEqual(rows[1]["City"], "Shanghai")

    def test_extract_table_no_headers(self) -> None:
        """测试无表头表格提取。"""
        rows = self.parser.extract_table("table.data-table", headers=False)
        self.assertGreater(len(rows), 0)


class TestListExtraction(unittest.TestCase):
    """列表提取测试。"""

    def setUp(self) -> None:
        """设置测试。"""
        self.parser = HTMLParser(SAMPLE_HTML, url="https://example.com")

    def test_extract_list(self) -> None:
        """测试列表提取。"""
        items = self.parser.extract_list("li")
        self.assertEqual(len(items), 3)
        self.assertIn("Item 1", items)


class TestJSONLD(unittest.TestCase):
    """JSON-LD提取测试。"""

    def setUp(self) -> None:
        """设置测试。"""
        self.parser = HTMLParser(SAMPLE_HTML, url="https://example.com")

    def test_json_ld(self) -> None:
        """测试JSON-LD提取。"""
        json_ld = self.parser.json_ld
        self.assertGreater(len(json_ld), 0)
        self.assertEqual(json_ld[0]["@type"], "Article")
        self.assertEqual(json_ld[0]["name"], "Test Article")


class TestOGData(unittest.TestCase):
    """Open Graph数据提取测试。"""

    def setUp(self) -> None:
        """设置测试。"""
        self.parser = HTMLParser(SAMPLE_HTML, url="https://example.com")

    def test_og_data(self) -> None:
        """测试OG数据提取。"""
        og = self.parser.og_data
        self.assertEqual(og["title"], "OG Test Title")
        self.assertEqual(og["description"], "OG Description")


class TestParserRepr(unittest.TestCase):
    """解析器字符串表示测试。"""

    def test_repr(self) -> None:
        """测试repr。"""
        parser = HTMLParser("<html></html>")
        repr_str = repr(parser)
        self.assertIn("HTMLParser", repr_str)


if __name__ == "__main__":
    unittest.main()
