"""Shared setup: OpenAI client and default model, both from environment."""

from __future__ import annotations

import os
import sys


def get_model(default: str = "gpt-4o") -> str:
    return os.environ.get("OPENAI_MODEL", default)


def get_client():
    """Return an OpenAI client, or exit with a clear message."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("ERROR: set the OPENAI_API_KEY environment variable before running.")
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("ERROR: the 'openai' package is missing. Run: pip install -r requirements.txt")
    return OpenAI(api_key=key)
