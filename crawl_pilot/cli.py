"""
CrawlPilot - 命令行入口模块

提供命令行接口，支持单URL爬取、整站爬取和本地HTML解析。

命令：
    - crawl: 单URL爬取
    - crawl-site: 整站爬取
    - parse: 解析本地HTML文件
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Optional

from crawl_pilot import __version__
from crawl_pilot.fetcher import FetchEngine
from crawl_pilot.parser import HTMLParser
from crawl_pilot.pipeline import Pipeline
from crawl_pilot.scheduler import CrawlScheduler
from crawl_pilot.storage import JSONStorage, CSVStorage, SQLiteStorage
from crawl_pilot.antibot import AntiBotDetector
from crawl_pilot.utils import (
    ProgressBar,
    format_size,
    is_valid_url,
    setup_logging,
)

logger = logging.getLogger("crawl_pilot.cli")


# ============================================================
# 命令处理函数
# ============================================================

def cmd_crawl(args: argparse.Namespace) -> None:
    """执行单URL爬取命令。

    Args:
        args: 命令行参数
    """
    # 配置日志
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level)

    url = args.url
    if not is_valid_url(url):
        logger.error(f"无效的URL: {url}")
        sys.exit(1)

    logger.info(f"开始爬取: {url}")

    # 创建请求引擎
    fetcher = FetchEngine(
        timeout=args.timeout,
        max_retries=args.retries,
        proxy=args.proxy,
    )

    # 添加自定义请求头
    if args.header:
        for header_str in args.header:
            if "=" in header_str:
                key, value = header_str.split("=", 1)
                fetcher.headers[key.strip()] = value.strip()

    # 发送请求
    try:
        response = fetcher.get(url)
    except Exception as e:
        logger.error(f"请求失败: {e}")
        sys.exit(1)

    logger.info(
        f"响应: {response.status_code} | 大小: {response.size} | "
        f"耗时: {response.elapsed:.2f}s"
    )

    # 反爬检测
    detector = AntiBotDetector()
    detection = detector.detect(response)
    if detection.detected:
        logger.warning(
            f"检测到反爬机制: {detection.bot_type} "
            f"(置信度: {detection.confidence:.2f})"
        )
        for evidence in detection.evidence:
            logger.warning(f"  证据: {evidence}")

    # 解析HTML
    parser = HTMLParser(response.text, url=response.url)

    # 显示基本信息
    if args.verbose:
        logger.info(f"标题: {parser.title}")
        logger.info(f"描述: {parser.meta_description}")
        logger.info(f"链接数: {len(parser.unique_links)}")
        logger.info(f"内部链接: {len(parser.internal_links)}")
        logger.info(f"外部链接: {len(parser.external_links)}")

    # 使用选择器提取数据
    results: List[Dict[str, str]] = []
    if args.selector:
        selector_results = parser.css(args.selector)
        for i, item in enumerate(selector_results.elements):
            result = {
                "index": str(i),
                "text": item.inner_text,
                "raw_html": str(item.attrs),
            }
            results.append(result)
        logger.info(f"选择器 '{args.selector}' 匹配 {len(results)} 个元素")

    # 如果没有选择器，提取所有链接
    if not args.selector:
        for link in parser.unique_links:
            results.append({"url": link})

    # 输出结果
    _output_results(results, args)


def cmd_crawl_site(args: argparse.Namespace) -> None:
    """执行整站爬取命令。

    Args:
        args: 命令行参数
    """
    # 配置日志
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level)

    url = args.url
    if not is_valid_url(url):
        logger.error(f"无效的URL: {url}")
        sys.exit(1)

    logger.info(f"开始整站爬取: {url}")

    # 创建存储后端
    storage = _create_storage(args)

    # 创建调度器
    scheduler = CrawlScheduler(
        max_concurrency=args.concurrency,
        rate_limit=1.0 / max(args.delay, 0.1),
        max_depth=args.depth,
        respect_robots=args.respect_robots,
        same_domain_only=True,
        checkpoint_file=os.path.join(args.output_dir, ".checkpoint.json") if args.output_dir else None,
        storage=storage,
    )

    # 添加起始URL
    scheduler.add_url(url)

    # 运行爬取
    try:
        stats = scheduler.run()
        logger.info(f"爬取统计: {stats}")
    except KeyboardInterrupt:
        logger.info("用户中断爬取")
        scheduler.stop()
    finally:
        scheduler.close()
        if storage:
            storage.close()


def cmd_parse(args: argparse.Namespace) -> None:
    """执行本地HTML解析命令。

    Args:
        args: 命令行参数
    """
    # 配置日志
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level)

    filepath = args.file
    if not os.path.exists(filepath):
        logger.error(f"文件不存在: {filepath}")
        sys.exit(1)

    # 读取文件
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            html_content = f.read()
    except Exception as e:
        logger.error(f"文件读取失败: {e}")
        sys.exit(1)

    logger.info(f"已读取文件: {filepath} ({format_size(len(html_content))})")

    # 解析HTML
    parser = HTMLParser(html_content)

    # 显示基本信息
    logger.info(f"标题: {parser.title}")
    logger.info(f"描述: {parser.meta_description}")
    logger.info(f"链接数: {len(parser.unique_links)}")

    # 使用选择器提取数据
    results: List[Dict[str, str]] = []
    if args.selector:
        selector_results = parser.css(args.selector)
        for i, item in enumerate(selector_results.elements):
            result = {
                "index": str(i),
                "text": item.inner_text,
                "tag": item.tag,
                "attrs": item.attrs,
            }
            results.append(result)
        logger.info(f"选择器 '{args.selector}' 匹配 {len(results)} 个元素")
    else:
        # 提取所有信息
        results = [{
            "title": parser.title,
            "description": parser.meta_description,
            "keywords": parser.meta_keywords,
            "links_count": str(len(parser.unique_links)),
            "og_data": json.dumps(parser.og_data, ensure_ascii=False),
        }]

        # 提取表格数据
        tables = parser.extract_table()
        if tables:
            results.extend(tables)

    # 输出结果
    _output_results(results, args)


# ============================================================
# 辅助函数
# ============================================================

def _create_storage(args: argparse.Namespace) -> Optional[object]:
    """根据参数创建存储后端。

    Args:
        args: 命令行参数

    Returns:
        存储后端实例或None
    """
    output_format = args.output or "json"
    output_dir = args.output_dir or "./output"

    if output_format == "json":
        return JSONStorage(output_dir=output_dir, filename="results.json")
    elif output_format == "csv":
        return CSVStorage(output_dir=output_dir, filename="results.csv")
    elif output_format == "sqlite":
        return SQLiteStorage(output_dir=output_dir, filename="results.db")
    else:
        logger.warning(f"不支持的输出格式: {output_format}，使用JSON")
        return JSONStorage(output_dir=output_dir, filename="results.json")


def _output_results(
    results: List[Dict[str, str]],
    args: argparse.Namespace,
) -> None:
    """输出结果到终端或文件。

    Args:
        results: 结果列表
        args: 命令行参数
    """
    output_format = args.output or "json"

    if output_format == "json":
        output = json.dumps(results, ensure_ascii=False, indent=2)
    elif output_format == "csv":
        import csv
        import io
        if not results:
            output = ""
        else:
            output_buf = io.StringIO()
            writer = csv.DictWriter(output_buf, fieldnames=results[0].keys())
            writer.writeheader()
            for row in results:
                writer.writerow(row)
            output = output_buf.getvalue()
    else:
        # 默认文本输出
        lines: List[str] = []
        for item in results:
            for key, value in item.items():
                if key == "attrs":
                    continue
                lines.append(f"{key}: {value}")
            lines.append("---")
        output = "\n".join(lines)

    # 输出到文件或终端
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        ext = "json" if output_format == "json" else "csv" if output_format == "csv" else "txt"
        filepath = os.path.join(args.output_dir, f"results.{ext}")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(output)
        logger.info(f"结果已保存: {filepath}")
    else:
        print(output)


# ============================================================
# CLI入口
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。

    Returns:
        ArgumentParser实例
    """
    parser = argparse.ArgumentParser(
        prog="crawl-pilot",
        description="CrawlPilot - 智能自适应Web爬虫引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 爬取单个页面
  crawl-pilot crawl https://example.com

  # 使用CSS选择器提取数据
  crawl-pilot crawl https://example.com --selector "h1.title"

  # 整站爬取
  crawl-pilot crawl-site https://example.com --depth 2 --output json

  # 解析本地HTML文件
  crawl-pilot parse page.html --selector "div.content"

  # 使用代理和自定义请求头
  crawl-pilot crawl https://example.com --proxy http://127.0.0.1:7890 --header "Accept-Language=en-US"
        """,
    )

    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"CrawlPilot v{__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="可用命令",
    )

    # crawl 命令
    crawl_parser = subparsers.add_parser(
        "crawl",
        help="爬取单个URL",
        description="爬取单个URL并提取数据",
    )
    crawl_parser.add_argument("url", help="目标URL")
    crawl_parser.add_argument(
        "-o", "--output",
        choices=["json", "csv", "sqlite"],
        default=None,
        help="输出格式（默认输出到终端）",
    )
    crawl_parser.add_argument(
        "--selector",
        "-s",
        default=None,
        help="CSS选择器（提取特定元素）",
    )
    crawl_parser.add_argument(
        "--proxy",
        default=None,
        help="代理地址（http://host:port 或 socks5://host:port）",
    )
    crawl_parser.add_argument(
        "--header",
        action="append",
        default=None,
        help="自定义请求头（格式：Key=Value，可多次使用）",
    )
    crawl_parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="请求超时时间（秒），默认30",
    )
    crawl_parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="最大重试次数，默认3",
    )
    crawl_parser.add_argument(
        "--output-dir",
        default=None,
        help="输出目录",
    )
    crawl_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="详细输出",
    )

    # crawl-site 命令
    site_parser = subparsers.add_parser(
        "crawl-site",
        help="整站爬取",
        description="爬取整个网站（同域名下的所有页面）",
    )
    site_parser.add_argument("url", help="起始URL")
    site_parser.add_argument(
        "-o", "--output",
        choices=["json", "csv", "sqlite"],
        default="json",
        help="输出格式，默认json",
    )
    site_parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="最大爬取深度，默认3",
    )
    site_parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="并发数，默认5",
    )
    site_parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="请求延迟（秒），默认0.5",
    )
    site_parser.add_argument(
        "--respect-robots",
        action="store_true",
        default=False,
        help="遵守robots.txt",
    )
    site_parser.add_argument(
        "--output-dir",
        default="./output",
        help="输出目录，默认./output",
    )
    site_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="详细输出",
    )

    # parse 命令
    parse_parser = subparsers.add_parser(
        "parse",
        help="解析本地HTML文件",
        description="解析本地HTML文件并提取数据",
    )
    parse_parser.add_argument("file", help="HTML文件路径")
    parse_parser.add_argument(
        "-o", "--output",
        choices=["json", "csv"],
        default=None,
        help="输出格式（默认输出到终端）",
    )
    parse_parser.add_argument(
        "--selector",
        "-s",
        default=None,
        help="CSS选择器",
    )
    parse_parser.add_argument(
        "--output-dir",
        default=None,
        help="输出目录",
    )
    parse_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="详细输出",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """CLI主入口函数。

    Args:
        argv: 命令行参数列表（可选，默认使用sys.argv）
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "crawl":
        cmd_crawl(args)
    elif args.command == "crawl-site":
        cmd_crawl_site(args)
    elif args.command == "parse":
        cmd_parse(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
