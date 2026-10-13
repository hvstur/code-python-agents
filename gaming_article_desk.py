"""Gaming Article Desk — tool-calling agent.

The agent searches fresh gaming news, picks concrete topics, writes a
style-controlled article for each (one natural in-context link), and saves it.

Tools: search_news, save_article.
Env: OPENAI_API_KEY, SERPER_API_KEY (for search), OPENAI_MODEL (optional).

    python gaming_article_desk.py --topics 3 --language english \
        --anchor "best crypto casinos" --url "https://example.com"
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

from agent_core import Agent, Tool
from common import get_client, get_model
from web import serper_search


def build_tools(out_dir: Path) -> list[Tool]:
    def search_news(query: str) -> list[dict]:
        return serper_search(f"{query} news", num=10)

    def save_article(filename: str, content: str) -> dict:
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|]', "", filename).strip()[:80] or "article"
        path = out_dir / f"{safe}.txt"
        path.write_text(content, encoding="utf-8")
        return {"saved": str(path), "chars": len(content)}

    return [
        Tool("search_news",
             "Search recent news for a query. Returns title, link, snippet.",
             {"type": "object",
              "properties": {"query": {"type": "string"}},
              "required": ["query"]},
             search_news),
        Tool("save_article",
             "Save a finished article to a .txt file.",
             {"type": "object",
              "properties": {"filename": {"type": "string",
                                          "description": "Short name without extension"},
                             "content": {"type": "string"}},
              "required": ["filename", "content"]},
             save_article),
    ]


SYSTEM = """You are a gaming content agent.
Workflow:
1. Call search_news with 1-2 queries to find fresh, specific angles
   (patches, releases, events, tournaments).
2. Choose {n} concrete, non-promotional topics in {language}.
3. For EACH topic, write an article yourself and then call save_article:
   - 2,500-3,500 characters, varied rhythm, a first-person opinion, concrete details;
   - no clichés, at most one bullet list;
   - exactly ONE link: anchor "{anchor}" to {url}, placed naturally in the middle
     (never the first or last paragraph).
When all {n} articles are saved, reply with a short summary."""


def main() -> None:
    p = argparse.ArgumentParser(description="Gaming Article Desk agent.")
    p.add_argument("--topics", type=int, default=3)
    p.add_argument("--language", default="english")
    p.add_argument("--anchor", default="1111")
    p.add_argument("--url", default="https://example.com")
    p.add_argument("--out", default="articles")
    a = p.parse_args()

    agent = Agent(
        client=get_client(), model=get_model(),
        system=SYSTEM.format(n=max(1, a.topics), language=a.language,
                             anchor=a.anchor, url=a.url),
        tools=build_tools(Path(a.out)),
        max_steps=4 + a.topics * 3,
    )
    print(agent.run(f"Produce {a.topics} article(s) now. Timestamp: "
                    f"{datetime.now():%Y-%m-%d %H:%M}."))


if __name__ == "__main__":
    main()
