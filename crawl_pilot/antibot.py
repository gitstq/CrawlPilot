"""
CrawlPilot - 反爬检测与自适应策略模块

提供反爬机制检测和自适应策略切换功能，包括Cloudflare检测、
验证码识别、速率限制响应处理、robots.txt解析和礼貌爬取策略。

核心类：
    - AntiBotDetection: 反爬检测结果
    - AntiBotDetector: 反爬检测器
    - RobotParser: robots.txt解析器
    - PolitenessPolicy: 礼貌爬取策略
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from crawl_pilot.utils import FetchError

if TYPE_CHECKING:
    from crawl_pilot.fetcher import FetchResponse

logger = logging.getLogger("crawl_pilot.antibot")


# ============================================================
# 反爬检测结果
# ============================================================

@dataclass
class AntiBotDetection:
    """反爬检测结果。

    Attributes:
        detected: 是否检测到反爬机制
        bot_type: 检测到的反爬类型
        confidence: 检测置信度（0.0-1.0）
        evidence: 检测证据列表
        recommended_action: 建议采取的操作
    """

    detected: bool = False
    bot_type: str = ""
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    recommended_action: str = ""

    def __repr__(self) -> str:
        if not self.detected:
            return "<AntiBotDetection [clean]>"
        return (
            f"<AntiBotDetection [detected] type={self.bot_type} "
            f"confidence={self.confidence:.2f}>"
        )


# ============================================================
# 反爬检测器
# ============================================================

class AntiBotDetector:
    """反爬检测器。

    检测常见的反爬机制，包括：
    - Cloudflare保护
    - 验证码页面（CAPTCHA）
    - 蜜罐链接
    - 速率限制响应
    - 基本认证要求
    - JavaScript挑战页面

    Attributes:
        adaptive: 是否启用自适应策略

    Examples:
        >>> detector = AntiBotDetector()
        >>> result = detector.detect(response)
        >>> if result.detected:
        ...     print(f"检测到 {result.bot_type}")
    """

    # Cloudflare检测模式
    CF_PATTERNS: List[str] = [
        r"cloudflare",
        r"cf-browser-verification",
        r"cf-ray",
        r"__cfduid",
        r"cf_clearance",
        r"challenge-platform",
        r"cf-challenge",
        r"cf.turnstile",
    ]

    # 验证码检测模式
    CAPTCHA_PATTERNS: List[str] = [
        r"captcha",
        r"recaptcha",
        r"g-recaptcha",
        r"hcaptcha",
        r"turnstile",
        r"验证码",
        r"please verify",
        r"are you a robot",
        r"human verification",
        r"prove you are human",
    ]

    # 速率限制检测模式
    RATE_LIMIT_PATTERNS: List[str] = [
        r"rate.?limit",
        r"too many requests",
        r"请求过于频繁",
        r"访问过于频繁",
        r"429",
        r"slow down",
        r"throttl",
    ]

    # JavaScript挑战检测模式
    JS_CHALLENGE_PATTERNS: List[str] = [
        r"javascript challenge",
        r"please enable javascript",
        r"js challenge",
        r"checking your browser",
        r"just a moment",
        r"please wait",
        r"检测中",
    ]

    # 蜜罐链接检测模式
    HONEYPOT_PATTERNS: List[str] = [
        r"display:\s*none",
        r"visibility:\s*hidden",
        r"opacity:\s*0",
        r"position:\s*absolute.*left:\s*-9999",
        r"font-size:\s*0",
        r"color:\s*transparent",
        r"clip:\s*rect\(0",
    ]

    def __init__(self, adaptive: bool = True) -> None:
        """初始化反爬检测器。

        Args:
            adaptive: 是否启用自适应策略（检测到反爬时自动调整）
        """
        self.adaptive = adaptive
        self._domain_stats: Dict[str, Dict[str, int]] = {}

    def detect(self, response: "FetchResponse") -> AntiBotDetection:
        """检测响应中是否包含反爬机制。

        综合分析响应状态码、响应头和响应内容，判断是否存在反爬机制。

        Args:
            response: HTTP响应对象

        Returns:
            AntiBotDetection检测结果
        """
        result = AntiBotDetection()
        evidence: List[str] = []

        # 1. 检查状态码
        if response.status_code == 403:
            evidence.append("HTTP 403 Forbidden")
            result.confidence += 0.3

        if response.status_code == 429:
            evidence.append("HTTP 429 Too Many Requests")
            result.confidence += 0.5
            result.bot_type = "rate_limit"
            result.recommended_action = "slow_down"

        if response.status_code == 503:
            evidence.append("HTTP 503 Service Unavailable")
            result.confidence += 0.2

        # 2. 检查响应头
        server = response.headers.get("server", "").lower()
        if "cloudflare" in server:
            evidence.append(f"Server: {server}")
            result.confidence += 0.4
            result.bot_type = "cloudflare"
            result.recommended_action = "add_cf_headers"

        cf_ray = response.headers.get("cf-ray", "")
        if cf_ray:
            evidence.append(f"CF-Ray: {cf_ray}")
            result.confidence += 0.3
            if not result.bot_type:
                result.bot_type = "cloudflare"
                result.recommended_action = "add_cf_headers"

        # 3. 检查响应内容
        text_lower = response.text.lower()
        html_lower = text_lower

        # 检测Cloudflare
        for pattern in self.CF_PATTERNS:
            if re.search(pattern, html_lower):
                evidence.append(f"Content matches Cloudflare pattern: {pattern}")
                result.confidence += 0.2
                if not result.bot_type:
                    result.bot_type = "cloudflare"
                    result.recommended_action = "add_cf_headers"
                break

        # 检测验证码
        for pattern in self.CAPTCHA_PATTERNS:
            if re.search(pattern, html_lower):
                evidence.append(f"Content matches CAPTCHA pattern: {pattern}")
                result.confidence += 0.5
                result.bot_type = "captcha"
                result.recommended_action = "skip_page"
                break

        # 检测速率限制
        for pattern in self.RATE_LIMIT_PATTERNS:
            if re.search(pattern, html_lower):
                evidence.append(f"Content matches rate limit pattern: {pattern}")
                result.confidence += 0.4
                if not result.bot_type:
                    result.bot_type = "rate_limit"
                    result.recommended_action = "slow_down"
                break

        # 检测JavaScript挑战
        for pattern in self.JS_CHALLENGE_PATTERNS:
            if re.search(pattern, html_lower):
                evidence.append(f"Content matches JS challenge pattern: {pattern}")
                result.confidence += 0.3
                if not result.bot_type:
                    result.bot_type = "js_challenge"
                    result.recommended_action = "skip_page"
                break

        # 4. 检查页面大小（异常小的页面可能是反爬页面）
        if response.content_length < 500 and response.status_code == 200:
            evidence.append(f"页面异常小: {response.content_length} bytes")
            result.confidence += 0.1

        # 5. 检查是否为空页面
        stripped = response.text.strip()
        if not stripped:
            evidence.append("空响应页面")
            result.confidence += 0.2

        # 综合判断
        result.evidence = evidence
        result.confidence = min(result.confidence, 1.0)
        result.detected = result.confidence >= 0.3

        if result.detected:
            logger.warning(
                f"检测到反爬机制: type={result.bot_type} "
                f"confidence={result.confidence:.2f} "
                f"evidence={evidence}"
            )

        return result

    def detect_honeypot(self, html: str, url: str) -> List[str]:
        """检测HTML中的蜜罐链接。

        蜜罐链接是隐藏在页面中但对用户不可见的链接，
        用于检测爬虫（正常用户不会点击这些链接）。

        Args:
            html: HTML内容
            url: 页面URL（用于日志记录）

        Returns:
            检测到的蜜罐链接列表
        """
        honeypots: List[str] = []

        # 查找隐藏元素中的链接
        # 匹配带有隐藏样式的元素中的href
        hidden_pattern = (
            r'<[^>]+(?:' +
            "|".join(self.HONEYPOT_PATTERNS) +
            r')[^>]*>.*?<a[^>]+href=["\']([^"\']+)["\'][^>]*>'
        )

        matches = re.findall(hidden_pattern, html, re.IGNORECASE | re.DOTALL)
        honeypots.extend(matches)

        if honeypots:
            logger.debug(f"在 {url} 中检测到 {len(honeypots)} 个蜜罐链接")

        return honeypots

    def get_adaptive_headers(self, bot_type: str) -> Dict[str, str]:
        """根据反爬类型获取自适应请求头。

        Args:
            bot_type: 反爬类型

        Returns:
            建议添加的请求头
        """
        headers: Dict[str, str] = {}

        if bot_type == "cloudflare":
            headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Alt-Used": urlparse(
                    "https://example.com"
                ).netloc,  # 占位，实际使用时替换
                "Sec-CH-UA": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": '"Windows"',
            })

        elif bot_type == "js_challenge":
            headers.update({
                "Accept": "*/*",
                "Sec-Fetch-Dest": "script",
                "Sec-Fetch-Mode": "no-cors",
            })

        return headers

    def get_adaptive_delay(self, bot_type: str, current_delay: float) -> float:
        """根据反爬类型获取自适应延迟。

        Args:
            bot_type: 反爬类型
            current_delay: 当前延迟（秒）

        Returns:
            建议的新延迟（秒）
        """
        if bot_type == "rate_limit":
            return min(current_delay * 3, 30.0)
        elif bot_type == "cloudflare":
            return min(current_delay * 2, 15.0)
        elif bot_type == "captcha":
            return min(current_delay * 5, 60.0)
        return current_delay

    def _update_domain_stats(self, domain: str, status: str) -> None:
        """更新域名级别的统计信息。

        Args:
            domain: 域名
            status: 状态（detected/clean）
        """
        if domain not in self._domain_stats:
            self._domain_stats[domain] = {"detected": 0, "clean": 0}
        self._domain_stats[domain][status] += 1

    def get_domain_risk(self, domain: str) -> float:
        """获取域名风险评分。

        Args:
            domain: 域名

        Returns:
            风险评分（0.0-1.0）
        """
        stats = self._domain_stats.get(domain, {})
        detected = stats.get("detected", 0)
        clean = stats.get("clean", 0)
        total = detected + clean
        if total == 0:
            return 0.0
        return detected / total


# ============================================================
# robots.txt 解析器
# ============================================================

class RobotParser:
    """robots.txt解析器。

    基于标准库urllib.robotparser实现，提供便捷的接口来判断
    特定URL是否允许被爬取。

    Attributes:
        user_agent: 爬虫的User-Agent标识

    Examples:
        >>> parser = RobotParser("CrawlPilot/0.1.0")
        >>> parser.fetch("https://example.com/robots.txt")
        >>> parser.can_fetch("https://example.com/page")
        True
    """

    def __init__(self, user_agent: str = "CrawlPilot/0.1.0") -> None:
        """初始化robots.txt解析器。

        Args:
            user_agent: 爬虫的User-Agent标识
        """
        self.user_agent = user_agent
        self._parsers: Dict[str, RobotFileParser] = {}
        self._fetcher = FetchEngine(timeout=10, max_retries=1)

    def fetch(self, url: str) -> bool:
        """获取并解析robots.txt。

        Args:
            url: 网站URL（自动拼接/robots.txt路径）

        Returns:
            成功获取返回True，失败或不存在返回False
        """
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        domain = parsed.netloc

        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            # 使用标准库方式读取
            import urllib.request
            req = urllib.request.Request(
                robots_url,
                headers={"User-Agent": self.user_agent},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            rp.parse(resp.read().decode("utf-8", errors="replace").splitlines())
            self._parsers[domain] = rp
            logger.debug(f"已解析 robots.txt: {robots_url}")
            return True
        except Exception as e:
            logger.debug(f"无法获取 robots.txt ({robots_url}): {e}")
            # 默认允许所有
            rp = RobotFileParser()
            rp.set_url(robots_url)
            self._parsers[domain] = rp
            return False

    def can_fetch(self, url: str) -> bool:
        """检查URL是否允许被爬取。

        Args:
            url: 待检查的URL

        Returns:
            允许爬取返回True
        """
        parsed = urlparse(url)
        domain = parsed.netloc

        if domain not in self._parsers:
            self.fetch(url)

        rp = self._parsers.get(domain)
        if rp is None:
            return True

        return rp.can_fetch(self.user_agent, url)

    def get_crawl_delay(self, url: str) -> Optional[float]:
        """获取爬取延迟（由robots.txt指定）。

        Args:
            url: URL

        Returns:
            爬取延迟（秒），未指定返回None
        """
        parsed = urlparse(url)
        domain = parsed.netloc

        if domain not in self._parsers:
            self.fetch(url)

        rp = self._parsers.get(domain)
        if rp is None:
            return None

        return rp.crawl_delay(self.user_agent)

    def get_sitemaps(self, url: str) -> List[str]:
        """获取Sitemap URL列表。

        Args:
            url: 网站URL

        Returns:
            Sitemap URL列表
        """
        parsed = urlparse(url)
        domain = parsed.netloc

        if domain not in self._parsers:
            self.fetch(url)

        rp = self._parsers.get(domain)
        if rp is None:
            return []

        return rp.sitemaps

    def close(self) -> None:
        """关闭解析器，清理资源。"""
        self._parsers.clear()
        self._fetcher.close()


# ============================================================
# 礼貌爬取策略
# ============================================================

class PolitenessPolicy:
    """礼貌爬取策略。

    实现域名级别的速率限制，确保对目标网站友好。

    Attributes:
        default_delay: 默认请求间隔（秒）
        domain_delays: 域名级别的自定义延迟
        last_access: 域名级别的最后访问时间

    Examples:
        >>> policy = PolitenessPolicy(default_delay=1.0)
        >>> policy.wait("example.com")  # 等待适当时间
        >>> # 然后发送请求...
    """

    def __init__(
        self,
        default_delay: float = 1.0,
        max_concurrent_per_domain: int = 1,
    ) -> None:
        """初始化礼貌爬取策略。

        Args:
            default_delay: 默认请求间隔（秒）
            max_concurrent_per_domain: 每个域名最大并发数
        """
        self.default_delay = default_delay
        self.max_concurrent_per_domain = max_concurrent_per_domain
        self._domain_delays: Dict[str, float] = {}
        self._last_access: Dict[str, float] = {}
        self._domain_concurrent: Dict[str, int] = {}

    def set_delay(self, domain: str, delay: float) -> None:
        """设置特定域名的请求延迟。

        Args:
            domain: 域名
            delay: 延迟时间（秒）
        """
        self._domain_delays[domain] = delay
        logger.debug(f"设置域名 {domain} 的延迟为 {delay}s")

    def get_delay(self, domain: str) -> float:
        """获取域名的请求延迟。

        Args:
            domain: 域名

        Returns:
            延迟时间（秒）
        """
        return self._domain_delays.get(domain, self.default_delay)

    def wait(self, domain: str) -> float:
        """等待适当时间后再请求指定域名。

        根据域名的最后访问时间和配置的延迟，计算需要等待的时间。

        Args:
            domain: 目标域名

        Returns:
            实际等待时间（秒）
        """
        delay = self.get_delay(domain)
        now = time.time()
        last = self._last_access.get(domain, 0)
        elapsed = now - last

        if elapsed < delay:
            wait_time = delay - elapsed
            logger.debug(f"礼貌等待 {wait_time:.2f}s (域名: {domain})")
            time.sleep(wait_time)
            return wait_time

        return 0.0

    def record_access(self, domain: str) -> None:
        """记录对域名的访问。

        Args:
            domain: 访问的域名
        """
        self._last_access[domain] = time.time()

    def can_access(self, domain: str) -> bool:
        """检查是否可以立即访问域名。

        Args:
            domain: 目标域名

        Returns:
            可以访问返回True
        """
        if self._domain_concurrent.get(domain, 0) >= self.max_concurrent_per_domain:
            return False

        delay = self.get_delay(domain)
        last = self._last_access.get(domain, 0)
        return (time.time() - last) >= delay

    def enter_domain(self, domain: str) -> None:
        """进入域名访问（增加并发计数）。

        Args:
            domain: 域名
        """
        self._domain_concurrent[domain] = self._domain_concurrent.get(domain, 0) + 1

    def leave_domain(self, domain: str) -> None:
        """离开域名访问（减少并发计数）。

        Args:
            domain: 域名
        """
        count = self._domain_concurrent.get(domain, 0)
        if count > 0:
            self._domain_concurrent[domain] = count - 1

    def adapt_from_detection(self, domain: str, bot_type: str) -> None:
        """根据反爬检测结果自适应调整策略。

        Args:
            domain: 域名
            bot_type: 反爬类型
        """
        current_delay = self.get_delay(domain)

        if bot_type == "rate_limit":
            new_delay = min(current_delay * 3, 30.0)
        elif bot_type == "cloudflare":
            new_delay = min(current_delay * 2, 15.0)
        elif bot_type == "captcha":
            new_delay = min(current_delay * 5, 60.0)
        else:
            new_delay = min(current_delay * 1.5, 10.0)

        self.set_delay(domain, new_delay)
        logger.warning(
            f"自适应调整: 域名 {domain} 延迟从 {current_delay}s 调整为 {new_delay}s"
        )
