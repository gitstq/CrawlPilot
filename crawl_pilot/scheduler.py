"""
CrawlPilot - 爬取调度器模块

提供并发爬取调度、速率限制、断点续爬、URL去重和优先级队列等功能。

核心类：
    - CrawlTask: 爬取任务
    - CrawlStats: 爬取统计
    - CrawlScheduler: 爬取调度器
"""

import heapq
import json
import logging
import os
import signal
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlparse

from crawl_pilot.fetcher import FetchEngine, FetchResponse
from crawl_pilot.parser import HTMLParser
from crawl_pilot.antibot import AntiBotDetector, PolitenessPolicy, RobotParser
from crawl_pilot.storage import StorageBackend
from crawl_pilot.utils import (
    FetchError,
    SchedulerError,
    ProgressBar,
    hash_url,
    is_same_domain,
    is_valid_url,
    normalize_url,
    setup_logging,
)

logger = logging.getLogger("crawl_pilot.scheduler")


# ============================================================
# CrawlTask - 爬取任务
# ============================================================

@dataclass(order=True)
class CrawlTask:
    """爬取任务。

    Attributes:
        priority: 优先级（数值越小优先级越高）
        url: 目标URL
        depth: 爬取深度
        parent_url: 来源URL
        retry_count: 已重试次数
        metadata: 附加元数据
    """

    priority: int = 0
    url: str = field(default="", compare=False)
    depth: int = field(default=0, compare=False)
    parent_url: Optional[str] = field(default=None, compare=False)
    retry_count: int = field(default=0, compare=False)
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        """初始化后处理。"""
        self.url = normalize_url(self.url)

    def __repr__(self) -> str:
        return f"<CrawlTask url={self.url} depth={self.depth} priority={self.priority}>"


# ============================================================
# CrawlStats - 爬取统计
# ============================================================

@dataclass
class CrawlStats:
    """爬取统计信息。

    Attributes:
        total: 总任务数
        success: 成功数
        failed: 失败数
        skipped: 跳过数
        start_time: 开始时间
        urls_per_second: 每秒URL数
    """

    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def elapsed(self) -> float:
        """获取已用时间（秒）。"""
        return time.time() - self.start_time

    @property
    def urls_per_second(self) -> float:
        """获取每秒处理URL数。"""
        elapsed = self.elapsed
        if elapsed > 0:
            return (self.success + self.failed) / elapsed
        return 0.0

    @property
    def success_rate(self) -> float:
        """获取成功率。"""
        total_processed = self.success + self.failed
        if total_processed > 0:
            return self.success / total_processed * 100
        return 0.0

    def increment_success(self) -> None:
        """增加成功计数。"""
        with self._lock:
            self.success += 1

    def increment_failed(self) -> None:
        """增加失败计数。"""
        with self._lock:
            self.failed += 1

    def increment_skipped(self) -> None:
        """增加跳过计数。"""
        with self._lock:
            self.skipped += 1

    def __repr__(self) -> str:
        return (
            f"<CrawlStats total={self.total} success={self.success} "
            f"failed={self.failed} skipped={self.skipped} "
            f"rate={self.success_rate:.1f}%>"
        )


# ============================================================
# CrawlScheduler - 爬取调度器
# ============================================================

