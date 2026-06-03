# CrawlPilot

CrawlPilot is an intelligent adaptive web crawling engine built with Python.

## Features

- Zero mandatory dependencies (pure standard library)
- Smart anti-bot detection and adaptive strategy switching
- Chainable data extraction pipeline
- Concurrent crawling with rate limiting
- Multiple storage backends (JSON/CSV/SQLite)
- Checkpoint and resume support

## Installation

```bash
pip install -e .
```

With optional dependencies:

```bash
pip install -e ".[full]"
```

## Quick Start

```python
from crawl_pilot import FetchEngine, HTMLParser, Pipeline

# Fetch a page
fetcher = FetchEngine()
response = fetcher.get("https://example.com")

# Parse HTML
parser = HTMLParser(response.text, url=response.url)
print(parser.title)
print(parser.links)

# Extract data with pipeline
pipeline = Pipeline()
pipeline.extract("title", css="h1")
pipeline.extract("content", css="p")
result = pipeline.run(response.text)
print(result)
```

## CLI Usage

```bash
# Crawl a single URL
crawl-pilot crawl https://example.com

# Crawl with CSS selector
crawl-pilot crawl https://example.com --selector "h1.title"

# Crawl entire site
crawl-pilot crawl-site https://example.com --depth 2 --output json

# Parse local HTML file
crawl-pilot parse page.html --selector "div.content"
```

## License

MIT License
