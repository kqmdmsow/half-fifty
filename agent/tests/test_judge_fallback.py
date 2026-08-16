"""judge_node의 JSON 파싱 실패 폴백 테스트 (PR#18에서 지적된 사각지대 수정).

invoke_json이 깨진 응답을 반환해도 예외가 파이프라인 전체를 죽이지 않고,
analysis.py와 동일하게 1회 재시도 후 낮은 점수로 폴백하는지 확인한다.
"""
from unittest.mock import patch

from src.nodes import judge


def _base_state():
    return {
        "clauses": [{"clause_id": "clause_001", "text": "임차인은 보증금을 낸다."}],
        "adapted_results": [{"clause_id": "clause_001", "explanation": "설명"}],
        "persona": "adult",
    }


def test_judge_falls_back_after_repeated_parse_failure():
    with patch.object(judge, "invoke_json", side_effect=ValueError("깨진 JSON")):
        scores = judge._judge(_base_state())
    assert scores["clarity"] == judge._FALLBACK_SCORE
    assert scores["faithfulness"] == judge._FALLBACK_SCORE
    assert scores["rationale"]["clarity"] == judge._FALLBACK_RATIONALE


def test_judge_recovers_on_second_attempt():
    good_response = {
        aspect: {"score": 4.0, "rationale": "정상 채점"} for aspect in judge._ASPECTS
    }
    with patch.object(judge, "invoke_json", side_effect=[ValueError("1차 실패"), good_response]):
        scores = judge._judge(_base_state())
    assert scores["clarity"] == 4.0
    assert scores["rationale"]["clarity"] == "정상 채점"


def test_judge_fallback_triggers_gate_failure():
    # 폴백 점수가 실제로 게이트(FAITHFULNESS_MIN·JUDGE_THRESHOLD)를 못 넘기는지 확인
    from src.state import FAITHFULNESS_MIN, JUDGE_THRESHOLD

    assert judge._FALLBACK_SCORE < FAITHFULNESS_MIN
    assert judge._FALLBACK_SCORE < JUDGE_THRESHOLD
