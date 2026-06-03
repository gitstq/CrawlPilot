"""
CrawlPilot - HTML解析引擎模块

提供HTML解析功能，支持CSS选择器、XPath、文本提取、链接提取、
元数据提取和结构化数据解析。

核心类：
    - SelectorResult: 选择器结果（支持链式调用）
    - HTMLParser: HTML解析引擎
"""

import json
import logging
import re
from html.parser import HTMLParser as StdHTMLParser
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

from crawl_pilot.utils import ParseError, clean_text, normalize_url

logger = logging.getLogger("crawl_pilot.parser")


# ============================================================
# 简易CSS选择器解析器
# ============================================================

class _CSSSelectorParser:
    """简易CSS选择器解析器。

    支持常见CSS选择器语法：
    - 标签选择器: div, p, a
    - 类选择器: .class-name
    - ID选择器: #id
    - 属性选择器: [attr], [attr=value], [attr~=value]
    - 后代选择器: div p
    - 子选择器: div > p
    - 通用选择器: *

    注意：这是一个轻量级实现，不支持伪类和复杂组合选择器。
    """

    @staticmethod
    def parse(selector: str) -> Dict[str, Any]:
        """解析CSS选择器为结构化表示。

        Args:
            selector: CSS选择器字符串

        Returns:
            解析后的选择器字典
        """
        result: Dict[str, Any] = {
            "tag": None,
            "id": None,
            "classes": [],
            "attrs": {},
            "combinator": "descendant",  # descendant, child
            "children": [],
        }

        # 分割组合选择器
        parts = _CSSSelectorParser._split_selector(selector)

        if len(parts) == 1:
            _CSSSelectorParser._parse_simple(parts[0].strip(), result)
        else:
            # 处理组合选择器
            _CSSSelectorParser._parse_simple(parts[-1].strip(), result)
            # 简化处理：只保留最后一个简单选择器的信息
            # 完整实现需要递归处理组合选择器

        return result

    @staticmethod
    def _split_selector(selector: str) -> List[str]:
        """分割组合选择器。

        Args:
            selector: CSS选择器字符串

        Returns:
            分割后的选择器部分列表
        """
        # 按空格分割（简化处理，不考虑括号内空格）
        parts = []
        current = ""
        depth = 0
        for char in selector:
            if char in ("[", "("):
                depth += 1
                current += char
            elif char in ("]", ")"):
                depth -= 1
                current += char
            elif char == " " and depth == 0:
                if current.strip():
                    parts.append(current.strip())
                current = ""
            else:
                current += char
        if current.strip():
            parts.append(current.strip())
        return parts

    @staticmethod
    def _parse_simple(selector: str, result: Dict[str, Any]) -> None:
        """解析简单选择器。

        Args:
            selector: 简单选择器字符串
            result: 结果字典（就地修改）
        """
        remaining = selector

        # 提取ID
        id_match = re.match(r".*#([a-zA-Z_][\w-]*)", remaining)
        if id_match:
            result["id"] = id_match.group(1)

        # 提取类名
        class_matches = re.findall(r"\.([a-zA-Z_][\w-]*)", remaining)
        if class_matches:
            result["classes"] = class_matches

        # 提取属性选择器
        attr_matches = re.findall(
            r"\[([a-zA-Z_][\w-]*)(?:([~|^$*]?=)([^\]]*))?\]",
            remaining,
        )
        for attr_name, operator, attr_value in attr_matches:
            if operator:
                result["attrs"][attr_name] = (operator, attr_value.strip("\"'"))
            else:
                result["attrs"][attr_name] = None

        # 提取标签名（去除ID、类、属性后的部分）
        tag = remaining
        tag = re.sub(r"#[a-zA-Z_][\w-]*", "", tag)
        tag = re.sub(r"\.[a-zA-Z_][\w-]*", "", tag)
        tag = re.sub(r"\[.*?\]", "", tag)
        tag = tag.strip().strip(">").strip()

        if tag and tag != "*":
            result["tag"] = tag.lower()


# ============================================================
# HTML元素表示
# ============================================================

