from __future__ import annotations

import os
import re
import asyncio
import aiohttp
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import Optional, Callable, Dict, Tuple

def _convert_github_url(url: str) -> str:
    """将GitHub的旧格式URL转换为新格式，避免重定向问题"""
    if "github.com" in url and "/raw/" in url:
        # 将 github.com/username/repo/raw/branch/path 转换为 raw.githubusercontent.com/username/repo/branch/path
        new_url = url.replace("github.com", "raw.githubusercontent.com").replace("/raw/", "/")
        return new_url
    return url

def _detect_image_format_from_header(content: bytes) -> str:
    """从文件头检测图片格式"""
    if len(content) < 20:
        return ''

    header = content[:20]

    # 检测各种图片格式的文件头
    if header.startswith(b'\xff\xd8\xff'):
        return '.jpg'  # JPEG
    elif header.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'  # PNG
    elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
        return '.gif'  # GIF
    elif header.startswith(b'RIFF') and len(header) >= 12 and header[8:12] == b'WEBP':
        return '.webp'  # WebP
    elif header.startswith(b'BM'):
        return '.bmp'  # BMP
    elif header.startswith(b'II*\x00') or header.startswith(b'MM\x00*'):
        return '.tiff'  # TIFF
    elif header.startswith(b'<svg') or b'<svg' in header:
        return '.svg'  # SVG
    elif header.startswith(b'\x00\x00\x01\x00') or header.startswith(b'\x00\x00\x02\x00'):
        return '.ico'  # ICO

    return ''

