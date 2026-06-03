"""
CrawlPilot - HTTP请求引擎模块

提供智能HTTP请求功能，包括自动重试、超时控制、User-Agent轮换、
Session管理、代理支持等特性。

核心类：
    - FetchResponse: 统一响应对象
    - FetchEngine: HTTP请求引擎
"""

import json
import logging
import random
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from crawl_pilot.utils import (
    FetchError,
    detect_encoding,
    format_size,
)

logger = logging.getLogger("crawl_pilot.fetcher")


# ============================================================
# 内置User-Agent列表
# ============================================================

USER_AGENTS: list = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    # Chrome (Linux)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox (Linux)
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Chrome (Android)
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    # Safari (iOS)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    # Chrome (iOS)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile Safari/604.1",
]


# ============================================================
# 默认请求头
# ============================================================

DEFAULT_HEADERS: Dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


# ============================================================
# FetchResponse - 统一响应对象
# ============================================================

class FetchResponse:
    """统一的HTTP响应对象。

    封装HTTP响应数据，提供便捷的属性访问方法。

    Attributes:
        url: 最终响应的URL（可能经过重定向）
        status_code: HTTP状态码
        headers: 响应头字典
        content: 原始响应内容（字节）
        text: 解码后的文本内容
        encoding: 检测到的编码
        elapsed: 请求耗时（秒）
        history: 重定向历史
        ok: 请求是否成功（状态码 < 400）
    """

    def __init__(
        self,
        url: str,
        status_code: int,
        headers: Dict[str, str],
        content: bytes,
        encoding: str = "utf-8",
        elapsed: float = 0.0,
        history: Optional[list] = None,
    ) -> None:
        """初始化响应对象。

        Args:
            url: 最终响应的URL
            status_code: HTTP状态码
            headers: 响应头字典
            content: 原始响应内容（字节）
            encoding: 文本编码
            elapsed: 请求耗时（秒）
            history: 重定向历史列表
        """
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self._encoding = encoding
        self._text: Optional[str] = None
        self.elapsed = elapsed
        self.history = history or []

    @property
    def text(self) -> str:
        """获取解码后的文本内容。

        Returns:
            解码后的文本字符串
        """
        if self._text is None:
            self._text = self.content.decode(self._encoding, errors="replace")
        return self._text

    @property
    def encoding(self) -> str:
        """获取响应编码。

        Returns:
            编码名称
        """
        return self._encoding

    @property
    def ok(self) -> bool:
        """检查请求是否成功。

        Returns:
            状态码小于400返回True
        """
        return self.status_code < 400

    @property
    def content_length(self) -> int:
        """获取响应内容长度。

        Returns:
            内容字节数
        """
        return len(self.content)

    @property
    def size(self) -> str:
        """获取格式化的内容大小。

        Returns:
            人类可读的大小字符串
        """
        return format_size(self.content_length)

    def json(self) -> Any:
        """将响应内容解析为JSON。

        Returns:
            解析后的JSON对象

        Raises:
            json.JSONDecodeError: 当内容不是有效JSON时
        """
        return json.loads(self.text)

    def __repr__(self) -> str:
        return (
            f"<FetchResponse [{self.status_code}] "
            f"url={self.url} size={self.size}>"
        )


# ============================================================
# FetchEngine - HTTP请求引擎
# ============================================================

