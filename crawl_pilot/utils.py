"""
CrawlPilot - 工具函数模块

提供URL处理、编码检测、日志配置、进度条显示等通用工具函数。

模块内容：
    - normalize_url: URL规范化处理
    - join_url: URL拼接
    - get_domain: 提取域名
    - detect_encoding: 编码检测
    - setup_logging: 日志配置
    - format_size: 文件大小格式化
    - hash_url: URL哈希计算
    - ProgressBar: 文本进度条
    - CrawlPilotError: 基础异常类
    - FetchError: 请求异常
    - ParseError: 解析异常
    - StorageError: 存储异常
    - SchedulerError: 调度异常
"""

import hashlib
import html
import logging
import os
import re
import sys
import time
from typing import Optional
from urllib.parse import (
    parse_qs,
    quote,
    unquote,
    urljoin,
    urlparse,
    urlunparse,
)


# ============================================================
# 自定义异常类
# ============================================================

class CrawlPilotError(Exception):
    """CrawlPilot基础异常类。

    所有CrawlPilot自定义异常的基类。

    Attributes:
        message: 错误描述信息
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[CrawlPilotError] {self.message}"


class FetchError(CrawlPilotError):
    """HTTP请求异常。

    当HTTP请求失败时抛出，包括网络错误、超时、状态码异常等。

    Attributes:
        message: 错误描述信息
        status_code: HTTP状态码（可选）
        url: 请求的URL（可选）
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
    ) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(message)

    def __str__(self) -> str:
        parts = [f"[FetchError] {self.message}"]
        if self.status_code:
            parts.append(f"status_code={self.status_code}")
        if self.url:
            parts.append(f"url={self.url}")
        return " | ".join(parts)


class ParseError(CrawlPilotError):
    """HTML解析异常。

    当HTML解析过程中出现错误时抛出。

    Attributes:
        message: 错误描述信息
        selector: 导致错误的CSS选择器或XPath表达式（可选）
    """

    def __init__(
        self,
        message: str,
        selector: Optional[str] = None,
    ) -> None:
        self.selector = selector
        super().__init__(message)

    def __str__(self) -> str:
        parts = [f"[ParseError] {self.message}"]
        if self.selector:
            parts.append(f"selector={self.selector}")
        return " | ".join(parts)


class StorageError(CrawlPilotError):
    """存储异常。

    当数据存储过程中出现错误时抛出。

    Attributes:
        message: 错误描述信息
        path: 存储路径（可选）
    """

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
    ) -> None:
        self.path = path
        super().__init__(message)

    def __str__(self) -> str:
        parts = [f"[StorageError] {self.message}"]
        if self.path:
            parts.append(f"path={self.path}")
        return " | ".join(parts)


class SchedulerError(CrawlPilotError):
    """调度异常。

    当爬取调度过程中出现错误时抛出。

    Attributes:
        message: 错误描述信息
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)

    def __str__(self) -> str:
        return f"[SchedulerError] {self.message}"


# ============================================================
# URL处理工具
# ============================================================

def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """规范化URL。

    对URL进行规范化处理，包括：
    - 如果提供了base_url，将相对URL转换为绝对URL
    - 去除URL中的片段标识符（#部分）
    - 统一为小写scheme和netloc
    - 去除末尾斜杠（路径部分）
    - 排序查询参数

    Args:
        url: 待规范化的URL
        base_url: 基础URL，用于将相对URL转换为绝对URL

    Returns:
        规范化后的URL字符串

    Examples:
        >>> normalize_url("/path", "https://example.com")
        'https://example.com/path'
        >>> normalize_url("HTTPS://Example.COM/path#frag")
        'https://example.com/path'
    """
    if base_url:
        url = urljoin(base_url, url)

    parsed = urlparse(url)

    # 规范化scheme和netloc为小写
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # 去除末尾斜杠（除非是根路径）
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # 去除片段标识符
    fragment = ""

    # 排序查询参数
    if parsed.query:
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        sorted_params = sorted(query_params.items())
        query_parts = []
        for key, values in sorted_params:
            for value in values:
                query_parts.append(f"{quote(key)}={quote(value)}")
        query = "&".join(query_parts)
    else:
        query = ""

    return urlunparse((scheme, netloc, path, parsed.params, query, fragment))


def join_url(base: str, relative: str) -> str:
    """拼接基础URL和相对URL。

    Args:
        base: 基础URL
        relative: 相对URL或路径

    Returns:
        拼接后的完整URL

    Examples:
        >>> join_url("https://example.com", "/page")
        'https://example.com/page'
    """
    return urljoin(base, relative)


def get_domain(url: str) -> str:
    """从URL中提取域名。

    Args:
        url: URL字符串

    Returns:
        域名字符串（小写）

    Examples:
        >>> get_domain("https://www.example.com/path")
        'www.example.com'
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()


