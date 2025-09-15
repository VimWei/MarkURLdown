from __future__ import annotations

import os
import re
import asyncio
import aiohttp
import hashlib
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import Optional, Callable, Dict, Tuple

# =============================================================================
# 域名配置区域 - 统一管理所有图片域名规则
# =============================================================================

class ImageDomainConfig:
    """图片域名配置类，统一管理各种域名的处理规则"""
    
    # 需要格式检测的域名（这些域名的图片可能没有正确的文件扩展名）
    FORMAT_DETECTION_DOMAINS = {
        # 知乎图片域名 - 使用通配符匹配
        'zhimg.com': 'wildcard',  # 匹配 *.zhimg.com
        # 微信图片CDN
        'qpic.cn': 'exact',
        'mmbiz.qpic.cn': 'exact',
    }
    
    # 通常格式正确的CDN域名（不需要格式检测）
    RELIABLE_CDN_PREFIXES = [
        'cdn.',
        'static.',
        'assets.',
        'img.',
        'images.',
    ]
    
    @classmethod
    def should_detect_format(cls, host: str) -> bool:
        """判断域名是否需要格式检测"""
        host = host.lower()
        
        for domain, match_type in cls.FORMAT_DETECTION_DOMAINS.items():
            if match_type == 'exact' and host == domain:
                return True
            elif match_type == 'wildcard' and (host == domain or host.endswith('.' + domain)):
                return True
        
        return False
    
    @classmethod
    def is_reliable_cdn(cls, host: str) -> bool:
        """判断是否是可靠的CDN域名"""
        host = host.lower()
        return any(host.startswith(prefix) for prefix in cls.RELIABLE_CDN_PREFIXES)

def _convert_github_url(url: str) -> str:
    """将GitHub的旧格式URL转换为新格式，避免重定向问题"""
    if "github.com" in url and "/raw/" in url:
        # 将 github.com/username/repo/raw/branch/path 转换为 raw.githubusercontent.com/username/repo/branch/path
        new_url = url.replace("github.com", "raw.githubusercontent.com").replace("/raw/", "/")
        return new_url
    return url

