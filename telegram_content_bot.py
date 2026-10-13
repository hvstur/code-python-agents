"""Telegram content bot — Python version of the n8n Telegram workflow.

This one is an interactive bot, not a tool-calling agent: the user picks a text
type and language with inline buttons, sends a topic, and the bot generates the
text with an LLM and sends it back (splitting messages over 4096 chars).
Per-chat dialog state is kept in memory.

Env: TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, OPENAI_MODEL (optional).

    python telegram_content_bot.py
"""

from __future__ import annotations

import os
import sys
import time

import requests

from common import get_client, get_model

TYPES = {"blog": "Blog article", "landing": "Landing page", "web2": "Web 2.0 article"}
LANGS = ["English", "Español", "Deutsch", "Français", "Čeština", "Italiano"]

SYSTEM_BY_TYPE = {
    "blog": "Write a 600-900 word blog article with an intro, subheadings and a conclusion.",
    "landing": "Write a landing page: a headline, short paragraphs, benefit bullets and a call to action.",
    "web2": "Write a 300-500 word Web 2.0 article in a friendly tone; work the topic in without keyword stuffing.",
}

state: dict[int, dict] = {}       # chat_id -> {"step","type","lang"}


class TG:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"

    def call(self, method: str, **params):
        r = requests.post(f"{self.base}/{method}", json=params, timeout=65)
        return r.json()

    def get_updates(self, offset: int):
        return self.call("getUpdates", offset=offset, timeout=50).get("result", [])


def kb(buttons: list[tuple[str, str]], per_row: int = 2) -> dict:
    rows, row = [], []
    for text, data in buttons:
        row.append({"text": text, "callback_data": data})
        if len(row) == per_row:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return {"inline_keyboard": rows}


def send_long(tg: TG, chat_id: int, text: str):
    for i in range(0, len(text), 4096):
        tg.call("sendMessage", chat_id=chat_id, text=text[i:i + 4096])


def generate(client, model: str, ttype: str, lang: str, topic: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_BY_TYPE[ttype]},
                  {"role": "user", "content": f"Language: {lang}. Topic: {topic}"}],
    )
    return (resp.choices[0].message.content or "").strip()


def handle_update(tg: TG, client, model: str, upd: dict):
    # Button press
    if "callback_query" in upd:
        cq = upd["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        data = cq["data"]
        tg.call("answerCallbackQuery", callback_query_id=cq["id"])
        st = state.setdefault(chat_id, {})
        if data.startswith("type:"):
            st["type"] = data.split(":", 1)[1]
            st["step"] = "ask_lang"
            tg.call("sendMessage", chat_id=chat_id, text="Choose a language:",
                    reply_markup=kb([(l, f"lang:{l}") for l in LANGS], per_row=3))
        elif data.startswith("lang:"):
            st["lang"] = data.split(":", 1)[1]
            st["step"] = "ask_topic"
            tg.call("sendMessage", chat_id=chat_id,
                    text="Send me the topic or keywords in one message.")
        return

    # Text message
    msg = upd.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = msg.get("text", "")
    if chat_id is None:
        return

    if text.startswith("/start"):
        state[chat_id] = {"step": "ask_type"}
        tg.call("sendMessage", chat_id=chat_id, text="What type of text do you need?",
                reply_markup=kb([(v, f"type:{k}") for k, v in TYPES.items()], per_row=1))
        return

    st = state.get(chat_id, {})
    if st.get("step") == "ask_topic" and text:
        tg.call("sendMessage", chat_id=chat_id, text="Generating, one moment…")
        try:
            out = generate(client, model, st["type"], st["lang"], text)
        except Exception as exc:
            tg.call("sendMessage", chat_id=chat_id, text=f"Error: {exc}")
            return
        send_long(tg, chat_id, out)
        state[chat_id] = {"step": "ask_type"}
        tg.call("sendMessage", chat_id=chat_id, text="Another one? Send /start.")
    else:
        tg.call("sendMessage", chat_id=chat_id, text="Send /start to begin.")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("ERROR: set TELEGRAM_BOT_TOKEN before running.")
    tg = TG(token)
    client, model = get_client(), get_model()
    print("Bot running (long polling). Press Ctrl+C to stop.")
    offset = 0
    while True:
        try:
            for upd in tg.get_updates(offset):
                offset = upd["update_id"] + 1
                handle_update(tg, client, model, upd)
        except KeyboardInterrupt:
            print("\nStopped."); break
        except Exception as exc:
            print("loop error:", exc); time.sleep(3)


if __name__ == "__main__":
    main()
