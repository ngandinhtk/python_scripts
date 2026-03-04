import json
import os
import re
from typing import Optional, List, Dict, Any

from thefuzz import fuzz


_CANNED_RESPONSES_CACHE: List[Dict[str, Any]] = []
_CANNED_RESPONSES_PATH = "canned_responses.json"
_DEFAULT_THRESHOLD = 80


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _load_canned_responses() -> List[Dict[str, Any]]:
    global _CANNED_RESPONSES_CACHE
    if _CANNED_RESPONSES_CACHE:
        return _CANNED_RESPONSES_CACHE

    if not os.path.exists(_CANNED_RESPONSES_PATH):
        return []

    try:
        with open(_CANNED_RESPONSES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                _CANNED_RESPONSES_CACHE = data
    except Exception as e:
        print(f"Loi doc {_CANNED_RESPONSES_PATH}: {e}")
        return []

    return _CANNED_RESPONSES_CACHE


def find_canned_response(user_message: str) -> Optional[str]:
    """
    Tim cau tra loi san trong file local JSON.

    Format moi item:
    {
      "keywords": ["xin chao", "chao ban", "..."],
      "response": "..."
    }
    """
    items = _load_canned_responses()
    if not items:
        return None

    message = _normalize_text(user_message)

    for item in items:
        keywords = item.get("keywords", [])
        response = item.get("response")
        threshold = int(item.get("threshold", _DEFAULT_THRESHOLD))
        if not keywords or not response:
            continue

        for raw_keyword in keywords:
            keyword = _normalize_text(str(raw_keyword))
            if not keyword:
                continue

            if keyword in message:
                return response

            score = fuzz.partial_ratio(keyword, message)
            if score >= threshold:
                return response

    return None