def _detect_image_format_from_header(content: bytes) -> str:
    """从文件头检测图片格式"""
    if len(content) < 8:
        return ''

    header = content[:20]

    # 检测各种图片格式的文件头
    if header.startswith(b'\xff\xd8\xff'):
        return '.jpg'  # JPEG
    elif header.startswith(b'\x89PNG'):
        # PNG格式检测：标准文件头是 89 50 4E 47 0D 0A 1A 0A (8字节)
        # 但实际文件中可能只有前4字节的PNG标识，后面4字节可能不同
        if len(content) >= 4:
            # 检查PNG文件头的前4字节：89 50 4E 47
            if content[:4] == b'\x89PNG':
                return '.png'
    elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
        return '.gif'  # GIF
    elif header.startswith(b'RIFF') and len(header) >= 12 and header[8:12] == b'WEBP':
        return '.webp'  # WebP
    elif header.startswith(b'BM'):
        return '.bmp'  # BMP
    elif header.startswith(b'II*\x00') or header.startswith(b'MM\x00*'):
        return '.tiff'  # TIFF
    elif header.startswith(b'<svg') or header.startswith(b'<SVG') or b'<svg' in header.lower():
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

    # 使用统一的域名配置进行检测
    if ImageDomainConfig.should_detect_format(host):
        return True

    # 对于没有扩展名的图片，采用保守策略
    # 只对已知可能有问题的模式进行检测
    if not any(ext in path for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
        # 检查是否是可靠的CDN域名
        if ImageDomainConfig.is_reliable_cdn(host):
            return False

        # 对于其他没有扩展名的图片，暂时不检测（保守策略）
        # 如果发现新的问题站点，可以添加到 ImageDomainConfig.FORMAT_DETECTION_DOMAINS 中
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
                                extra_headers: Optional[Dict[str, str]] = None,
                                hash_to_path: Optional[Dict[str, str]] = None,
                                hash_lock: Optional[asyncio.Lock] = None) -> tuple[bool, str]:
    """异步下载单张图片（流式计算SHA-256，基于内容精确去重）。

    返回 (success, final_local_path)。当命中去重时，final_local_path 为已存在文件路径。
    """
    try:
        # 转换GitHub URL以避免重定向问题
        converted_url = _convert_github_url(url)
        if converted_url != url:
            print(f"转换GitHub URL: {url} -> {converted_url}")

        timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
        async with session.get(converted_url, headers=extra_headers, timeout=timeout) as response:
            if response.status == 200:
                # 以 .part 临时文件写入，边写边算哈希
                temp_path = local_path + ".part"
                hasher = hashlib.sha256()
                try:
                    with open(temp_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(65536):
                            if not chunk:
                                continue
                            hasher.update(chunk)
                            f.write(chunk)
                    file_hash = hasher.hexdigest()
                    # 去重检查
                    if hash_to_path is not None and hash_lock is not None:
                        async with hash_lock:
                            existed = hash_to_path.get(file_hash)
                            if existed:
                                # 已存在同内容文件，删除临时文件并复用
                                try:
                                    os.remove(temp_path)
                                except Exception:
                                    pass
                                return True, existed
                            else:
                                # 首次出现，落盘为目标文件
                                try:
                                    os.replace(temp_path, local_path)
                                except Exception:
                                    # 回退到重命名失败的复制路径
                                    try:
                                        os.rename(temp_path, local_path)
                                    except Exception:
                                        # 实在失败也不影响流程
                                        pass
                                hash_to_path[file_hash] = local_path
                                return True, local_path
                    # 无去重上下文，直接落盘
                    try:
                        os.replace(temp_path, local_path)
                    except Exception:
                        try:
                            os.rename(temp_path, local_path)
                        except Exception:
                            pass
                    return True, local_path
                except Exception as e:
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except Exception:
                        pass
                    print(f"下载图片写入失败: {converted_url}, 错误: {e}")
                    return False, local_path
            else:
                print(f"下载图片失败: {converted_url}, 状态码: {response.status}")
                return False, local_path
    except asyncio.TimeoutError:
        print(f"下载图片超时: {converted_url}")
        return False, local_path
    except Exception as e:
        print(f"下载图片异常: {converted_url}, 错误: {e}")
        return False, local_path

async def _download_images_async(image_tasks: list[Tuple[str, str, Optional[Dict[str, str]]]],
                                session: aiohttp.ClientSession,
                                on_detail: Optional[Callable[[str], None]] = None,
                                hash_to_path: Optional[Dict[str, str]] = None,
                                hash_lock: Optional[asyncio.Lock] = None) -> Dict[str, Tuple[bool, str]]:
    """异步并发下载所有图片，并动态汇报进度；返回 {url: (ok, final_local_path)}"""
    if not image_tasks:
        return {}

    total = len(image_tasks)
    if on_detail:
        on_detail({"key": "images_dl_init", "data": {"total": total}})

    # 创建下载任务；每个任务返回 (url, success)
    async def _wrapped_download(url: str, local_path: str, headers: Optional[Dict[str, str]]):
        try:
            ok, final_path = await _download_single_image(session, url, local_path, headers, hash_to_path, hash_lock)
            return url, bool(ok), final_path
        except Exception:
            return url, False, local_path

    tasks: list[asyncio.Task] = []
    for url, local_path, headers in image_tasks:
        task = asyncio.create_task(_wrapped_download(url, local_path, headers))
        tasks.append(task)

    results: Dict[str, Tuple[bool, str]] = {}
    done_count = 0

    for finished in asyncio.as_completed(tasks):
        try:
            url, ok, final_path = await finished
        except Exception:
            # 理论上不会到这里
            url, ok, final_path = ("", False, "")
        if url:
            results[url] = (bool(ok), final_path)
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
                               on_detail: Optional[Callable[[str], None]] = None,
                               enable_compact_rename: bool = False,
                               timestamp: Optional[datetime] = None) -> str:
    """下载图片并重写markdown文本（使用异步并发下载）
    
    Args:
        md_text: 包含图片链接的markdown文本
        base_url: 基础URL，用于解析相对链接
        images_dir: 图片保存目录
        session: HTTP会话对象
        should_stop: 可选的停止检查函数
        on_detail: 可选的进度回调函数
        enable_compact_rename: 是否启用紧凑重命名（默认False，保留原始文件名便于调试）
        timestamp: 可选的时间戳，用于统一markdown和图片文件名的时间戳
    
    Returns:
        重写后的markdown文本，图片链接替换为本地路径
    """
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
    url_to_planned_local: Dict[str, str] = {}  # 计划中的URL到本地文件映射
    counter = 1
    # 使用传入的时间戳，如果没有则使用当前时间
    run_stamp = (timestamp or datetime.now()).strftime("%Y%m%d_%H%M%S")

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

        if resolved not in url_to_planned_local:
            parsed = urlparse(resolved)
            _, ext = os.path.splitext(os.path.basename(parsed.path))
            
            # 对于需要格式检测的域名，统一使用.img扩展名，后续会根据实际内容重命名
            if _should_detect_image_format(resolved):
                ext = ".img"
            elif not ext:
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
            url_to_planned_local[resolved] = f"{os.path.basename(images_dir)}/{local_name}"

    # 异步并发下载所有图片
    if image_tasks:
        async def download_all():
            # 创建aiohttp会话
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)  # 限制并发连接数
            async with aiohttp.ClientSession(connector=connector) as aio_session:
                # 每篇文章内的去重索引
                hash_to_path: Dict[str, str] = {}
                hash_lock = asyncio.Lock()
                return await _download_images_async(image_tasks, aio_session, on_detail, hash_to_path, hash_lock)

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

        # 根据下载结果建立最终的URL到本地文件映射
        # 关键修复：只有下载成功的图片才建立映射，避免失败图片被其他图片占用
        url_to_local: Dict[str, str] = {}
        for url, local_path, _ in image_tasks:
            ok, final_local_path = download_results.get(url, (False, local_path))
            if ok:
                # 只有下载成功的图片才建立映射
                url_to_local[url] = f"{os.path.basename(images_dir)}/{os.path.basename(final_local_path)}"
        
        # 条件性图片格式检测：只对特定域名进行格式检测
        # 同时根据最终落盘路径更新 url_to_local（可能因去重而指向其他文件）
        for url, local_path, _ in image_tasks:
            ok, final_local_path = download_results.get(url, (False, local_path))
            if ok and final_local_path.endswith('.img'):
                # 检查是否需要格式检测（基于域名）
                if _should_detect_image_format(url):
                    detected_ext = _detect_image_format_from_file(final_local_path)
                    if detected_ext and detected_ext != '.img':
                        # 重命名文件并更新路径映射
                        new_path = final_local_path.replace('.img', detected_ext)
                        try:
                            os.rename(final_local_path, new_path)
                            # 更新url_to_local中的路径
                            old_name = os.path.basename(final_local_path)
                            new_name = os.path.basename(new_path)
                            if url in url_to_local:
                                url_to_local[url] = url_to_local[url].replace(old_name, new_name)
                        except Exception as e:
                            print(f"重命名图片文件失败: {e}")

        # 事后紧凑重命名：按文章内首次出现顺序为"唯一图片文件"重新分配连续序号
        # 默认禁用，保留原始文件名以便调试和问题诊断
        if enable_compact_rename:
            try:
                # 收集按出现顺序的去重后的目标文件（相对路径）
                # 只处理成功下载的图片
                ordered_unique_rel: list[str] = []
                seen_files: set[str] = set()
                for match in matches:
                    raw = match.group(1)
                    src = raw.strip().split()[0].strip('<>"\'')
                    if src.startswith("data:"):
                        continue
                    if src.startswith("//"):
                        base_scheme = urlparse(base_url).scheme or "https"
                        src = f"{base_scheme}:{src}"
                    resolved = urljoin(base_url, src)
                    rel = url_to_local.get(resolved)  # 只有成功下载的图片才会在url_to_local中
                    if not rel:
                        continue
                    if rel not in seen_files:
                        seen_files.add(rel)
                        ordered_unique_rel.append(rel)

                # 计算目标名称映射 old_rel -> new_rel（保持扩展名，且仅对实际存在的文件连续编号）
                rel_rename_map: Dict[str, str] = {}
                new_index = 1
                for rel in ordered_unique_rel:
                    basename = os.path.basename(rel)
                    old_abs = os.path.join(images_dir, basename)
                    if not os.path.exists(old_abs):
                        # 文件不存在，跳过且不消耗序号，避免出现断号
                        continue
                    _, ext = os.path.splitext(basename)
                    if not ext:
                        ext = ".img"
                    new_basename = f"{run_stamp}_{new_index:03d}{ext}"
                    new_index += 1
                    dirname = os.path.basename(images_dir)
                    new_rel = f"{dirname}/{new_basename}"
                    if new_rel != rel:
                        rel_rename_map[rel] = new_rel

                if rel_rename_map:
                    # 第一阶段：全部改为临时名，避免目标名冲突
                    tmp_suffix = ".reseq.tmp"
                    tmp_paths: Dict[str, str] = {}
                    for old_rel, new_rel in rel_rename_map.items():
                        old_abs = os.path.join(images_dir, os.path.basename(old_rel))
                        if not os.path.exists(old_abs):
                            continue
                        tmp_abs = old_abs + tmp_suffix
                        try:
                            os.replace(old_abs, tmp_abs)
                            tmp_paths[old_rel] = tmp_abs
                        except Exception:
                            pass

                    # 第二阶段：从临时名移动到最终名，并更新映射
                    for old_rel, new_rel in rel_rename_map.items():
                        tmp_abs = tmp_paths.get(old_rel)
                        if not tmp_abs or not os.path.exists(tmp_abs):
                            continue
                        final_abs = os.path.join(images_dir, os.path.basename(new_rel))
                        try:
                            os.replace(tmp_abs, final_abs)
                        except Exception:
                            try:
                                os.rename(tmp_abs, final_abs)
                            except Exception:
                                pass
                    # 更新所有 URL 映射为新相对路径
                    for url, rel in list(url_to_local.items()):
                        url_to_local[url] = rel_rename_map.get(rel, rel)
            except Exception as e:
                print(f"图片紧凑重命名失败: {e}")

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
