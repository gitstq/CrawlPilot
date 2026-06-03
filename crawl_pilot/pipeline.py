"""
CrawlPilot - 数据提取管道模块

提供链式数据处理功能，包括数据提取、清洗和转换。

核心类：
    - DataExtractor: 基于规则的数据提取器
    - DataCleaner: 数据清洗器
    - DataTransformer: 数据转换器
    - Pipeline: 链式数据处理管道
"""

import logging
import re
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional, Union

from crawl_pilot.parser import HTMLParser
from crawl_pilot.utils import clean_text, extract_numbers

logger = logging.getLogger("crawl_pilot.pipeline")


# ============================================================
# DataExtractor - 数据提取器
# ============================================================

class DataExtractor:
    """基于规则的数据提取器。

    支持多种提取规则：
    - CSS选择器提取
    - XPath提取
    - 正则表达式提取
    - 属性提取

    Attributes:
        rules: 提取规则列表

    Examples:
        >>> extractor = DataExtractor()
        >>> extractor.add_rule("title", css="h1.title")
        >>> extractor.add_rule("links", css="a[href]", attribute="href")
        >>> extractor.add_rule("price", regex=r"\\$([\\d.]+)")
        >>> results = extractor.extract(html_content)
    """

    def __init__(self) -> None:
        """初始化数据提取器。"""
        self.rules: List[Dict[str, Any]] = []

    def add_rule(
        self,
        field_name: str,
        css: Optional[str] = None,
        xpath: Optional[str] = None,
        regex: Optional[str] = None,
        attribute: Optional[str] = None,
        multiple: bool = False,
        default: Any = None,
        clean: bool = True,
    ) -> "DataExtractor":
        """添加提取规则。

        Args:
            field_name: 字段名
            css: CSS选择器
            xpath: XPath表达式
            regex: 正则表达式
            attribute: 要提取的属性名（不指定则提取文本）
            multiple: 是否提取多个值（返回列表）
            default: 默认值（提取失败时使用）
            clean: 是否清洗提取结果

        Returns:
            self（支持链式调用）

        Raises:
            ValueError: 未指定任何提取规则时
        """
        if not any([css, xpath, regex]):
            raise ValueError("必须指定至少一种提取规则（css/xpath/regex）")

        rule: Dict[str, Any] = {
            "field_name": field_name,
            "css": css,
            "xpath": xpath,
            "regex": regex,
            "attribute": attribute,
            "multiple": multiple,
            "default": default,
            "clean": clean,
        }
        self.rules.append(rule)
        return self

    def extract(self, html: Union[str, HTMLParser]) -> Dict[str, Any]:
        """从HTML内容中提取数据。

        Args:
            html: HTML字符串或HTMLParser实例

        Returns:
            提取的数据字典
        """
        if isinstance(html, str):
            parser = HTMLParser(html)
        else:
            parser = html

        result: Dict[str, Any] = {}

        for rule in self.rules:
            field = rule["field_name"]
            value = self._apply_rule(parser, rule)
            result[field] = value

        return result

    def extract_many(
        self,
        html: Union[str, HTMLParser],
        item_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """从HTML中提取多条数据。

        先用item_selector定位到每个数据项，然后对每个数据项应用提取规则。

        Args:
            html: HTML字符串或HTMLParser实例
            item_selector: 数据项的CSS选择器

        Returns:
            数据字典列表
        """
        if isinstance(html, str):
            parser = HTMLParser(html)
        else:
            parser = html

        if not item_selector:
            return [self.extract(parser)]

        items = parser.css(item_selector)
        results: List[Dict[str, Any]] = []

        for i in range(len(items)):
            item_result = items[i]
            item_html = item_result.raw_html
            item_parser = HTMLParser(item_html, url=parser.base_url)
            data = self.extract(item_parser)
            results.append(data)

        return results

    def _apply_rule(self, parser: HTMLParser, rule: Dict[str, Any]) -> Any:
        """应用单条提取规则。

        Args:
            parser: HTMLParser实例
            rule: 提取规则

        Returns:
            提取的值
        """
        value: Any = rule.get("default")

        # CSS选择器提取
        if rule["css"]:
            result = parser.css(rule["css"])
            if result:
                if rule["attribute"]:
                    values = result.attr(rule["attribute"])
                    value = values[0] if values and not rule["multiple"] else values
                else:
                    if rule["multiple"]:
                        value = result.texts
                    else:
                        value = result.text

        # XPath提取
        elif rule["xpath"]:
            result = parser.xpath(rule["xpath"])
            if result:
                if rule["multiple"]:
                    value = result.texts
                else:
                    value = result.text

        # 正则表达式提取
        elif rule["regex"]:
            matches = re.findall(rule["regex"], parser.body_text)
            if matches:
                if rule["multiple"]:
                    value = matches
                else:
                    value = matches[0]

        # 数据清洗
        if rule["clean"] and isinstance(value, str):
            value = clean_text(value)
        elif rule["clean"] and isinstance(value, list):
            value = [clean_text(v) if isinstance(v, str) else v for v in value]

        return value

    def clear(self) -> "DataExtractor":
        """清除所有提取规则。

        Returns:
            self
        """
        self.rules.clear()
        return self

    def __repr__(self) -> str:
        return f"<DataExtractor [{len(self.rules)} rules]>"


# ============================================================
# DataCleaner - 数据清洗器
# ============================================================

class DataCleaner:
    """数据清洗器。

    提供常见的数据清洗操作：
    - 去除HTML标签
    - 文本规范化
    - 类型转换
    - 空值处理
    - 去除重复

    Attributes:
        rules: 清洗规则列表

    Examples:
        >>> cleaner = DataCleaner()
        >>> cleaner.strip_whitespace("title", "description")
        >>> cleaner.remove_html("content")
        >>> cleaner.to_float("price")
        >>> cleaned = cleaner.clean(data)
    """

    def __init__(self) -> None:
        """初始化数据清洗器。"""
        self._operations: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []

    def strip_whitespace(self, *fields: str) -> "DataCleaner":
        """去除指定字段的空白字符。

        Args:
            *fields: 字段名列表

        Returns:
            self（支持链式调用）
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            for field in fields:
                if field in data and isinstance(data[field], str):
                    data[field] = data[field].strip()
            return data

        self._operations.append(operation)
        return self

    def normalize_whitespace(self, *fields: str) -> "DataCleaner":
        """规范化指定字段的空白字符。

        将多个空白字符合并为一个空格。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            for field in fields:
                if field in data and isinstance(data[field], str):
                    data[field] = re.sub(r"\s+", " ", data[field]).strip()
            return data

        self._operations.append(operation)
        return self

    def remove_html(self, *fields: str) -> "DataCleaner":
        """去除指定字段中的HTML标签。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            for field in fields:
                if field in data and isinstance(data[field], str):
                    data[field] = re.sub(r"<[^>]+>", "", data[field])
            return data

        self._operations.append(operation)
        return self

    def to_float(self, *fields: str) -> "DataCleaner":
        """将指定字段转换为浮点数。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            for field in fields:
                if field in data:
                    try:
                        if isinstance(data[field], str):
                            # 提取数字
                            numbers = extract_numbers(data[field])
                            if numbers:
                                data[field] = float(numbers[0])
                        elif isinstance(data[field], (int, float)):
                            data[field] = float(data[field])
                    except (ValueError, TypeError):
                        pass
            return data

        self._operations.append(operation)
        return self

    def to_int(self, *fields: str) -> "DataCleaner":
        """将指定字段转换为整数。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            for field in fields:
                if field in data:
                    try:
                        if isinstance(data[field], str):
                            numbers = extract_numbers(data[field])
                            if numbers:
                                data[field] = int(float(numbers[0]))
                        elif isinstance(data[field], float):
                            data[field] = int(data[field])
                    except (ValueError, TypeError):
                        pass
            return data

        self._operations.append(operation)
        return self

    def remove_empty(self, *fields: str) -> "DataCleaner":
        """移除指定字段中的空值。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            for field in fields:
                if field in data:
                    value = data[field]
                    if isinstance(value, str) and not value.strip():
                        del data[field]
                    elif value is None:
                        del data[field]
            return data

        self._operations.append(operation)
        return self

    def fill_default(self, **defaults: Any) -> "DataCleaner":
        """为缺失字段填充默认值。

        Args:
            **defaults: 字段名和默认值的映射

        Returns:
            self

        Examples:
            >>> cleaner.fill_default(status="unknown", count=0)
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            for field, default_value in defaults.items():
                if field not in data or data[field] is None:
                    data[field] = default_value
            return data

        self._operations.append(operation)
        return self

    def apply_custom(self, func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> "DataCleaner":
        """应用自定义清洗函数。

        Args:
            func: 自定义清洗函数，接收数据字典，返回修改后的数据字典

        Returns:
            self
        """
        self._operations.append(func)
        return self

    def clean(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """对数据进行清洗。

        Args:
            data: 待清洗的数据字典

        Returns:
            清洗后的数据字典
        """
        result = deepcopy(data)
        for operation in self._operations:
            result = operation(result)
        return result

    def clean_many(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对多条数据进行清洗。

        Args:
            data_list: 数据字典列表

        Returns:
            清洗后的数据字典列表
        """
        return [self.clean(item) for item in data_list]

    def clear(self) -> "DataCleaner":
        """清除所有清洗操作。

        Returns:
            self
        """
        self._operations.clear()
        return self

    def __repr__(self) -> str:
        return f"<DataCleaner [{len(self._operations)} operations]>"


# ============================================================
# DataTransformer - 数据转换器
# ============================================================

class DataTransformer:
    """数据转换器。

    提供数据转换操作：
    - 字段重命名
    - 字段映射
    - 字段选择
    - 字段删除

    Attributes:
        _operations: 转换操作列表

    Examples:
        >>> transformer = DataTransformer()
        >>> transformer.rename({"old_name": "new_name"})
        >>> transformer.keep("title", "url", "content")
        >>> transformed = transformer.transform(data)
    """

    def __init__(self) -> None:
        """初始化数据转换器。"""
        self._operations: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []

    def rename(self, mapping: Dict[str, str]) -> "DataTransformer":
        """重命名字段。

        Args:
            mapping: 旧字段名到新字段名的映射

        Returns:
            self

        Examples:
            >>> transformer.rename({"title": "name", "url": "link"})
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            for old_name, new_name in mapping.items():
                if old_name in data:
                    data[new_name] = data.pop(old_name)
            return data

        self._operations.append(operation)
        return self

    def map_values(self, field: str, mapping: Dict[Any, Any]) -> "DataTransformer":
        """映射字段值。

        Args:
            field: 字段名
            mapping: 值映射字典

        Returns:
            self

        Examples:
            >>> transformer.map_values("status", {"1": "active", "0": "inactive"})
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            if field in data and data[field] in mapping:
                data[field] = mapping[data[field]]
            return data

        self._operations.append(operation)
        return self

    def keep(self, *fields: str) -> "DataTransformer":
        """只保留指定字段。

        Args:
            *fields: 要保留的字段名列表

        Returns:
            self
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            return {k: v for k, v in data.items() if k in fields}

        self._operations.append(operation)
        return self

    def remove(self, *fields: str) -> "DataTransformer":
        """删除指定字段。

        Args:
            *fields: 要删除的字段名列表

        Returns:
            self
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            for field in fields:
                data.pop(field, None)
            return data

        self._operations.append(operation)
        return self

    def add_field(
        self,
        name: str,
        value: Any = None,
        func: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> "DataTransformer":
        """添加新字段。

        Args:
            name: 新字段名
            value: 固定值（与func二选一）
            func: 计算函数（接收数据字典，返回字段值）

        Returns:
            self
        """
        def operation(data: Dict[str, Any]) -> Dict[str, Any]:
            if func:
                data[name] = func(data)
            else:
                data[name] = value
            return data

        self._operations.append(operation)
        return self

    def apply_custom(self, func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> "DataTransformer":
        """应用自定义转换函数。

        Args:
            func: 自定义转换函数

        Returns:
            self
        """
        self._operations.append(func)
        return self

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """对数据进行转换。

        Args:
            data: 待转换的数据字典

        Returns:
            转换后的数据字典
        """
        result = deepcopy(data)
        for operation in self._operations:
            result = operation(result)
        return result

    def transform_many(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对多条数据进行转换。

        Args:
            data_list: 数据字典列表

        Returns:
            转换后的数据字典列表
        """
        return [self.transform(item) for item in data_list]

    def clear(self) -> "DataTransformer":
        """清除所有转换操作。

        Returns:
            self
        """
        self._operations.clear()
        return self

    def __repr__(self) -> str:
        return f"<DataTransformer [{len(self._operations)} operations]>"


# ============================================================
# Pipeline - 链式数据处理管道
# ============================================================

class Pipeline:
    """链式数据处理管道。

    将数据提取、清洗和转换组合为一个处理管道，
    支持链式调用。

    Attributes:
        extractor: 数据提取器
        cleaner: 数据清洗器
        transformer: 数据转换器
        _output_handler: 输出处理函数

    Examples:
        >>> pipeline = Pipeline()
        >>> pipeline.extract(css="h1", field="title") \\
        ...        .extract(css="p.content", field="content") \\
        ...        .clean().strip_whitespace("title", "content") \\
        ...        .transform().rename({"title": "name"}) \\
        ...        .run(html_content)
        {'name': 'Hello', 'content': 'World'}
    """

    def __init__(self) -> None:
        """初始化管道。"""
        self.extractor = DataExtractor()
        self.cleaner = DataCleaner()
        self.transformer = DataTransformer()
        self._output_handler: Optional[Callable[[Any], None]] = None
        self._results: List[Dict[str, Any]] = []

    def extract(
        self,
        field: str,
        css: Optional[str] = None,
        xpath: Optional[str] = None,
        regex: Optional[str] = None,
        attribute: Optional[str] = None,
        multiple: bool = False,
        default: Any = None,
    ) -> "Pipeline":
        """添加提取规则。

        Args:
            field: 字段名
            css: CSS选择器
            xpath: XPath表达式
            regex: 正则表达式
            attribute: 属性名
            multiple: 是否提取多个值
            default: 默认值

        Returns:
            self（支持链式调用）
        """
        self.extractor.add_rule(
            field_name=field,
            css=css,
            xpath=xpath,
            regex=regex,
            attribute=attribute,
            multiple=multiple,
            default=default,
        )
        return self

    def clean(self) -> "Pipeline":
        """进入清洗配置模式。

        Returns:
            DataCleaner实例（可通过链式调用配置后继续管道）
        """
        return self

    def strip_whitespace(self, *fields: str) -> "Pipeline":
        """去除指定字段的空白字符。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        self.cleaner.strip_whitespace(*fields)
        return self

    def normalize_whitespace(self, *fields: str) -> "Pipeline":
        """规范化指定字段的空白字符。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        self.cleaner.normalize_whitespace(*fields)
        return self

    def remove_html(self, *fields: str) -> "Pipeline":
        """去除指定字段中的HTML标签。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        self.cleaner.remove_html(*fields)
        return self

    def to_float(self, *fields: str) -> "Pipeline":
        """将指定字段转换为浮点数。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        self.cleaner.to_float(*fields)
        return self

    def to_int(self, *fields: str) -> "Pipeline":
        """将指定字段转换为整数。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        self.cleaner.to_int(*fields)
        return self

    def fill_default(self, **defaults: Any) -> "Pipeline":
        """为缺失字段填充默认值。

        Args:
            **defaults: 字段名和默认值的映射

        Returns:
            self
        """
        self.cleaner.fill_default(**defaults)
        return self

    def transform(self) -> "Pipeline":
        """进入转换配置模式。

        Returns:
            self
        """
        return self

    def rename(self, mapping: Dict[str, str]) -> "Pipeline":
        """重命名字段。

        Args:
            mapping: 旧字段名到新字段名的映射

        Returns:
            self
        """
        self.transformer.rename(mapping)
        return self

    def keep(self, *fields: str) -> "Pipeline":
        """只保留指定字段。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        self.transformer.keep(*fields)
        return self

    def remove(self, *fields: str) -> "Pipeline":
        """删除指定字段。

        Args:
            *fields: 字段名列表

        Returns:
            self
        """
        self.transformer.remove(*fields)
        return self

    def add_field(
        self,
        name: str,
        value: Any = None,
        func: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> "Pipeline":
        """添加新字段。

        Args:
            name: 新字段名
            value: 固定值
            func: 计算函数

        Returns:
            self
        """
        self.transformer.add_field(name, value, func)
        return self

    def output(self, handler: Optional[Callable[[Any], None]] = None) -> "Pipeline":
        """设置输出处理函数。

        Args:
            handler: 输出处理函数

        Returns:
            self
        """
        self._output_handler = handler
        return self

    def run(
        self,
        html: Union[str, HTMLParser],
        item_selector: Optional[str] = None,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """运行管道处理数据。

        完整执行：提取 -> 清洗 -> 转换 -> 输出

        Args:
            html: HTML字符串或HTMLParser实例
            item_selector: 数据项选择器（提取多条数据时使用）

        Returns:
            处理后的数据字典或列表
        """
        # 提取
        if item_selector:
            results = self.extractor.extract_many(html, item_selector)
        else:
            results = [self.extractor.extract(html)]

        # 清洗
        results = self.cleaner.clean_many(results)

        # 转换
        results = self.transformer.transform_many(results)

        # 存储
        self._results.extend(results)

        # 输出
        if self._output_handler:
            for result in results:
                self._output_handler(result)

        # 返回结果
        if item_selector or len(results) > 1:
            return results
        return results[0] if results else {}

    def run_many(
        self,
        html_list: List[Union[str, HTMLParser]],
    ) -> List[Dict[str, Any]]:
        """对多个HTML内容运行管道。

        Args:
            html_list: HTML内容列表

        Returns:
            处理后的数据字典列表
        """
        all_results: List[Dict[str, Any]] = []
        for html in html_list:
            result = self.run(html)
            if isinstance(result, list):
                all_results.extend(result)
            elif result:
                all_results.append(result)
        return all_results

    @property
    def results(self) -> List[Dict[str, Any]]:
        """获取所有已处理的结果。

        Returns:
            结果列表
        """
        return self._results

    def clear(self) -> "Pipeline":
        """清除管道中的所有配置和结果。

        Returns:
            self
        """
        self.extractor.clear()
        self.cleaner.clear()
        self.transformer.clear()
        self._output_handler = None
        self._results.clear()
        return self

    def __repr__(self) -> str:
        return (
            f"<Pipeline "
            f"extractor={self.extractor} "
            f"cleaner={self.cleaner} "
            f"transformer={self.transformer}>"
        )