class CrawlScheduler:
    """爬取调度器。

    提供并发爬取调度功能，包括：
    - 并发控制（Semaphore限制并发数）
    - 速率限制（每秒请求数限制）
    - 域名级别速率限制
    - 断点续爬（记录已爬取URL，支持中断恢复）
    - URL去重（内存+可选文件持久化）
    - 优先级队列
    - 爬取统计
    - 优雅关闭（信号处理，保存进度）

    Attributes:
        max_concurrency: 最大并发数
        rate_limit: 每秒最大请求数
        max_depth: 最大爬取深度
        stats: 爬取统计

    Examples:
        >>> scheduler = CrawlScheduler(
        ...     max_concurrency=5,
        ...     rate_limit=2,
        ...     max_depth=3,
        ... )
        >>> scheduler.add_url("https://example.com")
        >>> scheduler.run(callback=my_callback)
    """

    def __init__(
        self,
        max_concurrency: int = 5,
        rate_limit: float = 2.0,
        max_depth: int = 10,
        respect_robots: bool = True,
        same_domain_only: bool = True,
        checkpoint_file: Optional[str] = None,
        storage: Optional[StorageBackend] = None,
        fetcher: Optional[FetchEngine] = None,
        on_page: Optional[Callable[[FetchResponse, HTMLParser], Optional[List[str]]]] = None,
    ) -> None:
        """初始化爬取调度器。

        Args:
            max_concurrency: 最大并发数
            rate_limit: 每秒最大请求数
            max_depth: 最大爬取深度
            respect_robots: 是否遵守robots.txt
            same_domain_only: 是否只爬取同域名URL
            checkpoint_file: 断点续爬文件路径
            storage: 存储后端
            fetcher: 自定义请求引擎
            on_page: 页面处理回调函数
        """
        self.max_concurrency = max_concurrency
        self.rate_limit = rate_limit
        self.max_depth = max_depth
        self.respect_robots = respect_robots
        self.same_domain_only = same_domain_only
        self.checkpoint_file = checkpoint_file

        # 组件
        self._fetcher = fetcher or FetchEngine()
        self._antibot = AntiBotDetector(adaptive=True)
        self._politeness = PolitenessPolicy(default_delay=1.0 / max(rate_limit, 0.1))
        self._robot_parser = RobotParser() if respect_robots else None
        self._storage = storage

        # 回调
        self._on_page = on_page

        # 状态
        self._task_queue: List[CrawlTask] = []
        self._seen_urls: Set[str] = set()
        self._stats = CrawlStats()
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_concurrency)
        self._running = False
        self._stop_event = threading.Event()
        self._rate_limit_lock = threading.Lock()
        self._last_request_time: float = 0.0
        self._base_domain: Optional[str] = None

        # 加载断点
        if checkpoint_file and os.path.exists(checkpoint_file):
            self._load_checkpoint()

        # 注册信号处理
        self._register_signal_handlers()

    def add_url(
        self,
        url: str,
        priority: int = 0,
        depth: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """添加URL到爬取队列。

        Args:
            url: 目标URL
            priority: 优先级（数值越小优先级越高）
            depth: 爬取深度
            metadata: 附加元数据
        """
        if not is_valid_url(url):
            logger.warning(f"无效URL，已跳过: {url}")
            return

        normalized = normalize_url(url)

        # URL去重
        url_hash = hash_url(normalized)
        if url_hash in self._seen_urls:
            return

        self._seen_urls.add(url_hash)

        # 设置基础域名
        if self._base_domain is None:
            self._base_domain = get_domain(url)

        task = CrawlTask(
            priority=priority,
            url=normalized,
            depth=depth,
            metadata=metadata or {},
        )
        heapq.heappush(self._task_queue, task)
        self._stats.total += 1

    def add_urls(self, urls: List[str], priority: int = 0) -> None:
        """批量添加URL。

        Args:
            urls: URL列表
            priority: 优先级
        """
        for url in urls:
            self.add_url(url, priority=priority)

    def run(
        self,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> CrawlStats:
        """运行爬取调度器。

        Args:
            callback: 数据处理回调函数

        Returns:
            爬取统计信息
        """
        self._running = True
        self._stats.start_time = time.time()
        self._stop_event.clear()

        # 创建工作线程
        threads: List[threading.Thread] = []
        num_workers = min(self.max_concurrency, max(len(self._task_queue), 1))

        logger.info(
            f"开始爬取: {self._stats.total} 个URL, "
            f"并发={self.max_concurrency}, 速率限制={self.rate_limit}/s"
        )

        # 进度条
        progress = ProgressBar(
            total=self._stats.total,
            prefix="Crawling",
        )

        def worker() -> None:
            """工作线程函数。"""
            while not self._stop_event.is_set():
                task = self._get_next_task()
                if task is None:
                    break

                try:
                    self._semaphore.acquire()
                    self._rate_limit_wait()

                    # 礼貌策略
                    domain = get_domain(task.url)
                    self._politeness.wait(domain)
                    self._politeness.enter_domain(domain)

                    # 爬取页面
                    result = self._crawl_page(task, callback)

                    if result:
                        self._stats.increment_success()
                    else:
                        self._stats.increment_failed()

                except Exception as e:
                    logger.error(f"爬取异常: {task.url} - {e}")
                    self._stats.increment_failed()
                finally:
                    self._politeness.leave_domain(domain)
                    self._semaphore.release()

                    # 更新进度
                    progress.update(
                        self._stats.success + self._stats.failed + self._stats.skipped
                    )

        # 启动工作线程
        for i in range(num_workers):
            t = threading.Thread(target=worker, name=f"worker-{i}", daemon=True)
            threads.append(t)
            t.start()

        # 等待完成
        for t in threads:
            t.join()

        progress.finish()

        # 保存断点
        if self.checkpoint_file:
            self._save_checkpoint()

        self._running = False

        logger.info(
            f"爬取完成: {self._stats.success} 成功, "
            f"{self._stats.failed} 失败, {self._stats.skipped} 跳过, "
            f"耗时 {self._stats.elapsed:.1f}s, "
            f"速率 {self._stats.urls_per_second:.1f} URL/s"
        )

        return self._stats

    def stop(self) -> None:
        """停止爬取。"""
        logger.info("正在停止爬取...")
        self._stop_event.set()
        self._running = False
        if self.checkpoint_file:
            self._save_checkpoint()

    def _get_next_task(self) -> Optional[CrawlTask]:
        """从队列中获取下一个任务。

        Returns:
            CrawlTask或None（队列为空）
        """
        with self._lock:
            if self._task_queue:
                return heapq.heappop(self._task_queue)
            return None

    def _rate_limit_wait(self) -> None:
        """速率限制等待。"""
        if self.rate_limit <= 0:
            return

        min_interval = 1.0 / self.rate_limit
        with self._rate_limit_lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                time.sleep(wait_time)
            self._last_request_time = time.time()

    def _crawl_page(
        self,
        task: CrawlTask,
        callback: Optional[Callable[[Dict[str, Any]], None]],
    ) -> bool:
        """爬取单个页面。

        Args:
            task: 爬取任务
            callback: 数据处理回调

        Returns:
            成功返回True
        """
        url = task.url
        domain = get_domain(url)

        # 检查robots.txt
        if self._robot_parser and self.respect_robots:
            if not self._robot_parser.can_fetch(url):
                logger.debug(f"robots.txt 禁止: {url}")
                self._stats.increment_skipped()
                return True

        # 发送请求
        try:
            response = self._fetcher.get(url)
        except FetchError as e:
            logger.error(f"请求失败: {url} - {e}")
            return False

        # 反爬检测
        detection = self._antibot.detect(response)
        if detection.detected:
            if detection.recommended_action == "skip_page":
                logger.warning(f"跳过页面（反爬检测）: {url}")
                self._stats.increment_skipped()
                self._antibot._update_domain_stats(domain, "detected")
                self._politeness.adapt_from_detection(domain, detection.bot_type)
                return True
            elif detection.recommended_action == "slow_down":
                self._politeness.adapt_from_detection(domain, detection.bot_type)
                self._antibot._update_domain_stats(domain, "detected")
                # 继续尝试
            else:
                self._antibot._update_domain_stats(domain, "detected")

        # 记录访问
        self._politeness.record_access(domain)

        # 解析页面
        try:
            parser = HTMLParser(response.text, url=response.url)
        except Exception as e:
            logger.error(f"解析失败: {url} - {e}")
            return False

        # 调用页面处理回调
        new_urls: Optional[List[str]] = None
        if self._on_page:
            try:
                new_urls = self._on_page(response, parser)
            except Exception as e:
                logger.error(f"页面处理回调异常: {url} - {e}")

        # 提取新URL
        if new_urls is None:
            new_urls = parser.unique_links

        # 添加新URL到队列
        if task.depth < self.max_depth:
            for new_url in new_urls:
                if not is_valid_url(new_url):
                    continue

                # 同域名限制
                if self.same_domain_only and self._base_domain:
                    if not is_same_domain(new_url, self._base_domain):
                        continue

                # 深度优先级（越深优先级越低）
                new_priority = task.depth + 1
                self.add_url(
                    new_url,
                    priority=new_priority,
                    depth=task.depth + 1,
                )

        # 调用数据回调
        if callback:
            try:
                data = {
                    "url": response.url,
                    "status_code": response.status_code,
                    "title": parser.title,
                    "depth": task.depth,
                    "metadata": task.metadata,
                }
                callback(data)
            except Exception as e:
                logger.error(f"数据回调异常: {url} - {e}")

        # 存储到后端
        if self._storage:
            try:
                self._storage.save({
                    "url": response.url,
                    "title": parser.title,
                    "status_code": response.status_code,
                    "depth": task.depth,
                    "content_length": response.content_length,
                })
            except Exception as e:
                logger.error(f"存储异常: {url} - {e}")

        return True

    def _save_checkpoint(self) -> None:
        """保存断点信息。"""
        if not self.checkpoint_file:
            return

        try:
            checkpoint_dir = os.path.dirname(self.checkpoint_file)
            if checkpoint_dir:
                os.makedirs(checkpoint_dir, exist_ok=True)

            data = {
                "seen_urls": list(self._seen_urls),
                "stats": {
                    "total": self._stats.total,
                    "success": self._stats.success,
                    "failed": self._stats.failed,
                    "skipped": self._stats.skipped,
                },
                "base_domain": self._base_domain,
            }

            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"断点已保存: {self.checkpoint_file}")
        except Exception as e:
            logger.error(f"保存断点失败: {e}")

    def _load_checkpoint(self) -> None:
        """加载断点信息。"""
        if not self.checkpoint_file or not os.path.exists(self.checkpoint_file):
            return

        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._seen_urls = set(data.get("seen_urls", []))
            self._base_domain = data.get("base_domain")

            stats_data = data.get("stats", {})
            self._stats.total = stats_data.get("total", 0)
            self._stats.success = stats_data.get("success", 0)
            self._stats.failed = stats_data.get("failed", 0)
            self._stats.skipped = stats_data.get("skipped", 0)

            logger.info(
                f"已加载断点: {len(self._seen_urls)} 个已爬URL, "
                f"基础域名: {self._base_domain}"
            )
        except Exception as e:
            logger.error(f"加载断点失败: {e}")

    def _register_signal_handlers(self) -> None:
        """注册信号处理函数（优雅关闭）。"""
        def signal_handler(signum: int, frame: Any) -> None:
            """信号处理函数。"""
            logger.info(f"收到信号 {signum}，正在优雅关闭...")
            self.stop()

        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except (ValueError, RuntimeError):
            # 非主线程无法注册信号处理
            pass

    @property
    def stats(self) -> CrawlStats:
        """获取爬取统计。"""
        return self._stats

    @property
    def pending_count(self) -> int:
        """获取待处理任务数。"""
        return len(self._task_queue)

    @property
    def is_running(self) -> bool:
        """是否正在运行。"""
        return self._running

    def close(self) -> None:
        """关闭调度器，清理资源。"""
        self.stop()
        self._fetcher.close()
        if self._robot_parser:
            self._robot_parser.close()

    def __enter__(self) -> "CrawlScheduler":
        """支持上下文管理器。"""
        return self

    def __exit__(self, *args: object) -> None:
        """退出上下文时自动关闭。"""
        self.close()

    def __repr__(self) -> str:
        return (
            f"<CrawlScheduler concurrency={self.max_concurrency} "
            f"rate={self.rate_limit}/s pending={self.pending_count}>"
        )


# ============================================================
# 辅助函数
# ============================================================

def get_domain(url: str) -> str:
    """从URL中提取域名。"""
    parsed = urlparse(url)
    return parsed.netloc.lower()