def _should_detect_image_format(url: str) -> bool:
    """判断是否需要对指定URL的图片进行格式检测"""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    # 只对已知有格式问题的域名进行检测
    problematic_domains = [
        'zhimg.com',  # 知乎图片
        'pic.zhimg.com',  # 知乎图片
    ]

    # 检查是否是问题域名
    if any(domain in host for domain in problematic_domains):
        return True

    # 对于没有扩展名的图片，采用保守策略
    # 只对已知可能有问题的模式进行检测
    if not any(ext in path for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
        # 微信图片：不需要检测（格式正确）
        if 'qpic.cn' in host or 'mmbiz.qpic.cn' in host:
            return False

        # 其他常见CDN和API：通常格式正确，不需要检测
        if any(cdn in host for cdn in ['cdn.', 'static.', 'assets.', 'img.', 'images.']):
            return False

        # 对于其他没有扩展名的图片，暂时不检测（保守策略）
        # 如果发现新的问题站点，可以添加到上面的problematic_domains中
        return False

    return False

def _detect_image_format_from_file(file_path: str) -> str:
    """从本地文件检测图片格式"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(20)
            return _detect_image_format_from_header(header)
    except Exception:
        return ''

async def _download_single_image(session: aiohttp.ClientSession, url: str, local_path: str,
                                extra_headers: Optional[Dict[str, str]] = None) -> bool:
    """异步下载单张图片"""
    try:
        # 转换GitHub URL以避免重定向问题
        converted_url = _convert_github_url(url)
        if converted_url != url:
            print(f"转换GitHub URL: {url} -> {converted_url}")

        timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
        async with session.get(converted_url, headers=extra_headers, timeout=timeout) as response:
            if response.status == 200:
                content = await response.read()
                with open(local_path, "wb") as f:
                    f.write(content)
                return True
            else:
                print(f"下载图片失败: {converted_url}, 状态码: {response.status}")
                return False
    except asyncio.TimeoutError:
        print(f"下载图片超时: {converted_url}")
        return False
    except Exception as e:
        print(f"下载图片异常: {converted_url}, 错误: {e}")
        return False

async def _download_images_async(image_tasks: list[Tuple[str, str, Optional[Dict[str, str]]]],
                                session: aiohttp.ClientSession,
                                on_detail: Optional[Callable[[str], None]] = None) -> Dict[str, bool]:
    """异步并发下载所有图片，并动态汇报进度"""
    if not image_tasks:
        return {}

    total = len(image_tasks)
    if on_detail:
        on_detail({"key": "images_dl_init", "data": {"total": total}})

    # 创建下载任务；每个任务返回 (url, success)
    async def _wrapped_download(url: str, local_path: str, headers: Optional[Dict[str, str]]):
        try:
            ok = await _download_single_image(session, url, local_path, headers)
            return url, bool(ok)
        except Exception:
            return url, False

    tasks: list[asyncio.Task] = []
    for url, local_path, headers in image_tasks:
        task = asyncio.create_task(_wrapped_download(url, local_path, headers))
        tasks.append(task)

    results: Dict[str, bool] = {}
    done_count = 0

    for finished in asyncio.as_completed(tasks):
        try:
            url, ok = await finished
        except Exception:
            # 理论上不会到这里
            url, ok = ("", False)
        if url:
            results[url] = bool(ok)
        done_count += 1
        if on_detail:
            # 动态更新为统一前缀+百分比（无小数点）
            percent = int(done_count * 100 / total)
            on_detail({"key": "images_dl_progress", "data": {"total": total, "percent": percent}})

    if on_detail:
        on_detail({"key": "images_dl_done", "data": {"total": total}})

    return results

def download_images_and_rewrite(md_text: str, base_url: str, images_dir: str, session,
                               should_stop: Optional[Callable[[], bool]] = None,
                               on_detail: Optional[Callable[[str], None]] = None) -> str:
    """下载图片并重写markdown文本（使用异步并发下载）"""
    os.makedirs(images_dir, exist_ok=True)

    # Match markdown images; be tolerant of titles/angles/spaces: ![alt](URL [title])
    pattern_md = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    # also support inline HTML <img src="..."> inside markdown
    pattern_html = re.compile(r"<img[^>]+src=\"([^\"]+)\"[^>]*>", re.IGNORECASE)

    matches = list(pattern_md.finditer(md_text)) + list(pattern_html.finditer(md_text))
    total = len(matches)
    if total == 0:
        return md_text

    if on_detail:
        on_detail({"key": "images_found_start", "data": {"count": total}})

    # 收集所有需要下载的图片信息
    image_tasks = []
    url_to_local: Dict[str, str] = {}
    counter = 1
    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for match in matches:
        if should_stop and should_stop():
            break

        raw = match.group(1)
        # take first token as URL; strip surrounding <>, quotes
        src = raw.strip().split()[0].strip('<>"\'')
        if src.startswith("data:"):
            continue
        if src.startswith("//"):
            base_scheme = urlparse(base_url).scheme or "https"
            src = f"{base_scheme}:{src}"
        resolved = urljoin(base_url, src)

        if resolved not in url_to_local:
            parsed = urlparse(resolved)
            _, ext = os.path.splitext(os.path.basename(parsed.path))
            if not ext:
                ext = ".img"
            local_name = f"{run_stamp}_{counter:03d}{ext}"
            counter += 1
            local_path = os.path.join(images_dir, local_name)

            # 准备请求头
            extra_headers = {}
            host = parsed.netloc.lower()
            if ("mp.weixin.qq.com" in host) or host.endswith(".qpic.cn") or ("weixin" in host) or ("wechat" in host):
                extra_headers.update({
                    "Referer": base_url,
                    "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0"),
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                })

            image_tasks.append((resolved, local_path, extra_headers))
            url_to_local[resolved] = f"{os.path.basename(images_dir)}/{local_name}"

    # 异步并发下载所有图片
    if image_tasks:
        async def download_all():
            # 创建aiohttp会话
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)  # 限制并发连接数
            async with aiohttp.ClientSession(connector=connector) as aio_session:
                return await _download_images_async(image_tasks, aio_session, on_detail)

        # 检查是否已有事件循环
        try:
            asyncio.get_running_loop()
            # 如果已有事件循环，使用线程池执行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, download_all())
                download_results = future.result()
        except RuntimeError:
            # 没有事件循环，直接运行
            download_results = asyncio.run(download_all())

        # 条件性图片格式检测：只对特定域名进行格式检测
        for url, local_path, _ in image_tasks:
            if download_results.get(url, False) and local_path.endswith('.img'):
                # 检查是否需要格式检测（基于域名）
                if _should_detect_image_format(url):
                    detected_ext = _detect_image_format_from_file(local_path)
                    if detected_ext and detected_ext != '.img':
                        # 重命名文件并更新路径映射
                        new_path = local_path.replace('.img', detected_ext)
                        try:
                            os.rename(local_path, new_path)
                            # 更新url_to_local中的路径
                            for key, value in url_to_local.items():
                                if key == url:
                                    url_to_local[key] = value.replace('.img', detected_ext)
                        except Exception as e:
                            print(f"重命名图片文件失败: {e}")

    # 替换markdown中的图片链接
    def replace_md(match: re.Match) -> str:
        raw = match.group(1)
        src = raw.strip().split()[0].strip('<>"\'')
        if src.startswith("data:"):
            return match.group(0)
        if src.startswith("//"):
            base_scheme = urlparse(base_url).scheme or "https"
            src = f"{base_scheme}:{src}"
        resolved = urljoin(base_url, src)

        if resolved in url_to_local:
            local_rel = url_to_local[resolved]
            alt_match = re.search(r"!\[([^\]]*)\]", match.group(0))
            alt_text = alt_match.group(1) if alt_match else ""
            return f"![{alt_text}]({local_rel})"
        else:
            return match.group(0)

    # First replace markdown images
    result_text = pattern_md.sub(replace_md, md_text)
    # Then replace HTML img tags
    def replace_html(m: re.Match) -> str:
        fake_md = f"![]({m.group(1)})"
        rewritten = pattern_md.sub(replace_md, fake_md)
        # extract path back
        new_src = re.search(r"!\[[^\]]*\]\(([^)]+)\)", rewritten)
        return m.group(0).replace(m.group(1), new_src.group(1) if new_src else m.group(1))

    result_text = pattern_html.sub(replace_html, result_text)
    if total > 0 and on_detail:
        on_detail({"key": "images_dl_saving"})
    return result_text
