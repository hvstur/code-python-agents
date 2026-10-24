# n8n workflows as Python AI agents

Python re-implementations of my n8n workflows, written as **tool-calling agents**:
a small shared agent loop (`agent_core.py`) gives an LLM a set of tools, and the
model decides which tools to call, in what order, until the task is done.

[Описание на русском](#на-русском)

## Agents

| Script | What it does | Tools | External service |
| --- | --- | --- | --- |
| `gaming_article_desk.py` | Search gaming news, pick topics, write and save articles with one in-context link | search_news, save_article | OpenAI, Serper |
| `blog_comment_prospecting.py` | Find blogs with an open comment form, classify them, save prospects with a status | serper_search, analyze_site, save_result | OpenAI, Serper |
| `bulk_article_generator.py` | Generate a batch of plain-text placement articles, one brand mention each | save_article | OpenAI |
| `topic_queue_to_docs.py` | Read a topic queue, write a long article per topic, save each as a document | read_topics, save_doc | OpenAI |
| `forum_page_fetcher.py` | Prototype: fetch a list of forum pages and record HTTP status | read_urls, fetch_and_record | OpenAI |
| `telegram_content_bot.py` | Interactive Telegram bot (inline buttons, per-chat state, LLM generation) | — (interactive bot) | OpenAI, Telegram |

`telegram_content_bot.py` is an interactive bot, not a tool-calling agent — the
LLM is used for the generation step. `forum_page_fetcher.py` is a thin prototype
(matches the original workflow, which had no posting step).

## Shared modules

- `agent_core.py` — the tool-calling loop (`Agent`, `Tool`).
- `common.py` — OpenAI client and model from environment.
- `web.py` — page fetch, Serper search, and CMS / comment-form heuristics.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env     # then fill in the keys
# load the variables (bash):
export $(grep -v '^#' .env | xargs)
```

Keys are read from the environment; nothing is hard-coded.

## Run

```bash
python gaming_article_desk.py --topics 3 --language english --anchor "best project management tools" --url "https://example.com"
python blog_comment_prospecting.py --niches "travel,home improvement" --out prospects.csv
python bulk_article_generator.py --count 5 --brand "AcmeTravel" --niche "travel"
python topic_queue_to_docs.py --topics topics.txt --brand "AcmeTravel"
python forum_page_fetcher.py --urls forums.txt
python telegram_content_bot.py
```

## Storage note (local vs Google)

The storage tools write locally by default (`.txt`, `.md`, `.csv`) so everything runs
with just an OpenAI key. The original workflows used Google Sheets / Docs / Drive; to
use those, replace the `save_*` / `read_*` tool bodies with `google-api-python-client`
calls and a service-account credential (`GOOGLE_APPLICATION_CREDENTIALS`).

## На русском

Python-версии моих n8n-воркфлоу, написанные как **агенты с tool-calling**: общий
цикл агента (`agent_core.py`) даёт модели набор инструментов, и она сама решает,
какие из них и в каком порядке вызывать, пока задача не выполнена.

Ключи берутся из переменных окружения, в коде их нет. По умолчанию результаты
сохраняются локально (файлы и CSV), чтобы всё работало с одним ключом OpenAI;
версии с Google Sheets/Docs/Drive подключаются заменой тел `save_*`/`read_*`-инструментов.
`telegram_content_bot.py` — интерактивный бот (LLM используется на шаге генерации),
`forum_page_fetcher.py` — прототип без шага публикации, как и в оригинале.
