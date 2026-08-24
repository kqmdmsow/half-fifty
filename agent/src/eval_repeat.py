"""평가 하네스 공통 — 반복 다수결과 폴백 감지 (#161).

세 평가 스크립트(eval_real_labels·eval_ext_sets·eval_normal_fp)가 같은 문제를
안고 있어 여기로 모은다. 복붙하면 다음에 규칙이 바뀔 때 세 곳을 고쳐야 하고,
실제로 폴백 판정 기준은 이미 한 번 바뀌었다(#163 → #165).

두 가지를 제공한다.

**반복 다수결** — temperature=0인데도 조항 판정이 회차마다 뒤집힌다
(docs/reproducibility.md: 예금약관 24조항 중 1건). Test 40이면 회차마다
1~2건, 정확도로 ±4%p다. 보고용 수치는 3회 이상 반복해 다수결로 확정한다.

**폴백 감지** — `_analyze_clause`는 실패를 '주의/해당 없음'으로 흡수한다.
2026-08-07 AI Hub 실행에서 크레딧이 소진된 뒤 이 폴백이 정상 결과처럼
기록돼 strong 82%라는 오염 수치가 나왔다. 다만 폴백이 전부 사고는 아니다 —
인용 검증(citation_check) 재시도 소진으로 조항 하나가 이따금 폴백하는 것은
정상이다(#165). 그래서 개별 폴백은 세어서 보고하고, **여러 조항이 연속으로
통째 폴백할 때만** API 이상으로 보고 중단한다.
"""

from collections import Counter
from typing import Callable

from src.nodes.analysis import _FALLBACK_EVIDENCE

# 연속으로 이만큼 항목이 통째로(전 회차) 폴백하면 개별 항목 특성이 아니라
# API 이상(크레딧 소진·인증·레이트리밋)으로 간주해 중단한다.
CONSECUTIVE_FULL_FALLBACK_LIMIT = 3


class SystemicFailureDetected(RuntimeError):
    """연속 다수 항목이 통째로 폴백했을 때 즉시 중단시키는 예외.

    평가 하네스에서 이 상태는 데이터가 아니라 사고다 — 계속 돌면 폴백이
    정상 결과로 집계돼 수치가 조용히 오염된다.
    """


def is_fallback(prediction: dict) -> bool:
    """`_analyze_clause`가 실패를 흡수해 내놓은 폴백 응답인지."""
    return prediction.get("risk_evidence") == _FALLBACK_EVIDENCE


def majority(levels: list) -> tuple[str, bool]:
    """회차별 risk_level 다수결. 반환: (확정 level, 과반 없음 여부)."""
    counts = Counter(levels)
    top, n = counts.most_common(1)[0]
    return top, n * 2 <= len(levels)


class RepeatRunner:
    """항목별 N회 실행 → 폴백 제외 → 다수결 확정. 연속 전체 폴백이면 중단.

    호출부는 항목 루프만 갖고, 반복·폴백·다수결 판단은 여기에 맡긴다.

        runner = RepeatRunner(repeats=3)
        for row in rows:
            outcome = runner.run(lambda: _analyze_clause(cid, text), label=cid)
            if outcome.fully_fallback:
                continue          # 정확도 집계에서 제외
            use(outcome.prediction)
        print(runner.summary())
    """

    def __init__(self, repeats: int = 1):
        if repeats < 1:
            raise ValueError("repeats는 1 이상이어야 한다")
        self.repeats = repeats
        self._consecutive_full_fallback = 0
        self.total_attempts = 0
        self.total_fallbacks = 0
        self.fully_fallback_labels: list[str] = []
        self.tie_labels: list[str] = []

    def run(self, call: Callable[[], dict], label: str = "") -> "RepeatOutcome":
        attempts = [call() for _ in range(self.repeats)]
        runs = [p for p in attempts if not is_fallback(p)]
        fallback_count = len(attempts) - len(runs)

        self.total_attempts += len(attempts)
        self.total_fallbacks += fallback_count

        if not runs:
            self._consecutive_full_fallback += 1
            self.fully_fallback_labels.append(label)
            if self._consecutive_full_fallback >= CONSECUTIVE_FULL_FALLBACK_LIMIT:
                raise SystemicFailureDetected(
                    f"최근 항목 {self._consecutive_full_fallback}개가 연속으로 전체 폴백 — "
                    f"API 오류(크레딧 소진·인증·레이트리밋) 가능성이 높다. 원인을 확인한 "
                    f"뒤 재실행할 것."
                )
            return RepeatOutcome(None, [], attempts, False, fallback_count, True)

        self._consecutive_full_fallback = 0  # 유효 응답이 나왔으니 리셋

        # 다수결은 risk_level 기준(폴백 회차 제외). 확정 level을 낸 회차의
        # 예측을 대표로 삼아야 risk_type·근거가 확정 level과 어긋나지 않는다.
        level, tie = majority([p["risk_level"] for p in runs])
        if tie and label:
            self.tie_labels.append(label)
        prediction = next(p for p in runs if p["risk_level"] == level)
        return RepeatOutcome(prediction, runs, attempts, tie, fallback_count, False)

    def summary(self) -> str:
        """리포트 머리말에 넣을 측정 조건 한 줄."""
        if self.repeats == 1:
            base = "조항별 1회 실행 (단발 — 보고용 아님)"
        else:
            base = f"조항별 {self.repeats}회 실행 후 risk_level 다수결"
            base += f" / 과반 없음 {len(self.tie_labels)}건"
        if self.total_attempts:
            pct = self.total_fallbacks / self.total_attempts * 100
            base += f" / 폴백 {self.total_fallbacks}/{self.total_attempts}건 ({pct:.1f}%)"
        if self.fully_fallback_labels:
            base += f" / 전체 폴백으로 집계 제외 {len(self.fully_fallback_labels)}건"
        return base


class RepeatOutcome:
    """한 항목의 반복 실행 결과.

    `fully_fallback`이면 `prediction`이 None이다 — 정답과 대조할 수 없으므로
    호출부는 정확도 분모에서도 빼야 한다.
    """

    __slots__ = ("prediction", "runs", "attempts", "tie", "fallback_count", "fully_fallback")

    def __init__(self, prediction, runs, attempts, tie, fallback_count, fully_fallback):
        self.prediction = prediction
        self.runs = runs
        self.attempts = attempts
        self.tie = tie
        self.fallback_count = fallback_count
        self.fully_fallback = fully_fallback
