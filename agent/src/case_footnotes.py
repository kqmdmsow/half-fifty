"""위험 유형별 실제 분쟁 사례 각주 조회 (#91 시그니처 기능 ① 실제 사건 각주).

data/case_footnotes.json은 골든셋(data/real_clause_labels*.csv)의 A등급
(정부·법원 판정) 행 중 사건번호가 검증 가능한 출처만 사람이 직접 검수해
risk_type별로 큐레이션한 정적 테이블이다. LLM 호출도 임베딩 검색도 없는
순수 dict 조회라 신규 환각·오인용 경로가 없다 — 자문의견서가 권고한
"근거를 명시하는 RAG"에 대한 리스크 없는 응답(#91).

**격리 원칙 (#91 최우선 설계 항목)**: 이 모듈의 반환값은 사용자 화면
표시 전용이다. Judge가 채점하는 adapted_results/final_output에는 절대
섞이지 않는다 — persona.py의 translations와 동일한 원칙(state.py
PipelineState.translations 주석 참조). 호출부(main.py, src/stream.py)는
Judge 입력이 이미 조립된 뒤, 응답/이벤트를 프론트로 내보내는 마지막
단계에서만 이 함수를 불러야 한다.
"""

import json
from pathlib import Path
from typing import List, TypedDict

_PATH = Path(__file__).parent.parent.parent / "data" / "case_footnotes.json"
_TABLE: dict = json.loads(_PATH.read_text(encoding="utf-8"))
_TABLE.pop("_readme", None)


class CaseFootnote(TypedDict):
    case_id: str
    agency: str      # 판정 기관 (예: 금융분쟁조정위원회)
    citation: str     # 사건번호·사례 표기 (예: "제2019-18호")
    result: str       # 한 줄 결과 요약
    source: str       # 골든셋 내부 출처 (감사 추적용, 화면 표시 불필요)
    grade: str        # 라벨 등급 ("A"만 큐레이션 대상)


def get_related_cases(risk_type: str) -> List[CaseFootnote]:
    """risk_type에 매핑된 큐레이션 사례 목록 (없으면 빈 리스트).

    "해당 없음"이거나 테이블에 없는 유형(v1 미커버: 신탁관계·소유권
    불안정 고지, 선택권 제한·구입 강제, 보증금 반환 지연)은 빈 리스트를
    반환한다 — 틀린 사건번호를 보여주는 것보다 안 보여주는 게 낫다는
    원칙(#91).
    """
    return _TABLE.get(risk_type, [])
