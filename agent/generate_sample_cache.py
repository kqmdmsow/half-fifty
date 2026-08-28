"""데모 샘플 사전 분석 캐시 생성 — 원클릭 즉시 결과.

frontend/src/data/sampleTexts.json의 텍스트 샘플 6종을 실제 파이프라인으로
분석해, REST /analyze 응답과 **정확히 같은 형태**(AnalyzeResponse)로
frontend/src/data/sampleResults.json 에 {샘플id: 응답} 으로 저장한다.

- 응답 조립은 main._state_to_response를 그대로 재사용한다 — 조립 로직을
  복제하면 캐시와 실분석 결과의 필드가 어긋나 '자세히 보기'(evidence_spans·
  related_cases 등)가 캐시에서만 깨질 수 있다.
- 언어는 ko 고정(프론트 캐시는 ko 화면에서만 쓰인다), 페르소나는 샘플
  지정값 또는 adult, 도메인은 샘플 값을 그대로 전달한다.

실패 시 빈 캐시로 되돌리는 이유: 파이프라인은 API 오류(크레딧 소진 등)를
조항별 폴백(analysis_failed)으로 삼켜 exit 0으로 끝난다 — 그 결과를 캐시로
구우면 "분석 실패" 카드를 심사위원에게 즉시 결과라고 보여주게 된다. 그래서
① 시작 전 최소 호출로 API 상태를 사전 점검하고(회로 차단), ② 샘플마다
폴백 마커·needs_review를 검사해 하나라도 걸리면 부분 캐시 없이 {}로
되돌린다. 프론트는 캐시가 비면 기존 실분석 경로로 폴백하므로 안전하다.

사용법:
    cd agent
    source .venv/bin/activate
    python generate_sample_cache.py
"""

import json
import sys
import time
from pathlib import Path

from main import _state_to_response
from src.graph import run_pipeline
from src.llm import get_worker_llm

ROOT = Path(__file__).resolve().parent.parent
TEXTS_PATH = ROOT / "frontend" / "src" / "data" / "sampleTexts.json"
RESULTS_PATH = ROOT / "frontend" / "src" / "data" / "sampleResults.json"


def _abort(reason: str) -> int:
    """부분/오염 캐시를 남기지 않고 빈 객체로 되돌린 뒤 실패 종료."""
    RESULTS_PATH.write_text("{}\n", encoding="utf-8")
    print(f"캐시 생성 실패: {reason}")
    print("sampleResults.json을 {}로 되돌렸습니다 — 프론트는 실분석 경로로 폴백합니다.")
    return 1


def _preflight() -> str | None:
    """본 실행 전 최소 호출 1회로 API 상태 점검. 이상이면 사유 반환."""
    try:
        get_worker_llm().invoke("ping")
    except Exception as exc:  # noqa: BLE001 — 사유를 그대로 보고
        return f"{type(exc).__name__}: {exc}"
    return None


def main() -> int:
    samples = json.loads(TEXTS_PATH.read_text(encoding="utf-8"))

    if reason := _preflight():
        return _abort(f"API 사전 점검 실패 — {reason}")

    cache: dict[str, dict] = {}
    started = time.perf_counter()
    for sample in samples:
        t0 = time.perf_counter()
        try:
            state = run_pipeline(
                sample["text"],
                persona=sample.get("persona", "adult"),
                language="ko",
                domain=sample.get("domain", ""),
            )
            response = _state_to_response(state)
        except Exception as exc:  # noqa: BLE001
            return _abort(f"[{sample['id']}] {type(exc).__name__}: {exc}")

        # 폴백이 섞인 결과는 캐시 부적격 — 재시도 소진(needs_review)도 심사용
        # 사전 결과로는 굽지 않는다 (재실행이 맞는 처방).
        failed = [r.clause_id for r in response.results if r.analysis_failed]
        if failed:
            return _abort(f"[{sample['id']}] 조항 분석 폴백 발생: {failed}")
        if response.needs_review:
            return _abort(f"[{sample['id']}] needs_review=True — Judge 게이트 미통과")

        cache[sample["id"]] = response.model_dump()
        print(f"[{sample['id']}] 조항 {response.clause_count}개, "
              f"retry {response.retry_count}, {time.perf_counter() - t0:.1f}s")

    RESULTS_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    size_kb = RESULTS_PATH.stat().st_size / 1024
    print(f"총 {len(cache)}건 -> {RESULTS_PATH} "
          f"({size_kb:.0f}KB, {time.perf_counter() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
