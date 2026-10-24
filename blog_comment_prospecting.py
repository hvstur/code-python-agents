"""Blog Comment Prospecting — tool-calling agent.

For each niche the agent builds search footprints, searches via Serper,
analyses each unique domain (CMS, blog/forum, comment form, registration),
and saves sites that have an open comment form, with a status:
ready_to_contact (open form, no registration) or needs_review.

Results are written to a local CSV by default (Google Sheets optional — see README).
Tools: serper_search, analyze_site, save_result.
Env: OPENAI_API_KEY, SERPER_API_KEY, OPENAI_MODEL (optional).

    python blog_comment_prospecting.py --niches "travel,home improvement" --out results.csv
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from agent_core import Agent, Tool
from common import get_client, get_model
from web import analyze_html, domain_of, fetch_page, serper_search

FIELDS = ["url", "cms", "has_comment_form", "requires_registration",
          "niche", "status", "checked_at"]


def build_tools(out_path: Path) -> list[Tool]:
    seen: set[str] = set()

    def _search(query: str) -> list[dict]:
        return serper_search(query, num=10)

    def analyze_site(url: str) -> dict:
        dom = domain_of(url)
        if dom in seen:
            return {"url": url, "skip": "domain already analysed"}
        seen.add(dom)
        page = fetch_page(url)
        if page.get("status") != 200 or not page.get("html"):
            return {"url": url, "status": page.get("status"),
                    "error": page.get("error", "no content")}
        verdict = analyze_html(page["html"])
        verdict["url"] = url
        return verdict

    def save_result(url: str, cms: str, has_comment_form: bool,
                    requires_registration: bool, niche: str, status: str) -> dict:
        new = not out_path.exists()
        with out_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow({"url": url, "cms": cms, "has_comment_form": has_comment_form,
                        "requires_registration": requires_registration, "niche": niche,
                        "status": status, "checked_at": datetime.now().isoformat(timespec="seconds")})
        return {"saved": url, "status": status}

    return [
        Tool("serper_search", "Google search; returns title, link, snippet.",
             {"type": "object", "properties": {"query": {"type": "string"}},
              "required": ["query"]}, _search),
        Tool("analyze_site",
             "Fetch a URL and detect CMS, blog/forum, comment form, registration need. "
             "Skips domains already analysed.",
             {"type": "object", "properties": {"url": {"type": "string"}},
              "required": ["url"]}, analyze_site),
        Tool("save_result", "Save a prospect row to the results file.",
             {"type": "object",
              "properties": {"url": {"type": "string"}, "cms": {"type": "string"},
                             "has_comment_form": {"type": "boolean"},
                             "requires_registration": {"type": "boolean"},
                             "niche": {"type": "string"}, "status": {"type": "string"}},
              "required": ["url", "cms", "has_comment_form",
                           "requires_registration", "niche", "status"]},
             save_result),
    ]


SYSTEM = """You are a link-prospecting agent.
For each niche in: {niches}
1. Build 2-3 search footprints, e.g. '"powered by wordpress" "leave a comment" <niche> blog'.
2. Call serper_search for each footprint.
3. For each unique result domain, call analyze_site.
4. If it has a comment form, call save_result:
   - status "ready_to_contact" when has_comment_form is true AND requires_registration is false;
   - otherwise "needs_review".
Skip pages with no comment form. Work through all niches, then reply with a short summary
(how many saved, how many ready_to_contact)."""


def main() -> None:
    p = argparse.ArgumentParser(description="Blog comment prospecting agent.")
    p.add_argument("--niches", default="travel,home improvement")
    p.add_argument("--out", default="prospects.csv")
    a = p.parse_args()

    agent = Agent(
        client=get_client(), model=get_model(),
        system=SYSTEM.format(niches=a.niches),
        tools=build_tools(Path(a.out)),
        max_steps=60,
    )
    print(agent.run(f"Start prospecting for: {a.niches}"))


if __name__ == "__main__":
    main()