def is_same_domain(url1: str, url2: str) -> bool:
    """判断两个URL是否属于同一域名。

    Args:
        url1: 第一个URL
        url2: 第二个URL

    Returns:
        如果两个URL的域名相同则返回True
    """
    return get_domain(url1) == get_domain(url2)


def is_valid_url(url: str) -> bool:
    """检查URL是否有效。

    Args:
        url: 待检查的URL

    Returns:
        如果URL格式有效则返回True
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


# ============================================================
# 编码检测
# ============================================================

def detect_encoding(data: bytes) -> str:
    """检测字节数据的编码。

    优先从HTML meta标签中检测编码，然后尝试标准库方法。
    如果安装了chardet则使用chardet作为后备方案。

    Args:
        data: 待检测编码的字节数据

    Returns:
        检测到的编码名称，默认为"utf-8"
    """
    # 尝试从HTML meta标签中检测
    if b"<meta" in data.lower():
        # 匹配 <meta charset="xxx"> 或 <meta http-equiv="Content-Type" content="text/html; charset=xxx">
        charset_pattern = rb'charset=["\']?([a-zA-Z0-9_-]+)["\']?'
        # 只检查前1024字节（meta标签通常在head中）
        head = data[:4096]
        matches = re.findall(charset_pattern, head, re.IGNORECASE)
        if matches:
            charset = matches[0].decode("ascii", errors="ignore").strip()
            if charset:
                return charset.lower()

    # 尝试使用chardet（可选依赖）
    try:
        import chardet  # type: ignore
        result = chardet.detect(data)
        if result and result.get("encoding"):
            return result["encoding"].lower()
    except ImportError:
        pass

    return "utf-8"


# ============================================================
# 文本处理工具
# ============================================================

def clean_text(text: str) -> str:
    """清洗文本内容。

    - 去除HTML标签
    - 解码HTML实体
    - 规范化空白字符
    - 去除首尾空白

    Args:
        text: 待清洗的文本

    Returns:
        清洗后的文本
    """
    if not text:
        return ""
    # 解码HTML实体
    text = html.unescape(text)
    # 去除HTML标签
    text = re.sub(r"<[^>]+>", "", text)
    # 规范化空白字符（多个空白合并为一个空格）
    text = re.sub(r"[\t\r\n\f]+", " ", text)
    # 去除多余空格
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def extract_numbers(text: str) -> list:
    """从文本中提取所有数字。

    Args:
        text: 待提取的文本

    Returns:
        包含所有数字的列表（字符串形式）
    """
    return re.findall(r"-?\d+\.?\d*", text)


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """截断文本到指定长度。

    Args:
        text: 待截断的文本
        max_length: 最大长度
        suffix: 截断后添加的后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


# ============================================================
# 日志配置
# ============================================================

class ColorFormatter(logging.Formatter):
    """彩色日志格式化器。

    为不同日志级别添加ANSI颜色代码，使终端输出更加清晰。
    """

    # ANSI颜色代码
    COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",    # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[35m",   # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录。

        Args:
            record: 日志记录对象

        Returns:
            带颜色的格式化日志字符串
        """
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    color: bool = True,
) -> logging.Logger:
    """配置日志系统。

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        log_file: 日志文件路径（可选，不指定则仅输出到终端）
        color: 是否启用彩色输出（默认True）

    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger("crawl_pilot")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除已有处理器
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 终端处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    if color and sys.stdout.isatty():
        console_handler.setFormatter(ColorFormatter(fmt=formatter._fmt, datefmt=formatter.datefmt))
    else:
        console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# ============================================================
