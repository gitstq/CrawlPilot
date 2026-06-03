"""
CrawlPilot - Pipeline 测试模块

测试数据提取管道的各项功能。
"""

import unittest

from crawl_pilot.pipeline import (
    DataExtractor,
    DataCleaner,
    DataTransformer,
    Pipeline,
)

# 测试用HTML
SAMPLE_HTML = """
<html>
<head><title>Test Page</title></head>
<body>
    <h1 class="title">Product Name</h1>
    <div class="price">$99.99</div>
    <p class="description">A great product for <em>everyone</em>.</p>
    <a href="/product/1" class="link">Product 1</a>
    <a href="/product/2" class="link">Product 2</a>
    <div class="items">
        <div class="item">
            <span class="name">Item A</span>
            <span class="value">100</span>
        </div>
        <div class="item">
            <span class="name">Item B</span>
            <span class="value">200</span>
        </div>
    </div>
</body>
</html>
"""


class TestDataExtractor(unittest.TestCase):
    """DataExtractor 测试。"""

    def test_extract_css(self) -> None:
        """测试CSS选择器提取。"""
        extractor = DataExtractor()
        extractor.add_rule("title", css="h1.title")
        result = extractor.extract(SAMPLE_HTML)
        self.assertIn("Product Name", result["title"])

    def test_extract_multiple_fields(self) -> None:
        """测试多字段提取。"""
        extractor = DataExtractor()
        extractor.add_rule("title", css="h1.title")
        extractor.add_rule("price", css="div.price")
        extractor.add_rule("description", css="p.description")
        result = extractor.extract(SAMPLE_HTML)
        self.assertIn("Product Name", result["title"])
        self.assertIn("99.99", result["price"])

    def test_extract_with_attribute(self) -> None:
        """测试属性提取。"""
        extractor = DataExtractor()
        extractor.add_rule("links", css="a.link", attribute="href", multiple=True)
        result = extractor.extract(SAMPLE_HTML)
        self.assertIsInstance(result["links"], list)
        self.assertIn("/product/1", result["links"])

    def test_extract_with_regex(self) -> None:
        """测试正则提取。"""
        extractor = DataExtractor()
        extractor.add_rule("price_num", regex=r"\$([\d.]+)")
        result = extractor.extract(SAMPLE_HTML)
        self.assertEqual(result["price_num"], "99.99")

    def test_extract_default_value(self) -> None:
        """测试默认值。"""
        extractor = DataExtractor()
        extractor.add_rule("nonexistent", css=".nonexistent", default="N/A")
        result = extractor.extract(SAMPLE_HTML)
        self.assertEqual(result["nonexistent"], "N/A")

    def test_extract_many(self) -> None:
        """测试批量提取。"""
        extractor = DataExtractor()
        extractor.add_rule("name", css="span.name")
        extractor.add_rule("value", css="span.value")
        results = extractor.extract_many(SAMPLE_HTML, item_selector="div.item")
        self.assertEqual(len(results), 2)
        self.assertIn("Item A", results[0]["name"])
        self.assertIn("200", results[1]["value"])

    def test_chain_add_rule(self) -> None:
        """测试链式添加规则。"""
        extractor = DataExtractor()
        extractor.add_rule("f1", css="h1").add_rule("f2", css="p")
        self.assertEqual(len(extractor.rules), 2)

    def test_clear_rules(self) -> None:
        """测试清除规则。"""
        extractor = DataExtractor()
        extractor.add_rule("f1", css="h1")
        extractor.clear()
        self.assertEqual(len(extractor.rules), 0)

    def test_no_rule_error(self) -> None:
        """测试无规则错误。"""
        extractor = DataExtractor()
        with self.assertRaises(ValueError):
            extractor.add_rule("f1")


class TestDataCleaner(unittest.TestCase):
    """DataCleaner 测试。"""

    def test_strip_whitespace(self) -> None:
        """测试去除空白。"""
        cleaner = DataCleaner()
        cleaner.strip_whitespace("title", "desc")
        result = cleaner.clean({"title": "  hello  ", "desc": "  world  "})
        self.assertEqual(result["title"], "hello")
        self.assertEqual(result["desc"], "world")

    def test_normalize_whitespace(self) -> None:
        """测试空白规范化。"""
        cleaner = DataCleaner()
        cleaner.normalize_whitespace("text")
        result = cleaner.clean({"text": "hello   \n  world"})
        self.assertEqual(result["text"], "hello world")

    def test_remove_html(self) -> None:
        """测试去除HTML标签。"""
        cleaner = DataCleaner()
        cleaner.remove_html("content")
        result = cleaner.clean({"content": "<p>Hello <em>world</em></p>"})
        self.assertEqual(result["content"], "Hello world")

    def test_to_float(self) -> None:
        """测试转换为浮点数。"""
        cleaner = DataCleaner()
        cleaner.to_float("price")
        result = cleaner.clean({"price": "$99.99"})
        self.assertAlmostEqual(result["price"], 99.99)

    def test_to_int(self) -> None:
        """测试转换为整数。"""
        cleaner = DataCleaner()
        cleaner.to_int("count")
        result = cleaner.clean({"count": "42 items"})
        self.assertEqual(result["count"], 42)

    def test_fill_default(self) -> None:
        """测试默认值填充。"""
        cleaner = DataCleaner()
        cleaner.fill_default(status="unknown", count=0)
        result = cleaner.clean({"title": "Hello"})
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["count"], 0)

    def test_remove_empty(self) -> None:
        """测试移除空值。"""
        cleaner = DataCleaner()
        cleaner.remove_empty("desc")
        result = cleaner.clean({"title": "Hello", "desc": "   "})
        self.assertNotIn("desc", result)
        self.assertIn("title", result)

    def test_clean_many(self) -> None:
        """测试批量清洗。"""
        cleaner = DataCleaner()
        cleaner.strip_whitespace("name")
        results = cleaner.clean_many([
            {"name": "  Alice  "},
            {"name": "  Bob  "},
        ])
        self.assertEqual(results[0]["name"], "Alice")
        self.assertEqual(results[1]["name"], "Bob")

    def test_chain_operations(self) -> None:
        """测试链式操作。"""
        cleaner = DataCleaner()
        cleaner.strip_whitespace("name").remove_html("desc").to_float("price")
        self.assertEqual(len(cleaner._operations), 3)

    def test_custom_function(self) -> None:
        """测试自定义函数。"""
        def uppercase(data):
            if "name" in data:
                data["name"] = data["name"].upper()
            return data

        cleaner = DataCleaner()
        cleaner.apply_custom(uppercase)
        result = cleaner.clean({"name": "hello"})
        self.assertEqual(result["name"], "HELLO")


