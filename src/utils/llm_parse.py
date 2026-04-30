from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict | list:
    """LLM 응답 텍스트에서 JSON 추출.

    1. markdown fence 제거
    2. 첫 { 또는 [ 부터 마지막 } 또는 ] 까지 추출
    3. json.loads 시도

    Raises:
        ValueError: JSON 추출/파싱 실패 시.
    """
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    start_obj = text.find("{")
    start_arr = text.find("[")

    if start_obj == -1 and start_arr == -1:
        raise ValueError(f"No JSON found in LLM response: {text[:200]}")

    if start_arr == -1 or (start_obj != -1 and start_obj < start_arr):
        end = text.rfind("}")
        if end == -1:
            raise ValueError(f"No closing brace in LLM response: {text[:200]}")
        candidate = text[start_obj : end + 1]
    else:
        end = text.rfind("]")
        if end == -1:
            raise ValueError(f"No closing bracket in LLM response: {text[:200]}")
        candidate = text[start_arr : end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse failed: {e}\nCandidate: {candidate[:300]}") from e
