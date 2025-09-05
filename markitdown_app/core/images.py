from __future__ import annotations

import os
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse


def download_images_and_rewrite(md_text: str, base_url: str, images_dir: str, session, should_stop: callable | None = None, on_detail: callable | None = None) -> str:
    os.makedirs(images_dir, exist_ok=True)

    # Match markdown images; be tolerant of titles/angles/spaces: ![alt](URL [title])
    pattern_md = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    # also support inline HTML <img src="..."> inside markdown
    pattern_html = re.compile(r"<img[^>]+src=\"([^\"]+)\"[^>]*>", re.IGNORECASE)
    url_to_local: dict[str, str] = {}
    counter = 1
    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    matches = list(pattern_md.finditer(md_text)) + list(pattern_html.finditer(md_text))
    total = len(matches)
    if total > 0 and on_detail:
        on_detail(f"发现 {total} 张图片，开始下载…")

    def replace_md(match: re.Match) -> str:
        nonlocal counter
        if should_stop and should_stop():
            return match.group(0)

        raw = match.group(1)
        # take first token as URL; strip surrounding <>, quotes
        src = raw.strip().split()[0].strip('<>"\'')
        if src.startswith("data:"):
            return match.group(0)
        if src.startswith("//"):
            base_scheme = urlparse(base_url).scheme or "https"
            src = f"{base_scheme}:{src}"
        resolved = urljoin(base_url, src)
        if resolved in url_to_local:
            local_rel = url_to_local[resolved]
        else:
            parsed = urlparse(resolved)
            _, ext = os.path.splitext(os.path.basename(parsed.path))
            if not ext:
                ext = ".img"
            local_name = f"{run_stamp}_{counter:03d}{ext}"
            counter += 1
            local_path = os.path.join(images_dir, local_name)
            try:
                extra_headers = {}
                host = parsed.netloc.lower()
                if ("mp.weixin.qq.com" in host) or host.endswith(".qpic.cn") or ("weixin" in host) or ("wechat" in host):
                    extra_headers.update({
                        "Referer": base_url,
                        "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0"),
                        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                    })
                with session.get(resolved, stream=True, timeout=20, headers=extra_headers or None) as r:
                    r.raise_for_status()
                    if ext == ".img":
                        ctype = r.headers.get("Content-Type", "").lower()
                        if "/" in ctype:
                            subtype = ctype.split("/", 1)[1].split(";", 1)[0].strip()
                            mapping = {
                                "jpeg": ".jpg",
                                "jpg": ".jpg",
                                "png": ".png",
                                "gif": ".gif",
                                "webp": ".webp",
                                "svg+xml": ".svg",
                                "bmp": ".bmp",
                            }
                            guess_ext = mapping.get(subtype)
                            if guess_ext:
                                local_name = f"{run_stamp}_{counter-1:03d}{guess_ext}"
                                local_path = os.path.join(images_dir, local_name)
                    with open(local_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                local_rel = f"{os.path.basename(images_dir)}/{local_name}"
                url_to_local[resolved] = local_rel
            except Exception:
                return match.group(0)

        alt_match = re.search(r"!\[([^\]]*)\]", match.group(0))
        alt_text = alt_match.group(1) if alt_match else ""
        if total > 0 and on_detail:
            on_detail(f"下载图片 {counter-1}/{total}")
        return f"![{alt_text}]({local_rel})"

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
        on_detail("图片下载完成，正在保存文件…")
    return result_text


