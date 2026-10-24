"""Topic Queue to Docs — tool-calling agent.

Reads a queue of topics (one per line in a local file; Google Sheets optional —
see README), writes a long-form article for each, and saves each as its own
document (local .md by default; Google Docs optional).

Tools: read_topics, save_doc.
Env: OPENAI_API_KEY, OPENAI_MODEL (optional).

    python topic_queue_to_docs.py --topics topics.txt --brand "AcmeTravel" --out docs
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from agent_core import Agent, Tool
from common import get_client, get_model


def build_tools(topics_file: Path, out_dir: Path) -> list[Tool]:
    def read_topics() -> list[str]:
        if not topics_file.exists():
            return []
        return [ln.strip() for ln in topics_file.read_text(encoding="utf-8").splitlines()
                if ln.strip()]

    def save_doc(title: str, content: str) -> dict:
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|]', "", title).strip()[:80] or "document"
        path = out_dir / f"{safe}.md"
        path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
        return {"saved": str(path), "chars": len(content)}

    return [
        Tool("read_topics", "Return the list of topics from the queue file.",
             {"type": "object", "properties": {}}, read_topics),
        Tool("save_doc", "Save one article as a document.",
             {"type": "object",
              "properties": {"title": {"type": "string"}, "content": {"type": "string"}},
              "required": ["title", "content"]}, save_doc),
    ]


SYSTEM = """You are a content-queue agent.
1. Call read_topics to get the queue.
2. For EACH topic, write a long-form article and then call save_doc(title, content):
   - at least 2,500-3,000 characters;
   - normal paragraphs, no Markdown symbols inside the body;
   - mention the brand "{brand}" once, in the first paragraph only.
When every topic is saved, reply with a short summary. If the queue is empty, say so."""


def main() -> None:
    p = argparse.ArgumentParser(description="Topic queue to docs agent.")
    p.add_argument("--topics", default="topics.txt")
    p.add_argument("--brand", default="{{CLIENT_BRAND}}")
    p.add_argument("--out", default="docs")
    a = p.parse_args()

    agent = Agent(
        client=get_client(), model=get_model(),
        system=SYSTEM.format(brand=a.brand),
        tools=build_tools(Path(a.topics), Path(a.out)),
        max_steps=60,
    )
    print(agent.run("Process the topic queue now."))


if __name__ == "__main__":
    main()