class _HTMLElement:
    """HTML元素的轻量级表示。

    用于存储解析后的HTML元素信息。

    Attributes:
        tag: 标签名
        attrs: 属性字典
        text: 直接文本内容
        children: 子元素列表
        parent: 父元素
    """

    def __init__(
        self,
        tag: str,
        attrs: Optional[Dict[str, str]] = None,
        parent: Optional["_HTMLElement"] = None,
    ) -> None:
        """初始化HTML元素。

        Args:
            tag: 标签名
            attrs: 属性字典
            parent: 父元素
        """
        self.tag = tag.lower()
        self.attrs = attrs or {}
        self.text_parts: List[str] = []
        self.children: List[_HTMLElement] = []
        self.parent = parent

    @property
    def text(self) -> str:
        """获取元素的文本内容（包含所有子元素的文本）。

        Returns:
            文本内容字符串
        """
        parts = list(self.text_parts)
        for child in self.children:
            parts.append(child.text)
        return "".join(parts)

    @property
    def inner_text(self) -> str:
        """获取元素的内部文本（去除HTML标签）。

        Returns:
            清洗后的文本内容
        """
        return clean_text(self.text)

    @property
    def id(self) -> Optional[str]:
        """获取元素的ID属性。"""
        return self.attrs.get("id")

    @property
    def classes(self) -> List[str]:
        """获取元素的CSS类名列表。"""
        class_str = self.attrs.get("class", "")
        return class_str.split() if class_str else []

    def get_attr(self, name: str, default: str = "") -> str:
        """获取元素属性值。

        Args:
            name: 属性名
            default: 默认值

        Returns:
            属性值
        """
        return self.attrs.get(name, default)

    def matches_selector(self, selector_dict: Dict[str, Any]) -> bool:
        """检查元素是否匹配选择器。

        Args:
            selector_dict: 解析后的选择器字典

        Returns:
            匹配返回True
        """
        # 标签匹配
        if selector_dict["tag"] and selector_dict["tag"] != self.tag:
            return False

        # ID匹配
        if selector_dict["id"] and self.id != selector_dict["id"]:
            return False

        # 类名匹配
        if selector_dict["classes"]:
            element_classes = set(self.classes)
            if not all(c in element_classes for c in selector_dict["classes"]):
                return False

        # 属性匹配
        for attr_name, attr_value in selector_dict["attrs"].items():
            if attr_name not in self.attrs:
                return False
            if attr_value is not None:
                operator, expected = attr_value
                actual = self.attrs[attr_name]
                if operator == "=" and actual != expected:
                    return False
                elif operator == "~=" and expected not in actual.split():
                    return False
                elif operator == "|=" and not (
                    actual == expected or actual.startswith(expected + "-")
                ):
                    return False
                elif operator == "^=" and not actual.startswith(expected):
                    return False
                elif operator == "$=" and not actual.endswith(expected):
                    return False
                elif operator == "*=" and expected not in actual:
                    return False

        return True

    def find_all(
        self,
        selector_dict: Dict[str, Any],
        max_depth: int = 100,
    ) -> List["_HTMLElement"]:
        """查找所有匹配选择器的后代元素。

        Args:
            selector_dict: 解析后的选择器字典
            max_depth: 最大搜索深度

        Returns:
            匹配的元素列表
        """
        results: List[_HTMLElement] = []
        self._find_recursive(selector_dict, results, 0, max_depth)
        return results

    def _find_recursive(
        self,
        selector_dict: Dict[str, Any],
        results: List["_HTMLElement"],
        depth: int,
        max_depth: int,
    ) -> None:
        """递归查找匹配元素。

        Args:
            selector_dict: 选择器字典
            results: 结果列表
            depth: 当前深度
            max_depth: 最大深度
        """
        if depth > max_depth:
            return

        for child in self.children:
            if child.matches_selector(selector_dict):
                results.append(child)
            child._find_recursive(selector_dict, results, depth + 1, max_depth)

    def __repr__(self) -> str:
        attrs_str = " ".join(f'{k}="{v}"' for k, v in self.attrs.items())
        if attrs_str:
            return f"<_HTMLElement {self.tag} {attrs_str}>"
        return f"<_HTMLElement {self.tag}>"


# ============================================================
# HTML解析器（基于标准库）
# ============================================================