class TestDataTransformer(unittest.TestCase):
    """DataTransformer 测试。"""

    def test_rename(self) -> None:
        """测试字段重命名。"""
        transformer = DataTransformer()
        transformer.rename({"old_name": "new_name"})
        result = transformer.transform({"old_name": "Hello"})
        self.assertEqual(result["new_name"], "Hello")
        self.assertNotIn("old_name", result)

    def test_keep(self) -> None:
        """测试字段保留。"""
        transformer = DataTransformer()
        transformer.keep("name", "url")
        result = transformer.transform({"name": "A", "url": "B", "extra": "C"})
        self.assertIn("name", result)
        self.assertIn("url", result)
        self.assertNotIn("extra", result)

    def test_remove(self) -> None:
        """测试字段删除。"""
        transformer = DataTransformer()
        transformer.remove("extra")
        result = transformer.transform({"name": "A", "extra": "B"})
        self.assertNotIn("extra", result)

    def test_add_field_value(self) -> None:
        """测试添加固定值字段。"""
        transformer = DataTransformer()
        transformer.add_field("source", value="crawl_pilot")
        result = transformer.transform({"name": "A"})
        self.assertEqual(result["source"], "crawl_pilot")

    def test_add_field_function(self) -> None:
        """测试添加计算字段。"""
        transformer = DataTransformer()
        transformer.add_field("full_name", func=lambda d: f"{d.get('first', '')} {d.get('last', '')}")
        result = transformer.transform({"first": "John", "last": "Doe"})
        self.assertEqual(result["full_name"], "John Doe")

    def test_transform_many(self) -> None:
        """测试批量转换。"""
        transformer = DataTransformer()
        transformer.rename({"name": "title"})
        results = transformer.transform_many([
            {"name": "A"},
            {"name": "B"},
        ])
        self.assertEqual(results[0]["title"], "A")
        self.assertEqual(results[1]["title"], "B")


class TestPipeline(unittest.TestCase):
    """Pipeline 测试。"""

    def test_simple_pipeline(self) -> None:
        """测试简单管道。"""
        pipeline = Pipeline()
        pipeline.extract("title", css="h1.title")
        pipeline.extract("price", css="div.price")
        result = pipeline.run(SAMPLE_HTML)
        self.assertIn("Product Name", result["title"])
        self.assertIn("99.99", result["price"])

    def test_pipeline_with_clean(self) -> None:
        """测试带清洗的管道。"""
        pipeline = Pipeline()
        pipeline.extract("title", css="h1.title")
        pipeline.extract("desc", css="p.description")
        pipeline.strip_whitespace("title", "desc")
        pipeline.remove_html("desc")
        result = pipeline.run(SAMPLE_HTML)
        self.assertIn("Product Name", result["title"])
        # em标签应被去除
        self.assertNotIn("<em>", result["desc"])

    def test_pipeline_with_transform(self) -> None:
        """测试带转换的管道。"""
        pipeline = Pipeline()
        pipeline.extract("title", css="h1.title")
        pipeline.extract("price", css="div.price")
        pipeline.rename({"title": "name"})
        pipeline.add_field("source", value="test")
        result = pipeline.run(SAMPLE_HTML)
        self.assertIn("name", result)
        self.assertNotIn("title", result)
        self.assertEqual(result["source"], "test")

    def test_pipeline_extract_many(self) -> None:
        """测试批量提取管道。"""
        pipeline = Pipeline()
        pipeline.extract("name", css="span.name")
        pipeline.extract("value", css="span.value")
        results = pipeline.run(SAMPLE_HTML, item_selector="div.item")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)

    def test_pipeline_results_property(self) -> None:
        """测试结果属性。"""
        pipeline = Pipeline()
        pipeline.extract("title", css="h1.title")
        pipeline.run(SAMPLE_HTML)
        self.assertEqual(len(pipeline.results), 1)

    def test_pipeline_clear(self) -> None:
        """测试管道清除。"""
        pipeline = Pipeline()
        pipeline.extract("title", css="h1")
        pipeline.run(SAMPLE_HTML)
        pipeline.clear()
        self.assertEqual(len(pipeline.results), 0)
        self.assertEqual(len(pipeline.extractor.rules), 0)


if __name__ == "__main__":
    unittest.main()
