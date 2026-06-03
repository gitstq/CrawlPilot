"""
CrawlPilot - 智能自适应Web爬虫引擎

一个纯Python实现的智能Web爬虫框架，支持反爬检测、自适应策略、
数据提取管道、并发调度和多种存储后端。

核心特性：
    - 零强制依赖（纯标准库实现核心功能）
    - 智能反爬检测与自适应策略切换
    - 链式数据提取管道
    - 并发爬取调度与速率限制
    - 多种存储后端（JSON/CSV/SQLite）
    - 断点续爬支持

使用示例：
    >>> from crawl_pilot import FetchEngine, HTMLParser, Pipeline
    >>> fetcher = FetchEngine()
    >>> response = fetcher.get("https://example.com")
    >>> parser = HTMLParser(response.text)
    >>> parser.css("h1").text
    >>> pipeline = Pipeline()
    >>> pipeline.extract(css="h1").clean().output()

版本: 0.1.0
作者: CrawlPilot Team
协议: MIT
"""

__version__ = "0.1.0"
__author__ = "CrawlPilot Team"
__license__ = "MIT"

from crawl_pilot.fetcher import FetchEngine
from crawl_pilot.parser import HTMLParser
from crawl_pilot.pipeline import Pipeline, DataExtractor, DataCleaner, DataTransformer
from crawl_pilot.scheduler import CrawlScheduler
from crawl_pilot.storage import JSONStorage, CSVStorage, SQLiteStorage
from crawl_pilot.antibot import AntiBotDetector, RobotParser, PolitenessPolicy

__all__ = [
    "FetchEngine",
    "HTMLParser",
    "Pipeline",
    "DataExtractor",
    "DataCleaner",
    "DataTransformer",
    "CrawlScheduler",
    "JSONStorage",
    "CSVStorage",
    "SQLiteStorage",
    "AntiBotDetector",
    "RobotParser",
    "PolitenessPolicy",
]