class _StdHTMLParserImpl(StdHTMLParser):
    """基于标准库html.parser的HTML解析器实现。

    将HTML解析为HTMLElement树结构。
    """

    VOID_ELEMENTS = frozenset({
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    })

    def __init__(self) -> None:
        """初始化解析器。"""
        super().__init__(convert_charrefs=True)
        self.root = _HTMLElement(tag="__root__")
        self._current = self.root
        self._text_buffer: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        """处理开始标签。"""
        attrs_dict = {k: v or "" for k, v in attrs}
        element = _HTMLElement(tag=tag, attrs=attrs_dict, parent=self._current)

        # 添加缓冲的文本
        if self._text_buffer:
            self._current.text_parts.extend(self._text_buffer)
            self._text_buffer = []

        self._current.children.append(element)
        if tag.lower() not in self.VOID_ELEMENTS:
            self._current = element

    def handle_endtag(self, tag: str) -> None:
        """处理结束标签。"""
        # 将缓冲的文本添加到当前元素
        if self._text_buffer:
            self._current.text_parts.extend(self._text_buffer)
            self._text_buffer = []

        # 向上查找匹配的开始标签
        node = self._current
        while node and node != self.root:
            if node.tag == tag.lower():
                self._current = node.parent if node.parent else self.root
                return
            node = node.parent
        # 未找到匹配标签，忽略

    def handle_data(self, data: str) -> None:
        """处理文本数据。"""
        self._text_buffer.append(data)

    def handle_comment(self, data: str) -> None:
        """处理注释（忽略）。"""
        pass

    def handle_decl(self, decl: str) -> None:
        """处理声明（忽略）。"""
        pass

    def handle_pi(self, data: str) -> None:
        """处理处理指令（忽略）。"""
        pass


# ============================================================
# SelectorResult - 选择器结果
# ============================================================

class SelectorResult:
    """选择器查询结果。

    封装一组匹配的HTML元素，提供便捷的数据提取方法。

    Attributes:
        elements: 匹配的HTMLElement列表
        raw_html: 原始HTML片段

    Examples:
        >>> result = parser.css("h1.title")
        >>> result.text
        'Hello World'
        >>> result.attr("href")
        '/page'
        >>> result[0].text
        'Hello World'
    """

    def __init__(
        self,
        elements: List[_HTMLElement],
        base_url: Optional[str] = None,
    ) -> None:
        """初始化选择器结果。

        Args:
            elements: 匹配的HTMLElement列表
            base_url: 基础URL（用于解析相对链接）
        """
        self.elements = elements
        self._base_url = base_url

    @property
    def raw_html(self) -> str:
        """获取所有匹配元素的原始HTML。

        Returns:
            原始HTML字符串
        """
        return "".join(self._element_to_html(el) for el in self.elements)

    @property
    def text(self) -> str:
        """获取所有匹配元素的文本内容。

        Returns:
            拼接的文本字符串
        """
        return "\n".join(el.inner_text for el in self.elements)

    @property
    def texts(self) -> List[str]:
        """获取所有匹配元素的文本内容列表。

        Returns:
            文本内容列表
        """
        return [el.inner_text for el in self.elements]

    @property
    def attrs(self) -> List[Dict[str, str]]:
        """获取所有匹配元素的属性字典列表。

        Returns:
            属性字典列表
        """
        return [el.attrs for el in self.elements]

    @property
    def first(self) -> Optional["SelectorResult"]:
        """获取第一个匹配元素。

        Returns:
            包含第一个元素的SelectorResult，无匹配返回None
        """
        if self.elements:
            return SelectorResult([self.elements[0]], self._base_url)
        return None

    @property
    def last(self) -> Optional["SelectorResult"]:
        """获取最后一个匹配元素。

        Returns:
            包含最后一个元素的SelectorResult，无匹配返回None
        """
        if self.elements:
            return SelectorResult([self.elements[-1]], self._base_url)
        return None

    def attr(self, name: str) -> List[str]:
        """获取所有匹配元素的指定属性值。

        Args:
            name: 属性名

        Returns:
            属性值列表
        """
        return [el.get_attr(name) for el in self.elements]

    def text_contains(self, keyword: str) -> "SelectorResult":
        """筛选包含指定文本的元素。

        Args:
            keyword: 关键词

        Returns:
            筛选后的SelectorResult
        """
        filtered = [
            el for el in self.elements
            if keyword.lower() in el.inner_text.lower()
        ]
        return SelectorResult(filtered, self._base_url)

    def has_attr(self, name: str) -> "SelectorResult":
        """筛选拥有指定属性的元素。

        Args:
            name: 属性名

        Returns:
            筛选后的SelectorResult
        """
        filtered = [el for el in self.elements if name in el.attrs]
        return SelectorResult(filtered, self._base_url)

    def regex(self, pattern: str) -> List[str]:
        """使用正则表达式从文本中提取。

        Args:
            pattern: 正则表达式

        Returns:
            匹配结果列表
        """
        results: List[str] = []
        for el in self.elements:
            matches = re.findall(pattern, el.text)
            results.extend(matches)
        return results

    def links(self, absolute: bool = True) -> List[str]:
        """提取所有匹配元素中的链接。

        Args:
            absolute: 是否转换为绝对URL

        Returns:
            链接URL列表
        """
        links: List[str] = []
        for el in self.elements:
            href = el.get_attr("href")
            if href:
                href = href.strip()
                if absolute and self._base_url:
                    href = urljoin(self._base_url, href)
                links.append(href)
        return links

    @staticmethod
    def _element_to_html(element: _HTMLElement) -> str:
        """将HTMLElement转换回HTML字符串。

        Args:
            element: HTML元素

        Returns:
            HTML字符串
        """
        attrs_str = ""
        for k, v in element.attrs.items():
            attrs_str += f' {k}="{v}"'

        if element.children:
            inner = "".join(
                SelectorResult._element_to_html(child)
                for child in element.children
            )
            text = "".join(element.text_parts)
            return f"<{element.tag}{attrs_str}>{text}{inner}</{element.tag}>"
        else:
            text = "".join(element.text_parts)
            return f"<{element.tag}{attrs_str}>{text}</{element.tag}>"

    def __len__(self) -> int:
        return len(self.elements)

    def __bool__(self) -> bool:
        return len(self.elements) > 0

    def __iter__(self):
        return iter(self.elements)

    def __getitem__(self, index: int) -> "SelectorResult":
        return SelectorResult([self.elements[index]], self._base_url)

    def __repr__(self) -> str:
        return f"<SelectorResult [{len(self.elements)} elements]>"


