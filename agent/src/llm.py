"""LLM 클라이언트 생성 및 JSON 응답 파싱 공통 유틸.

Analysis/Persona/Judge 세 노드가 이 모듈을 통해서만 LLM을 호출한다.
"""

import json
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

DEFAULT_MODEL_WORKER = "claude-haiku-4-5"
DEFAULT_MODEL_JUDGE = "claude-sonnet-4-6"


@lru_cache(maxsize=None)
def get_worker_llm() -> ChatAnthropic:
    """Analysis/Persona 등 생성 작업용 LLM (.env의 MODEL_WORKER, 기본 Haiku)."""
    model = os.getenv("MODEL_WORKER", DEFAULT_MODEL_WORKER)
    return ChatAnthropic(model=model, temperature=0)


@lru_cache(maxsize=None)
def get_judge_llm() -> ChatAnthropic:
    """Judge 채점용 LLM (.env의 MODEL_JUDGE, 기본 Sonnet)."""
    model = os.getenv("MODEL_JUDGE", DEFAULT_MODEL_JUDGE)
    return ChatAnthropic(model=model, temperature=0)


def invoke_json(llm: ChatAnthropic, prompt: str) -> dict:
    """LLM을 호출하고 응답 텍스트를 JSON 객체로 파싱해 반환한다."""
    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return _extract_json(content)


def _extract_json(text: str) -> dict:
    """```json 코드펜스 유무와 무관하게 첫 { ~ 마지막 } 구간을 파싱한다."""
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"응답에서 JSON 객체를 찾을 수 없습니다: {text[:200]!r}")
    return json.loads(text[start : end + 1])
