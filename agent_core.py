"""Minimal tool-calling agent built on the OpenAI Chat Completions API.

An Agent is given a system prompt and a list of Tools (Python callables with a
JSON-schema description). On run(task) the model decides which tools to call,
in what order, until it produces a final text answer or hits max_steps.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict          # JSON schema for the arguments
    handler: Callable[..., Any]

    def spec(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class Agent:
    def __init__(self, client, model: str, system: str, tools: list[Tool],
                 max_steps: int = 25, verbose: bool = True):
        self.client = client
        self.model = model
        self.tools = {t.name: t for t in tools}
        self.messages: list[dict] = [{"role": "system", "content": system}]
        self.max_steps = max_steps
        self.verbose = verbose

    def _log(self, *a):
        if self.verbose:
            print(*a, flush=True)

    def run(self, task: str) -> str:
        self.messages.append({"role": "user", "content": task})
        specs = [t.spec() for t in self.tools.values()]

        for _ in range(self.max_steps):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=specs or None,
                tool_choice="auto" if specs else None,
            )
            msg = resp.choices[0].message
            self.messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                return msg.content or ""

            for call in msg.tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                self._log(f"  -> {name}({_short(args)})")
                tool = self.tools.get(name)
                if tool is None:
                    result: Any = {"error": f"unknown tool: {name}"}
                else:
                    try:
                        result = tool.handler(**args)
                    except Exception as exc:          # tool errors go back to the model
                        result = {"error": str(exc)}
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False)[:6000],
                })

        return "Stopped: reached the maximum number of steps."


def _short(args: dict, limit: int = 120) -> str:
    s = json.dumps(args, ensure_ascii=False)
    return s if len(s) <= limit else s[:limit] + "…"
