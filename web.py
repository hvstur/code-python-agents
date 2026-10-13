"""Shared web helpers used by several agents: page fetching, Serper search,
and lightweight HTML heuristics (CMS / blog / comment form).

These are plain functions; the agent scripts wrap the ones they need as Tools.
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

import requests

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_HEADERS = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return url


def fetch_page(url: str, timeout: int = 10, max_bytes: int = 2_000_000) -> dict:
    """Download a page. Returns status, final URL and truncated HTML."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout, stream=True)
        html = r.raw.read(max_bytes, decode_content=True) or b""
        text = html.decode(r.encoding or "utf-8", errors="ignore")
        return {"url": url, "final_url": r.url, "status": r.status_code,
                "bytes": len(html), "html": text}
    except requests.RequestException as exc:
        return {"url": url, "status": 0, "error": str(exc), "html": ""}


def serper_search(query: str, num: int = 10) -> list[dict]:
    """Google search via the Serper API. Needs SERPER_API_KEY in the env."""
    key = os.environ.get("SERPER_API_KEY")
    if not key:
        return [{"error": "SERPER_API_KEY is not set"}]
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": query, "num": num}, timeout=20,
        )
        r.raise_for_status()
        organic = r.json().get("organic", [])
        return [{"title": o.get("title"), "link": o.get("link"),
                 "snippet": o.get("snippet")} for o in organic]
    except requests.RequestException as exc:
        return [{"error": str(exc)}]


_CMS_SIGNS = {
    "WordPress": ["wp-content", "wp-includes", 'name="generator" content="WordPress'],
    "Ghost": ["content=\"Ghost", "ghost-url"],
    "Blogger": ["blogger.com", "blogspot"],
    "Joomla": ["/media/jui/", "com_content", "Joomla!"],
    "Drupal": ["drupal-settings-json", "/sites/default/files"],
    "Tilda": ["tilda", "tildacdn"],
    "Wix": ["wixstatic.com", "wix-thunderbolt", "X-Wix-"],
}
_COMMENT_SIGNS = ["leave a comment", "post a comment", "write a comment",
                  "add a comment", "comment-form", 'id="comments"',
                  "respond", "reply"]
_REGISTER_SIGNS = ["you must be logged in", "login to comment",
                   "register to comment", "sign in to comment"]
_FORUM_SIGNS = ["phpbb", "vbulletin", "xenforo", "smf", "viewtopic.php"]


def analyze_html(html: str) -> dict:
    """Heuristics for CMS, blog/forum, comment form and registration need."""
    low = html.lower()
    cms = next((name for name, signs in _CMS_SIGNS.items()
                if any(s.lower() in low for s in signs)), "unknown")
    has_comment = any(s in low for s in _COMMENT_SIGNS)
    requires_reg = any(s in low for s in _REGISTER_SIGNS)
    is_forum = any(s in low for s in _FORUM_SIGNS)
    is_blog = ("article:published_time" in low or "/blog/" in low
               or "/post/" in low or cms in ("WordPress", "Ghost", "Blogger"))
    return {"cms": cms, "is_blog": is_blog, "is_forum": is_forum,
            "has_comment_form": has_comment, "requires_registration": requires_reg}
