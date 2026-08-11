"""LLM 클라이언트 생성 및 JSON 응답 파싱 공통 유틸.

Analysis/Persona/Judge 세 노드가 이 모듈을 통해서만 LLM을 호출한다.
"""

import json
import os
import threading
from functools import lru_cache

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

load_dotenv()

DEFAULT_MODEL_WORKER = "claude-haiku-4-5"
DEFAULT_MODEL_JUDGE = "claude-sonnet-4-6"

# 파이프라인 1회 실행 단위의 대략적 토큰 사용량 누적 (eval.py 등에서 사용).
# 조항 병렬 분석 도입으로 여러 스레드가 동시에 갱신하므로 락으로 보호한다.
_token_usage = {"input_tokens": 0, "output_tokens": 0}
_token_lock = threading.Lock()


def reset_token_usage() -> None:
    """토큰 사용량 누적치를 0으로 초기화한다."""
    _token_usage["input_tokens"] = 0
    _token_usage["output_tokens"] = 0


def get_token_usage() -> dict:
    """마지막 reset_token_usage() 이후 누적된 토큰 사용량을 반환한다."""
    return dict(_token_usage)


# API 응답이 멈춘 채 안 돌아오는 경우(2026-08-05/06 각각 3.5시간/2시간 관측)를
# 막기 위한 호출당 타임아웃. langchain-anthropic은 max_retries 기본값이 2라
# timeout과 함께 두면 한 번 멈춰도 최대 REQUEST_TIMEOUT_SEC * 3초 내에
# 타임아웃 예외로 끝나고, 호출부(analysis.py 등)의 기존 재시도/폴백 로직으로
# 넘어간다.
REQUEST_TIMEOUT_SEC = 90


@lru_cache(maxsize=None)
def get_worker_llm() -> ChatAnthropic:
    """Analysis/Persona 등 생성 작업용 LLM (.env의 MODEL_WORKER, 기본 Haiku)."""
    model = os.getenv("MODEL_WORKER", DEFAULT_MODEL_WORKER)
    return ChatAnthropic(model=model, temperature=0, timeout=REQUEST_TIMEOUT_SEC)


@lru_cache(maxsize=None)
def get_judge_llm() -> ChatAnthropic:
    """Judge 채점용 LLM (.env의 MODEL_JUDGE, 기본 Sonnet)."""
    model = os.getenv("MODEL_JUDGE", DEFAULT_MODEL_JUDGE)
    return ChatAnthropic(model=model, temperature=0, timeout=REQUEST_TIMEOUT_SEC)


def invoke_json(llm: ChatAnthropic, prompt: str, cached_prefix: str | None = None) -> dict:
    """LLM을 호출하고 응답 텍스트를 JSON 객체로 파싱해 반환한다.

    cached_prefix를 주면 그 부분을 Anthropic 프롬프트 캐시(ephemeral) 블록으로
    보낸다 — 조항마다 반복되는 정적 프롬프트(위험 유형 정의·앵커 예시)를 캐시해
    두 번째 호출부터 입력 토큰 비용을 크게 줄인다. 프리픽스가 모델별 캐시 최소
    토큰(하이쿠 2048 등)에 못 미치면 API가 조용히 무시하므로 무해하다.
    주의: cached_prefix는 호출 간 완전히 동일해야 캐시가 적중한다.
    """
    if cached_prefix is not None:
        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": cached_prefix,
                    "cache_control": {"type": "ephemeral"},
                },
                {"type": "text", "text": prompt},
            ]
        )
        response = llm.invoke([message])
    else:
        response = llm.invoke(prompt)

    usage = getattr(response, "usage_metadata", None) or {}
    with _token_lock:
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