# 进度条
# ============================================================

class ProgressBar:
    """文本进度条。

    在终端中显示简洁的文本进度条，用于展示爬取进度。

    Attributes:
        total: 总任务数
        current: 当前已完成数
        width: 进度条宽度（字符数）
        prefix: 进度条前缀文字

    Examples:
        >>> bar = ProgressBar(total=100, prefix="Crawling")
        >>> bar.update(50)
        Crawling: [████████████████████░░░░░░░░░░░░] 50/100 (50.0%)
    """

    def __init__(
        self,
        total: int,
        width: int = 40,
        prefix: str = "Progress",
    ) -> None:
        """初始化进度条。

        Args:
            total: 总任务数
            width: 进度条显示宽度（字符数）
            prefix: 进度条前缀文字
        """
        self.total = max(total, 1)
        self.current = 0
        self.width = width
        self.prefix = prefix
        self._start_time = time.time()
        self._last_print_len = 0

    def update(self, current: Optional[int] = None) -> None:
        """更新进度条。

        Args:
            current: 当前进度值，如果不指定则自动加1
        """
        if current is not None:
            self.current = current
        else:
            self.current += 1

        # 计算进度百分比
        progress = min(self.current / self.total, 1.0)
        percent = progress * 100

        # 构建进度条
        filled = int(self.width * progress)
        bar = "█" * filled + "░" * (self.width - filled)

        # 计算已用时间
        elapsed = time.time() - self._start_time
        if progress > 0:
            eta = elapsed / progress - elapsed
            eta_str = _format_time(eta)
        else:
            eta_str = "--:--"

        elapsed_str = _format_time(elapsed)

        # 构建输出行
        line = (
            f"\r{self.prefix}: [{bar}] {self.current}/{self.total} "
            f"({percent:.1f}%) ETA: {eta_str} Elapsed: {elapsed_str}"
        )

        # 清除之前的内容
        clear = "\b" * self._last_print_len if self._last_print_len > 0 else ""
        sys.stdout.write(clear + line)
        sys.stdout.flush()
        self._last_print_len = len(line)

    def finish(self) -> None:
        """完成进度条，换行。"""
        sys.stdout.write("\n")
        sys.stdout.flush()

    def __enter__(self) -> "ProgressBar":
        """支持上下文管理器。"""
        return self

    def __exit__(self, *args: object) -> None:
        """退出上下文时自动完成。"""
        self.finish()


def _format_time(seconds: float) -> str:
    """格式化时间为 HH:MM:SS 或 MM:SS 格式。

    Args:
        seconds: 秒数

    Returns:
        格式化的时间字符串
    """
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


# ============================================================
# 文件大小格式化
# ============================================================

def format_size(size_bytes: int) -> str:
    """将字节数格式化为人类可读的大小表示。

    Args:
        size_bytes: 字节数

    Returns:
        格式化后的大小字符串

    Examples:
        >>> format_size(1024)
        '1.00 KB'
        >>> format_size(1048576)
        '1.00 MB'
    """
    if size_bytes < 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"


# ============================================================
# 哈希计算
# ============================================================

def hash_url(url: str, algorithm: str = "md5") -> str:
    """计算URL的哈希值，用于URL去重。

    Args:
        url: 待哈希的URL
        algorithm: 哈希算法（md5/sha1/sha256）

    Returns:
        哈希值的十六进制字符串

    Examples:
        >>> hash_url("https://example.com")[:8]
        '8f1b3e4a'
    """
    url_normalized = normalize_url(url)
    hasher = hashlib.new(algorithm)
    hasher.update(url_normalized.encode("utf-8"))
    return hasher.hexdigest()


def hash_content(content: str, algorithm: str = "md5") -> str:
    """计算内容哈希值，用于内容去重。

    Args:
        content: 待哈希的内容
        algorithm: 哈希算法

    Returns:
        哈希值的十六进制字符串
    """
    hasher = hashlib.new(algorithm)
    hasher.update(content.encode("utf-8"))
    return hasher.hexdigest()
