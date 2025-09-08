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
    success_count = 0
    
    for finished in asyncio.as_completed(tasks):
        try:
            url, ok = await finished
        except Exception:
            # 理论上不会到这里，因为 _wrapped_download 已吃异常
            url, ok = ("", False)
        if url:
            results[url] = bool(ok)
        done_count += 1
        if ok:
            success_count += 1
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
            loop = asyncio.get_running_loop()
            # 如果已有事件循环，使用线程池执行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, download_all())
                download_results = future.result()
        except RuntimeError:
            # 没有事件循环，直接运行
            download_results = asyncio.run(download_all())
        
        # 处理下载失败的情况，更新文件扩展名
        for i, (url, local_path, _) in enumerate(image_tasks):
            if download_results.get(url, False):
                # 下载成功，检查是否需要更新扩展名
                if local_path.endswith('.img'):
                    try:
                        with open(local_path, 'rb') as f:
                            header = f.read(10)
                            if header.startswith(b'\xff\xd8\xff'):
                                new_path = local_path.replace('.img', '.jpg')
                                os.rename(local_path, new_path)
                                # 更新url_to_local中的路径
                                for key, value in url_to_local.items():
                                    if key == url:
                                        url_to_local[key] = value.replace('.img', '.jpg')
                            elif header.startswith(b'\x89PNG'):
                                new_path = local_path.replace('.img', '.png')
                                os.rename(local_path, new_path)
                                for key, value in url_to_local.items():
                                    if key == url:
                                        url_to_local[key] = value.replace('.img', '.png')
                    except Exception:
                        pass  # 如果检测失败，保持原扩展名

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


