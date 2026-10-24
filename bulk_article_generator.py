"""Bulk Article Generator — tool-calling agent.

Produces a batch of plain-text articles for crowd / Web 2.0 placements and saves
each as a separate file. The brand is mentioned exactly once per article.

Tools: save_article.
Env: OPENAI_API_KEY, OPENAI_MODEL (optional).

    python bulk_article_generator.py --count 5 --brand "AcmeTravel" --niche "travel"

Note: the original n8n workflow defaulted to 312 per run. Keep --count small while
testing; each article is a separate model call.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from agent_core import Agent, Tool
from common import get_client, get_model


def build_tools(out_dir: Path) -> list[Tool]:
    counter = {"n": 0}

    def save_article(content: str) -> dict:
        out_dir.mkdir(parents=True, exist_ok=True)
        counter["n"] += 1
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = out_dir / f"article_{counter['n']:03d}_{stamp}.txt"
        path.write_text(content, encoding="utf-8")
        return {"saved": str(path), "index": counter["n"], "chars": len(content)}

    return [
        Tool("save_article", "Save one finished article to a .txt file.",
             {"type": "object", "properties": {"content": {"type": "string"}},
              "required": ["content"]}, save_article),
    ]


SYSTEM = """You are a bulk content agent for the {niche} niche.
Produce exactly {count} DISTINCT articles. For each one:
- pick a popular, specific sub-topic (bonuses, slots, live dealer, crypto payments,
  mobile apps, etc.) — do not repeat sub-topics;
- 800-1,500 words, plain text only (no Markdown, hashtags or bullet symbols);
- intro, 2-3 sections, conclusion; no keyword stuffing;
- mention the brand "{brand}" exactly once in the whole article;
- then call save_article with the text.
After {count} articles are saved, reply with a one-line summary."""


def main() -> None:
    p = argparse.ArgumentParser(description="Bulk article generator agent.")
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--brand", default="{{CLIENT_BRAND}}")
    p.add_argument("--niche", default="travel")
    p.add_argument("--out", default="articles")
    a = p.parse_args()

    agent = Agent(
        client=get_client(), model=get_model(),
        system=SYSTEM.format(count=max(1, a.count), brand=a.brand, niche=a.niche),
        tools=build_tools(Path(a.out)),
        max_steps=3 + a.count * 2,
    )
    print(agent.run(f"Generate {a.count} articles now."))


if __name__ == "__main__":
    main()
