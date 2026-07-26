"""LLM 클라이언트 생성 및 JSON 응답 파싱 공통 유틸.

Analysis/Persona/Judge 세 노드가 이 모듈을 통해서만 LLM을 호출한다.

2026-07-26: 비용 절감을 위해 Claude(Anthropic)에서 Gemini 무료 티어(Google AI
Studio)로 전환. GOOGLE_API_KEY만 있으면 과금 없이 실행 가능 — 무료 티어 호출량
한도는 https://ai.google.dev/gemini-api/docs/rate-limits 참고.
"""

import json
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

DEFAULT_MODEL_WORKER = "gemini-2.0-flash"
DEFAULT_MODEL_JUDGE = "gemini-2.5-flash"

# 파이프라인 1회 실행 단위의 대략적 토큰 사용량 누적 (eval.py 등에서 사용).
_token_usage = {"input_tokens": 0, "output_tokens": 0}


def reset_token_usage() -> None:
    """토큰 사용량 누적치를 0으로 초기화한다."""
    _token_usage["input_tokens"] = 0
    _token_usage["output_tokens"] = 0


def get_token_usage() -> dict:
    """마지막 reset_token_usage() 이후 누적된 토큰 사용량을 반환한다."""
    return dict(_token_usage)


@lru_cache(maxsize=None)
def get_worker_llm() -> ChatGoogleGenerativeAI:
    """Analysis/Persona 등 생성 작업용 LLM (.env의 MODEL_WORKER, 기본 Gemini Flash)."""
    model = os.getenv("MODEL_WORKER", DEFAULT_MODEL_WORKER)
    return ChatGoogleGenerativeAI(model=model, temperature=0)


@lru_cache(maxsize=None)
def get_judge_llm() -> ChatGoogleGenerativeAI:
    """Judge 채점용 LLM (.env의 MODEL_JUDGE, 기본 Gemini Flash)."""
    model = os.getenv("MODEL_JUDGE", DEFAULT_MODEL_JUDGE)
    return ChatGoogleGenerativeAI(model=model, temperature=0)


def invoke_json(llm: ChatGoogleGenerativeAI, prompt: str) -> dict:
    """LLM을 호출하고 응답 텍스트를 JSON 객체로 파싱해 반환한다."""
    response = llm.invoke(prompt)

    usage = getattr(response, "usage_metadata", None) or {}
    _token_usage["input_tokens"] += usage.get("input_tokens", 0)
    _token_usage["output_tokens"] += usage.get("output_tokens", 0)

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
