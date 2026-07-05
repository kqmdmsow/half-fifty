"""파이프라인 데모: 샘플 계약서로 4단계 파이프라인 한 바퀴 실행.

사용법:
    cd agent
    source .venv/bin/activate
    python demo.py
"""

import json

from src.graph import run_pipeline

SAMPLE_CONTRACT = """
제1조(목적) 이 계약은 임대인과 임차인 간의 주택 임대차에 관한 사항을 정함을 목적으로 한다.

제2조(보증금) 임차인은 보증금 2억원을 계약 체결 시 임대인에게 지급한다. 임대인은 계약 종료 후 3개월 이내에 보증금을 반환할 수 있다.

제3조(계약 해지) 임대인은 필요하다고 판단되는 경우 언제든지 본 계약을 해지할 수 있다.

특약사항
1. 임차인이 계약을 중도 해지하는 경우 보증금의 30%를 위약금으로 지급한다.
2. 시설물 하자에 대하여 임대인은 일체의 책임을 지지 않는다.
"""


def main() -> None:
    result = run_pipeline(SAMPLE_CONTRACT, persona="senior")

    print("=" * 60)
    print(f"조항 수: {len(result['clauses'])}")
    print(f"재시도 횟수: {result['retry_count']}")
    print(f"주의 필요 플래그: {result['needs_review']}")
    print(f"Judge 점수: {json.dumps(result['judge_scores'], ensure_ascii=False)}")
    print("=" * 60)

    for r in result["adapted_results"]:
        print(f"\n[{r['clause_id']}] 위험도: {r['risk_level']} / 유형: {r['risk_type']}")
        print(f"  설명: {r['explanation']}")
        print(f"  근거: {r['risk_evidence']}")
        print(f"  질문: {r['check_questions']}")


if __name__ == "__main__":
    main()
