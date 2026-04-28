"""Tiny text helpers used by prompt rendering and JSON extraction."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping


_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def render_prompt(template: str, variables: Mapping[str, Any]) -> str:
    """Replace `{{var}}` tokens. Missing vars become an empty string.

    We avoid Jinja to keep deps minimal; the surface we need is single-level
    string substitution.
    """

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        value = variables.get(key, "")
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    return _PLACEHOLDER.sub(_sub, template)


_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> dict:
    """Best-effort JSON extraction from an LLM response.

    Many models wrap JSON in ```json ... ``` fences or add prose around it.
    We try direct parse first, then fall back to the first balanced-looking
    object.
    """

    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))

    match = _JSON_OBJECT.search(text)
    if match:
        return json.loads(match.group(0))

    raise ValueError("No JSON object found in LLM response.")
