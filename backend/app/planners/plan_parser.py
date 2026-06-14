from __future__ import annotations

import json
import re
from typing import Any


def parse_plan_json(text: str | None) -> dict[str, Any] | None:
    if not text or not str(text).strip():
        return None

    payload = str(text).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", payload, flags=re.DOTALL)
    if fenced:
        payload = fenced.group(1).strip()

    try:
        data = json.loads(payload)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start = payload.find("{")
        end = payload.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            data = json.loads(payload[start : end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
