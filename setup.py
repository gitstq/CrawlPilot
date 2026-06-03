from setuptools import setup, find_packages

setup(
    name="crawl-pilot",
    version="0.1.0",
    description="CrawlPilot - 智能自适应Web爬虫引擎",
    long_description=open("README.md", "r", encoding="utf-8").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="CrawlPilot Team",
    author_email="crawl-pilot@example.com",
    license="MIT",
    url="https://github.com/crawl-pilot/crawl-pilot",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[],
    extras_require={
        "httpx": ["httpx>=0.24.0"],
        "lxml": ["lxml>=4.9.0"],
        "beautifulsoup4": ["beautifulsoup4>=4.12.0"],
        "full": [
            "httpx>=0.24.0",
            "lxml>=4.9.0",
            "beautifulsoup4>=4.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "crawl-pilot=crawl_pilot.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
