from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup

from markitdown_app.core.html_to_md import html_fragment_to_markdown


@dataclass
class FetchResult:
    title: str | None
    html_markdown: str


def fetch_weixin_article(session, url: str) -> FetchResult:
    weixin_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://mp.weixin.qq.com/",
    }

    original_headers = session.headers.copy()
    session.headers.update(weixin_headers)
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()

        text = resp.text
        soup = BeautifulSoup(text, 'lxml')

        title = None
        title_elem = (
            soup.find(attrs={'property': 'twitter:title'}) or
            soup.find(attrs={'property': 'og:title'}) or
            soup.find('h1', class_='rich_media_title') or
            soup.find('h1') or
            soup.find('title')
        )
        if title_elem:
            title = getattr(title_elem, 'get', lambda *_: None)('content') or title_elem.get_text(strip=True)

        content_elem = soup.find('div', class_='rich_media_content') or soup.find('div', id='js_content')
        if content_elem:
            for img in content_elem.find_all('img', {'data-src': True}):
                img['src'] = img['data-src']
                del img['data-src']
            for script in content_elem.find_all(['script', 'style']):
                script.decompose()
            md = html_fragment_to_markdown(content_elem)
        else:
            md = ""

        if title:
            md = (f"# {title}\n\n" + md) if md else f"# {title}\n\n"
        return FetchResult(title=title, html_markdown=md)
    finally:
        session.headers = original_headers


