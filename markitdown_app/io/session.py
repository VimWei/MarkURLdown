from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_requests_session(ignore_ssl: bool, no_proxy: bool) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    if no_proxy:
        session.trust_env = False
    if ignore_ssl:
        session.verify = False
    session.headers.update({
        "User-Agent": "MarkItDown/Refactor (+https://github.com/microsoft/markitdown)",
    })
    return session


