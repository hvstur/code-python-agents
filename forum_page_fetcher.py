"""Forum Page Fetcher — small tool-calling agent (prototype).

Reads forum URLs from a local file (one per line; Google Sheets optional) and
fetches each page, recording HTTP status and size to a CSV. This mirrors the
original n8n prototype, where only reading + fetching were implemented (no posting).

Tools: read_urls, fetch_and_record.
Env: OPENAI_API_KEY, OPENAI_MODEL (optional).

    python forum_page_fetcher.py --urls forums.txt --out forums_fetched.csv
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from agent_core import Agent, Tool
from common import get_client, get_model
from web import fetch_page

FIELDS = ["url", "status", "bytes", "checked_at"]


def build_tools(urls_file: Path, out_path: Path) -> list[Tool]:
    def read_urls() -> list[str]:
        if not urls_file.exists():
            return []
        return [ln.strip() for ln in urls_file.read_text(encoding="utf-8").splitlines()
                if ln.strip()]

    def fetch_and_record(url: str) -> dict:
        page = fetch_page(url)
        row = {"url": url, "status": page.get("status"),
               "bytes": page.get("bytes", 0),
               "checked_at": datetime.now().isoformat(timespec="seconds")}
        new = not out_path.exists()
        with out_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow(row)
        return row

    return [
        Tool("read_urls", "Return the list of forum URLs to fetch.",
             {"type": "object", "properties": {}}, read_urls),
        Tool("fetch_and_record", "Fetch one URL and append its status to the CSV.",
             {"type": "object", "properties": {"url": {"type": "string"}},
              "required": ["url"]}, fetch_and_record),
    ]


SYSTEM = """You are a fetch agent (prototype).
1. Call read_urls to get the list.
2. Call fetch_and_record for every URL.
When done, reply with how many succeeded (status 200) and how many failed.
Do not attempt to post anything — this prototype only fetches."""


def main() -> None:
    p = argparse.ArgumentParser(description="Forum page fetcher agent (prototype).")
    p.add_argument("--urls", default="forums.txt")
    p.add_argument("--out", default="forums_fetched.csv")
    a = p.parse_args()

    agent = Agent(
        client=get_client(), model=get_model(),
        system=SYSTEM,
        tools=build_tools(Path(a.urls), Path(a.out)),
        max_steps=80,
    )
    print(agent.run("Fetch all forum pages now."))


if __name__ == "__main__":
    main()