class FetchEngine:
    """HTTP请求引擎。

    提供智能HTTP请求功能，支持自动重试、UA轮换、超时控制、
    Session管理、代理支持等特性。

    优先使用httpx作为HTTP后端（高性能），如果不可用则回退到
    标准库urllib。

    Attributes:
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
        retry_delay: 重试基础延迟（秒）
        verify_ssl: 是否验证SSL证书
        proxy: 代理地址
        headers: 默认请求头
        session_cookies: Session Cookie存储

    Examples:
        >>> fetcher = FetchEngine(timeout=15, max_retries=2)
        >>> response = fetcher.get("https://example.com")
        >>> print(response.status_code, response.size)
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        verify_ssl: bool = True,
        proxy: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        user_agent: Optional[str] = None,
        rotate_ua: bool = True,
    ) -> None:
        """初始化请求引擎。

        Args:
            timeout: 请求超时时间（秒），默认30
            max_retries: 最大重试次数，默认3
            retry_delay: 重试基础延迟（秒），默认1.0
            verify_ssl: 是否验证SSL证书，默认True
            proxy: 代理地址（格式：http://host:port 或 socks5://host:port）
            headers: 自定义默认请求头
            user_agent: 固定User-Agent（设置后不轮换）
            rotate_ua: 是否自动轮换User-Agent，默认True
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.verify_ssl = verify_ssl
        self.proxy = proxy
        self.rotate_ua = rotate_ua
        self._fixed_ua = user_agent

        # 合并默认请求头
        self.headers = dict(DEFAULT_HEADERS)
        if headers:
            self.headers.update(headers)

        # Session Cookie存储
        self.session_cookies: Dict[str, Dict[str, str]] = {}

        # 检测httpx是否可用
        self._use_httpx = self._check_httpx()

        if self._use_httpx:
            logger.debug("使用 httpx 作为HTTP后端")
        else:
            logger.debug("使用 urllib 作为HTTP后端（httpx不可用）")

    @staticmethod
    def _check_httpx() -> bool:
        """检查httpx是否可用。

        Returns:
            httpx可用返回True
        """
        try:
            import httpx  # type: ignore
            return True
        except ImportError:
            return False

    def _get_user_agent(self) -> str:
        """获取当前请求的User-Agent。

        Returns:
            User-Agent字符串
        """
        if self._fixed_ua:
            return self._fixed_ua
        if self.rotate_ua:
            return random.choice(USER_AGENTS)
        return USER_AGENTS[0]

    def _build_headers(
        self,
        url: str,
        method: str = "GET",
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """构建完整的请求头。

        Args:
            url: 请求URL
            method: 请求方法
            extra_headers: 额外请求头

        Returns:
            完整的请求头字典
        """
        headers = dict(self.headers)
        headers["User-Agent"] = self._get_user_agent()

        # 根据请求方法设置Referer
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"

        # 添加额外请求头
        if extra_headers:
            headers.update(extra_headers)

        return headers

    def _get_cookies_for_url(self, url: str) -> Dict[str, str]:
        """获取指定URL的Cookie。

        Args:
            url: 目标URL

        Returns:
            Cookie字典
        """
        domain = urlparse(url).netloc
        cookies = {}
        for cookie_domain, cookie_jar in self.session_cookies.items():
            if domain.endswith(cookie_domain) or cookie_domain.endswith(domain):
                cookies.update(cookie_jar)
        return cookies

    def _store_cookies(self, url: str, set_cookie_header: str) -> None:
        """存储Set-Cookie响应头中的Cookie。

        Args:
            url: 来源URL
            set_cookie_header: Set-Cookie响应头值
        """
        domain = urlparse(url).netloc
        if domain not in self.session_cookies:
            self.session_cookies[domain] = {}

        # 简单解析Set-Cookie（name=value; ...）
        for cookie_str in set_cookie_header.split(","):
            cookie_str = cookie_str.strip()
            if "=" in cookie_str:
                name_value = cookie_str.split(";")[0].strip()
                if "=" in name_value:
                    name, value = name_value.split("=", 1)
                    self.session_cookies[domain][name.strip()] = value.strip()

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        allow_redirects: bool = True,
    ) -> FetchResponse:
        """发送HTTP请求。

        支持自动重试、UA轮换、超时控制等特性。

        Args:
            method: HTTP方法（GET/POST/HEAD）
            url: 请求URL
            params: URL查询参数
            data: POST表单数据
            json_data: POST JSON数据
            headers: 额外请求头
            timeout: 覆盖默认超时
            allow_redirects: 是否允许重定向

        Returns:
            FetchResponse响应对象

        Raises:
            FetchError: 请求失败时抛出
        """
        timeout = timeout or self.timeout
        request_headers = self._build_headers(url, method, headers)
        cookies = self._get_cookies_for_url(url)

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                # 指数退避
                if attempt > 0:
                    delay = self.retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    logger.debug(
                        f"重试第 {attempt + 1} 次，等待 {delay:.2f}s"
                    )
                    time.sleep(delay)

                if self._use_httpx:
                    response = self._request_httpx(
                        method=method,
                        url=url,
                        params=params,
                        data=data,
                        json_data=json_data,
                        headers=request_headers,
                        cookies=cookies,
                        timeout=timeout,
                        allow_redirects=allow_redirects,
                    )
                else:
                    response = self._request_urllib(
                        method=method,
                        url=url,
                        params=params,
                        data=data,
                        json_data=json_data,
                        headers=request_headers,
                        cookies=cookies,
                        timeout=timeout,
                        allow_redirects=allow_redirects,
                    )

                # 存储Cookie
                if "set-cookie" in response.headers:
                    self._store_cookies(url, response.headers["set-cookie"])

                # 检查状态码
                if response.status_code >= 500:
                    logger.warning(
                        f"服务器错误 {response.status_code}，URL: {url}"
                    )
                    if attempt < self.max_retries - 1:
                        continue

                if response.status_code == 429:
                    logger.warning(f"速率限制 (429)，URL: {url}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * 3)
                        continue

                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    continue

        raise FetchError(
            f"请求失败，已重试 {self.max_retries} 次: {last_error}",
            url=url,
        )

    def _request_httpx(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, str]],
        data: Optional[Dict[str, str]],
        json_data: Optional[Dict[str, Any]],
        headers: Dict[str, str],
        cookies: Dict[str, str],
        timeout: int,
        allow_redirects: bool,
    ) -> FetchResponse:
        """使用httpx发送请求。

        Args:
            method: HTTP方法
            url: 请求URL
            params: URL查询参数
            data: POST表单数据
            json_data: POST JSON数据
            headers: 请求头
            cookies: Cookie
            timeout: 超时时间
            allow_redirects: 是否允许重定向

        Returns:
            FetchResponse响应对象
        """
        import httpx  # type: ignore

        # 构建代理
        proxies = None
        if self.proxy:
            proxies = self.proxy

        # 构建客户端参数
        client_kwargs: Dict[str, Any] = {
            "timeout": timeout,
            "verify": self.verify_ssl,
            "follow_redirects": allow_redirects,
        }
        if proxies:
            client_kwargs["proxy"] = proxies

        with httpx.Client(**client_kwargs) as client:
            request_kwargs: Dict[str, Any] = {
                "method": method,
                "url": url,
                "headers": headers,
                "cookies": cookies,
            }
            if params:
                request_kwargs["params"] = params
            if data:
                request_kwargs["data"] = data
            if json_data:
                request_kwargs["json"] = json_data

            start_time = time.time()
            resp = client.request(**request_kwargs)
            elapsed = time.time() - start_time

            # 收集重定向历史
            history = []
            if resp.history:
                for h in resp.history:
                    history.append(
                        FetchResponse(
                            url=str(h.url),
                            status_code=h.status_code,
                            headers=dict(h.headers),
                            content=h.content,
                            elapsed=0,
                        )
                    )

            # 检测编码
            encoding = "utf-8"
            if resp.encoding:
                encoding = resp.encoding
            else:
                encoding = detect_encoding(resp.content)

            return FetchResponse(
                url=str(resp.url),
                status_code=resp.status_code,
                headers=dict(resp.headers),
                content=resp.content,
                encoding=encoding,
                elapsed=elapsed,
                history=history,
            )

    def _request_urllib(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, str]],
        data: Optional[Dict[str, str]],
        json_data: Optional[Dict[str, Any]],
        headers: Dict[str, str],
        cookies: Dict[str, str],
        timeout: int,
        allow_redirects: bool,
    ) -> FetchResponse:
        """使用标准库urllib发送请求。

        Args:
            method: HTTP方法
            url: 请求URL
            params: URL查询参数
            data: POST表单数据
            json_data: POST JSON数据
            headers: 请求头
            cookies: Cookie
            timeout: 超时时间
            allow_redirects: 是否允许重定向

        Returns:
            FetchResponse响应对象
        """
        import urllib.request
        import urllib.parse
        import urllib.error
        import ssl

        # 构建完整URL（含查询参数）
        if params:
            query_string = urllib.parse.urlencode(params)
            if "?" in url:
                url = f"{url}&{query_string}"
            else:
                url = f"{url}?{query_string}"

        # 准备请求体
        body: Optional[bytes] = None
        if json_data:
            body = json.dumps(json_data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif data:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        # 构建Cookie头
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            headers["Cookie"] = cookie_str

        # 创建请求对象
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        # SSL上下文
        ssl_context: Optional[ssl.SSLContext] = None
        if not self.verify_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        # 设置代理
        if self.proxy:
            proxy_handler = urllib.request.ProxyHandler(
                {"http": self.proxy, "https": self.proxy}
            )
            opener = urllib.request.build_opener(proxy_handler)
        else:
            opener = urllib.request.build_opener()

        # 发送请求
        start_time = time.time()
        try:
            resp = opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            # HTTPError也会返回响应体
            resp = e
        elapsed = time.time() - start_time

        # 读取响应
        response_content = resp.read()

        # 获取响应头
        response_headers: Dict[str, str] = {}
        if hasattr(resp, "headers"):
            for key, value in resp.headers.items():
                response_headers[key.lower()] = value

        # 获取最终URL
        final_url = getattr(resp, "url", url)

        # 获取状态码
        status_code = getattr(resp, "status", 200)
        if hasattr(resp, "code"):
            status_code = resp.code

        # 检测编码
        encoding = "utf-8"
        content_type = response_headers.get("content-type", "")
        if "charset=" in content_type:
            charset_match = content_type.split("charset=")[-1].strip("; ")
            if charset_match:
                encoding = charset_match
        else:
            encoding = detect_encoding(response_content)

        return FetchResponse(
            url=final_url,
            status_code=status_code,
            headers=response_headers,
            content=response_content,
            encoding=encoding,
            elapsed=elapsed,
        )

    def get(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        allow_redirects: bool = True,
    ) -> FetchResponse:
        """发送GET请求。

        Args:
            url: 请求URL
            params: URL查询参数
            headers: 额外请求头
            timeout: 覆盖默认超时
            allow_redirects: 是否允许重定向

        Returns:
            FetchResponse响应对象
        """
        return self.request(
            method="GET",
            url=url,
            params=params,
            headers=headers,
            timeout=timeout,
            allow_redirects=allow_redirects,
        )

    def post(
        self,
        url: str,
        data: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> FetchResponse:
        """发送POST请求。

        Args:
            url: 请求URL
            data: POST表单数据
            json_data: POST JSON数据
            headers: 额外请求头
            timeout: 覆盖默认超时

        Returns:
            FetchResponse响应对象
        """
        return self.request(
            method="POST",
            url=url,
            data=data,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
        )

    def head(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> FetchResponse:
        """发送HEAD请求。

        Args:
            url: 请求URL
            headers: 额外请求头
            timeout: 覆盖默认超时

        Returns:
            FetchResponse响应对象
        """
        return self.request(
            method="HEAD",
            url=url,
            headers=headers,
            timeout=timeout,
        )

    def close(self) -> None:
        """关闭请求引擎，清理资源。"""
        self.session_cookies.clear()
        logger.debug("请求引擎已关闭")

    def __enter__(self) -> "FetchEngine":
        """支持上下文管理器。"""
        return self

    def __exit__(self, *args: object) -> None:
        """退出上下文时自动关闭。"""
        self.close()

    def __repr__(self) -> str:
        backend = "httpx" if self._use_httpx else "urllib"
        return (
            f"<FetchEngine backend={backend} "
            f"timeout={self.timeout}s retries={self.max_retries}>"
        )
