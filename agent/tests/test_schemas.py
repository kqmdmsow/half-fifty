"""LLM 출력 스키마 검증 테스트 — 실측된 이탈 패턴 기반."""
import pytest
from pydantic import ValidationError

from src.schemas import AnalysisOutput

_BASE = {"explanation": "설명", "risk_level": "위험",
         "risk_type": "책임 면제", "risk_evidence": "근거",
         "check_questions": ["질문1"]}


def test_valid_output_passes():
    out = AnalysisOutput.model_validate(_BASE)
    assert out.risk_type == "책임 면제"


def test_list_risk_type_takes_first():
    # 실측: 10유형 확장 후 다중 유형 리스트 반환 빈도 증가
    out = AnalysisOutput.model_validate({**_BASE, "risk_type": ["책임 면제", "권리행사 제한"]})
    assert out.risk_type == "책임 면제"


def test_numbered_prefix_stripped():
    # 실측: Solar 전량 측정에서 "10. 권리행사 제한" 변형 관측
    out = AnalysisOutput.model_validate({**_BASE, "risk_type": "10. 권리행사 제한"})
    assert out.risk_type == "권리행사 제한"


def test_invalid_risk_level_raises():
    with pytest.raises(ValidationError):
        AnalysisOutput.model_validate({**_BASE, "risk_level": "높음"})


def test_string_check_questions_promoted_to_list():
    out = AnalysisOutput.model_validate({**_BASE, "check_questions": "질문 하나"})
    assert out.check_questions == ["질문 하나"]


def test_empty_explanation_raises():
    with pytest.raises(ValidationError):
        AnalysisOutput.model_validate({**_BASE, "explanation": "  "})


def test_missing_field_raises():
    bad = dict(_BASE); del bad["risk_evidence"]
    with pytest.raises(ValidationError):
        AnalysisOutput.model_validate(bad)