# ============================================================
# HTMLParser - HTML解析引擎
# ============================================================

class HTMLParser:
    """HTML解析引擎。

    提供统一的HTML解析接口，支持CSS选择器、XPath、文本提取、
    链接提取、元数据提取和结构化数据解析。

    优先使用lxml作为解析后端（高性能），如果不可用则回退到
    标准库实现。

    Attributes:
        html: 原始HTML内容
        url: 页面URL
        title: 页面标题
        base_url: 基础URL

    Examples:
        >>> parser = HTMLParser(html_content, url="https://example.com")
        >>> parser.css("h1").text
        'Hello World'
        >>> parser.xpath("//div[@class='content']/p")
        >>> parser.links
        ['https://example.com/page1', ...]
        >>> parser.title
        'Example Page'
    """

    def __init__(
        self,
        html: str,
        url: Optional[str] = None,
    ) -> None:
        """初始化HTML解析器。

        Args:
            html: HTML内容字符串
            url: 页面URL（用于解析相对链接）
        """
        self.html = html
        self.url = url
        self.base_url = url
        self._tree: Optional[_HTMLElement] = None
        self._lxml_tree: Optional[Any] = None
        self._use_lxml = self._check_lxml()

        # 解析HTML（始终构建stdlib tree作为后备）
        self._parse_with_stdlib()
        if self._use_lxml:
            self._parse_with_lxml()

    @staticmethod
    def _check_lxml() -> bool:
        """检查lxml是否可用。

        Returns:
            lxml可用返回True
        """
        try:
            from lxml import html as lxml_html  # type: ignore
            from lxml import etree  # type: ignore
            return True
        except ImportError:
            return False

    def _parse_with_stdlib(self) -> None:
        """使用标准库解析HTML。"""
        parser_impl = _StdHTMLParserImpl()
        try:
            parser_impl.feed(self.html)
        except Exception as e:
            logger.warning(f"HTML解析警告: {e}")
        self._tree = parser_impl.root

    def _parse_with_lxml(self) -> None:
        """使用lxml解析HTML。"""
        try:
            from lxml import html as lxml_html  # type: ignore
            self._lxml_tree = lxml_html.fromstring(self.html)
        except Exception:
            # 回退到标准库
            self._use_lxml = False
            self._parse_with_stdlib()

    # ========================================================
    # CSS选择器
    # ========================================================

    def css(self, selector: str) -> SelectorResult:
        """使用CSS选择器提取元素。

        Args:
            selector: CSS选择器字符串

        Returns:
            SelectorResult查询结果

        Raises:
            ParseError: 选择器语法错误时

        Examples:
            >>> parser.css("div.content > h1")
            >>> parser.css("a.external[href^='https']")
        """
        if self._use_lxml and self._lxml_tree is not None:
            return self._css_lxml(selector)
        return self._css_stdlib(selector)

    def _css_stdlib(self, selector: str) -> SelectorResult:
        """使用标准库实现CSS选择器。

        Args:
            selector: CSS选择器

        Returns:
            SelectorResult
        """
        if not self._tree:
            return SelectorResult([], self.base_url)

        try:
            selector_dict = _CSSSelectorParser.parse(selector)
            elements = self._tree.find_all(selector_dict)
            return SelectorResult(elements, self.base_url)
        except Exception as e:
            raise ParseError(f"CSS选择器解析失败: {e}", selector=selector)

    def _css_lxml(self, selector: str) -> SelectorResult:
        """使用lxml实现CSS选择器。

        Args:
            selector: CSS选择器

        Returns:
            SelectorResult
        """
        try:
            from lxml.cssselect import CSSSelector as LxmlCSSSelector  # type: ignore
            from lxml import html as lxml_html  # type: ignore

            if self._lxml_tree is None:
                return SelectorResult([], self.base_url)

            sel = LxmlCSSSelector(selector)
            lxml_elements = sel(self._lxml_tree)

            # 转换为HTMLElement
            elements: List[_HTMLElement] = []
            for el in lxml_elements:
                tag = el.tag if isinstance(el.tag, str) else str(el.tag)
                attrs = dict(el.attrib) if hasattr(el, "attrib") else {}
                html_el = _HTMLElement(tag=tag, attrs=attrs)
                html_el.text_parts = [
                    el.text_content() or ""
                ] if hasattr(el, "text_content") else []
                elements.append(html_el)

            return SelectorResult(elements, self.base_url)
        except ImportError:
            return self._css_stdlib(selector)
        except Exception as e:
            raise ParseError(f"CSS选择器解析失败: {e}", selector=selector)

    # ========================================================
    # XPath
    # ========================================================

    def xpath(self, expression: str) -> SelectorResult:
        """使用XPath表达式提取元素。

        Args:
            expression: XPath表达式

        Returns:
            SelectorResult查询结果

        Raises:
            ParseError: XPath语法错误时

        Examples:
            >>> parser.xpath("//div[@class='content']/p/text()")
            >>> parser.xpath("//a[contains(@href, 'article')]")
        """
        if self._use_lxml and self._lxml_tree is not None:
            return self._xpath_lxml(expression)
        return self._xpath_stdlib(expression)

    def _xpath_stdlib(self, expression: str) -> SelectorResult:
        """使用标准库xml.etree实现XPath。

        将HTML转换为XHTML格式后使用ElementTree的XPath支持。

        Args:
            expression: XPath表达式

        Returns:
            SelectorResult
        """
        try:
            # 将HTML转换为XHTML
            xhtml = self._html_to_xhtml(self.html)
            root = ET.fromstring(xhtml)

            elements: List[_HTMLElement] = []
            for el in root.findall(expression):
                tag = el.tag if isinstance(el.tag, str) else str(el.tag)
                attrs = dict(el.attrib) if hasattr(el, "attrib") else {}
                html_el = _HTMLElement(tag=tag, attrs=attrs)
                html_el.text_parts = [el.text or ""] if el.text else []
                elements.append(html_el)

            return SelectorResult(elements, self.base_url)
        except ET.ParseError as e:
            raise ParseError(f"XPath解析失败: {e}", selector=expression)
        except Exception as e:
            raise ParseError(f"XPath执行失败: {e}", selector=expression)

    def _xpath_lxml(self, expression: str) -> SelectorResult:
        """使用lxml实现XPath。

        Args:
            expression: XPath表达式

        Returns:
            SelectorResult
        """
        try:
            if self._lxml_tree is None:
                return SelectorResult([], self.base_url)

            results = self._lxml_tree.xpath(expression)

            elements: List[_HTMLElement] = []
            for item in results:
                if hasattr(item, "tag"):
                    tag = item.tag if isinstance(item.tag, str) else str(item.tag)
                    attrs = dict(item.attrib) if hasattr(item, "attrib") else {}
                    html_el = _HTMLElement(tag=tag, attrs=attrs)
                    html_el.text_parts = [
                        item.text_content() or ""
                    ] if hasattr(item, "text_content") else []
                    elements.append(html_el)
                elif isinstance(item, str):
                    # 文本节点
                    html_el = _HTMLElement(tag="__text__")
                    html_el.text_parts = [item]
                    elements.append(html_el)

            return SelectorResult(elements, self.base_url)
        except Exception as e:
            raise ParseError(f"XPath执行失败: {e}", selector=expression)

    @staticmethod
    def _html_to_xhtml(html_str: str) -> str:
        """将HTML转换为XHTML格式。

        简单的HTML到XHTML转换，处理常见的不规范HTML。

        Args:
            html_str: HTML字符串

        Returns:
            XHTML字符串
        """
        import re

        # 添加XML声明和根元素
        # 去除DOCTYPE
        xhtml = re.sub(r"<!DOCTYPE[^>]*>", "", html_str, flags=re.IGNORECASE)

        # 包裹在div中（ElementTree需要单一根元素）
        xhtml = f"<root>{xhtml}</root>"

        # 关闭自闭合标签
        void_tags = [
            "br", "hr", "img", "input", "link", "meta", "area",
            "base", "col", "embed", "param", "source", "track", "wbr",
        ]
        for tag in void_tags:
            xhtml = re.sub(
                rf"<{tag}([^>]*)>",
                rf"<{tag}\1/>",
                xhtml,
                flags=re.IGNORECASE,
            )

        # 移除注释
        xhtml = re.sub(r"<!--.*?-->", "", xhtml, flags=re.DOTALL)

        return xhtml

    # ========================================================
    # 文本提取
    # ========================================================

    @property
    def title(self) -> str:
        """获取页面标题。

        Returns:
            页面标题字符串
        """
        result = self.css("title")
        if result:
            return result.first.text if result.first else ""
        return ""

    @property
    def body_text(self) -> str:
        """获取页面主体文本（去除所有标签）。

        Returns:
            清洗后的页面文本
        """
        result = self.css("body")
        if result:
            return result.text
        return clean_text(self.html)

    def get_text(self, selector: Optional[str] = None) -> str:
        """获取指定选择器的文本内容。

        Args:
            selector: CSS选择器（可选，不指定则获取整个页面文本）

        Returns:
            文本内容
        """
        if selector:
            result = self.css(selector)
            return result.text
        return self.body_text

    # ========================================================
    # 链接提取
    # ========================================================

    @property
    def links(self) -> List[str]:
        """提取页面中所有链接。

        Returns:
            绝对URL列表
        """
        return self.css("a[href]").links(absolute=True)

    @property
    def internal_links(self) -> List[str]:
        """提取页面中的内部链接（同域名）。

        Returns:
            内部链接URL列表
        """
        if not self.url:
            return []
        domain = urlparse(self.url).netloc
        return [
            link for link in self.links
            if urlparse(link).netloc == domain
        ]

    @property
    def external_links(self) -> List[str]:
        """提取页面中的外部链接（不同域名）。

        Returns:
            外部链接URL列表
        """
        if not self.url:
            return self.links
        domain = urlparse(self.url).netloc
        return [
            link for link in self.links
            if urlparse(link).netloc != domain
        ]

    @property
    def unique_links(self) -> List[str]:
        """提取页面中去重后的所有链接。

        Returns:
            去重后的URL列表
        """
        seen: set = set()
        unique: List[str] = []
        for link in self.links:
            normalized = normalize_url(link)
            if normalized not in seen:
                seen.add(normalized)
                unique.append(link)
        return unique

    # ========================================================
    # 元数据提取
    # ========================================================

    @property
    def meta_description(self) -> str:
        """获取页面meta description。

        Returns:
            描述文本
        """
        result = self.css('meta[name="description"]')
        if result:
            content = result.first.attr("content") if result.first else []
            return content[0] if content else ""
        return ""

    @property
    def meta_keywords(self) -> str:
        """获取页面meta keywords。

        Returns:
            关键词字符串
        """
        result = self.css('meta[name="keywords"]')
        if result:
            content = result.first.attr("content") if result.first else []
            return content[0] if content else ""
        return ""

    @property
    def og_data(self) -> Dict[str, str]:
        """获取Open Graph元数据。

        Returns:
            OG数据字典
        """
        og: Dict[str, str] = {}
        result = self.css('meta[property^="og:"]')
        for el in result.elements:
            prop = el.get_attr("property")
            content = el.get_attr("content")
            if prop and content:
                # 去除og:前缀
                key = prop.replace("og:", "")
                og[key] = content
        return og

    @property
    def metadata(self) -> Dict[str, str]:
        """获取所有meta标签数据。

        Returns:
            元数据字典
        """
        meta: Dict[str, str] = {}
        result = self.css("meta")
        for el in result.elements:
            name = el.get_attr("name") or el.get_attr("property")
            content = el.get_attr("content")
            if name and content:
                meta[name] = content
        return meta

    # ========================================================
    # 结构化数据提取
    # ========================================================

    @property
    def json_ld(self) -> List[Dict[str, Any]]:
        """提取JSON-LD结构化数据。

        Returns:
            JSON-LD数据列表
        """
        results: List[Dict[str, Any]] = []
        scripts = self.css('script[type="application/ld+json"]')
        for el in scripts.elements:
            text = el.text.strip()
            if text:
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        results.extend(data)
                    else:
                        results.append(data)
                except json.JSONDecodeError:
                    continue
        return results

    def extract_table(
        self,
        selector: str = "table",
        headers: bool = True,
    ) -> List[Dict[str, str]]:
        """提取HTML表格为字典列表。

        Args:
            selector: 表格选择器
            headers: 是否使用第一行作为列名

        Returns:
            字典列表（每行一个字典）
        """
        tables = self.css(selector)
        if not tables:
            return []

        rows_data: List[Dict[str, str]] = []
        for table in tables.elements:
            # 提取表头
            header_cells: List[str] = []
            if headers:
                th_elements = table.find_all(
                    _CSSSelectorParser.parse("th")
                )
                header_cells = [el.inner_text for el in th_elements]

            # 提取数据行
            tr_elements = table.find_all(
                _CSSSelectorParser.parse("tr")
            )
            for tr in tr_elements:
                td_elements = tr.find_all(
                    _CSSSelectorParser.parse("td")
                )
                if not td_elements:
                    continue

                row_values = [el.inner_text for el in td_elements]

                if header_cells and len(header_cells) >= len(row_values):
                    row = dict(zip(header_cells[: len(row_values)], row_values))
                else:
                    row = {
                        f"col_{i}": val
                        for i, val in enumerate(row_values)
                    }
                rows_data.append(row)

        return rows_data

    def extract_list(self, selector: str = "li") -> List[str]:
        """提取列表内容。

        Args:
            selector: 列表项选择器

        Returns:
            列表项文本列表
        """
        items = self.css(selector)
        return items.texts

    # ========================================================
    # 辅助方法
    # ========================================================

    def get_html(self, selector: str) -> str:
        """获取匹配选择器的原始HTML。

        Args:
            selector: CSS选择器

        Returns:
            原始HTML字符串
        """
        return self.css(selector).raw_html

    def count(self, selector: str) -> int:
        """计算匹配选择器的元素数量。

        Args:
            selector: CSS选择器

        Returns:
            元素数量
        """
        return len(self.css(selector))

    def __repr__(self) -> str:
        backend = "lxml" if self._use_lxml else "stdlib"
        size = len(self.html)
        return f"<HTMLParser backend={backend} size={size}>"
