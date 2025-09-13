from __future__ import annotations

import random
from typing import Optional, Any, Iterable, Mapping

# --- Lifecycle helpers ---

def new_context_and_page_from_shared(shared_browser: Any, context_options: Optional[dict] = None, apply_stealth: bool = True) -> tuple[Any, Any]:
    """Create a fresh BrowserContext and Page from a shared Browser.

    context_options can override defaults such as UA/locale/headers.
    apply_stealth: whether to apply stealth scripts (default: True)
    """
    options = {
        'viewport': {'width': 1920, 'height': 1080},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'locale': 'zh-CN',
        'timezone_id': 'Asia/Shanghai',
        'geolocation': {'latitude': 39.9042, 'longitude': 116.4074},
        'permissions': ['geolocation'],
        'extra_http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    }
    if context_options:
        options.update(context_options)

    context = shared_browser.new_context(**options)
    page = context.new_page()
    
    # 根据参数决定是否应用反检测脚本
    if apply_stealth:
        apply_stealth_and_defaults(page)
    else:
        # 只设置超时，不应用反检测脚本
        try:
            page.set_default_timeout(30000)
        except Exception:
            pass
    
    return context, page

def teardown_context_page(context: Any, page: Any) -> None:
    """Close Page and Context, ignoring errors."""
    try:
        page.close()
    except Exception:
        pass
    try:
        context.close()
    except Exception:
        pass

def apply_stealth_and_defaults(page: Any, default_timeout_ms: int = 30000) -> None:
    """Inject basic stealth scripts and set default timeouts on a Playwright page.

    This function is site-agnostic and safe to call multiple times.
    """
    try:
        page.add_init_script(
            """
            // Hide webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            // Realistic navigator props
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            // Screen size
            Object.defineProperty(screen, 'width', { get: () => 1920 });
            Object.defineProperty(screen, 'height', { get: () => 1080 });
            // Timezone
            Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
                value: function() { return { timeZone: 'Asia/Shanghai' }; }
            });
            """
        )
    except Exception:
        pass
    try:
        page.set_default_timeout(default_timeout_ms)
    except Exception:
        pass

# --- Page operations ---

def try_close_modal_with_selectors(page: Any, selectors: Iterable[str]) -> bool:
    """Try to close a modal by trying a list of selectors. Return True if closed."""
    try:
        for selector in selectors:
            try:
                close_btn = page.query_selector(selector)
                if close_btn and (not hasattr(close_btn, 'is_visible') or close_btn.is_visible()):
                    try:
                        close_btn.click(timeout=3000)
                        return True
                    except Exception:
                        try:
                            close_btn.click(force=True, timeout=2000)
                            return True
                        except Exception:
                            try:
                                page.evaluate("arguments[0].click()", close_btn)
                                return True
                            except Exception:
                                pass
            except Exception:
                continue
    except Exception:
        pass
    return False

def establish_home_session(page: Any, home_url: str, home_modal_selectors: Optional[Iterable[str]] = None, on_detail: Optional[callable] = None) -> None:
    """Visit a site home to warm up cookies and optionally close an initial login modal."""
    try:
        if on_detail:
            try:
                on_detail("正在访问站点首页建立会话...")
            except Exception:
                pass
        page.goto(home_url, wait_until='domcontentloaded', timeout=15000)
        page.wait_for_timeout(random.uniform(2000, 4000))
        try:
            page.mouse.move(random.randint(100, 800), random.randint(100, 400))
            page.wait_for_timeout(random.uniform(500, 1500))
        except Exception:
            pass
        if home_modal_selectors:
            page.wait_for_timeout(random.uniform(500, 1500))
            if try_close_modal_with_selectors(page, home_modal_selectors):
                page.wait_for_timeout(500)
    except Exception:
        pass

def wait_for_selector_stable(page: Any, selector_or_mapping: str | Mapping[str, str], page_type_key: Optional[str] = None, timeout_ms: int = 10000) -> None:
    """Wait for a selector to appear. Accepts direct selector or a mapping by page type key."""
    try:
        selector = selector_or_mapping
        if isinstance(selector_or_mapping, dict):
            key = page_type_key or 'unknown'
            selector = selector_or_mapping.get(key, selector_or_mapping.get('unknown', 'main'))
        page.wait_for_selector(selector, timeout=timeout_ms)
    except Exception:
        pass

def read_page_content_and_title(page: Any, on_detail: Optional[callable] = None) -> tuple[str, Optional[str]]:
    """Read page content and title with lightweight error handling."""
    if on_detail:
        try:
            on_detail("正在获取页面内容...")
        except Exception:
            pass
    html = ""
    title = None
    try:
        html = page.content()
    except Exception:
        html = ""
    try:
        title = page.title()
    except Exception:
        title = None
    return html, title
