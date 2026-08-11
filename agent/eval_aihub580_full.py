"""AI Hub 580 정제본 전량 측정 — 고유 조항 5,782행 실행 후 전 10,200행에 전파.

목적 (docs/related_work_and_new_sources.md 사용 계획 ③):
1. 대규모 정합성: 파이프라인 판정 vs AI Hub 유불리 라벨 일치도 (n=10,200 전수)
2. 분야(25종)·신호등급(tier)·패턴별 성능 프로파일
3. 불일치 사례 전수 확보 → 라벨 오류/모델 약점/신유형 발굴 재료

주의: C급 라벨이므로 불일치 ≠ 모델 오류. strong(심결 인정) 서브셋만 준공식 지표.
체크포인트(JSONL)로 중단 안전 — 재실행 시 이어서 돈다.

사용법: cd agent && python eval_aihub580_full.py
"""

import csv
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import argparse
import os
import time

from src.llm import get_worker_llm, invoke_json
from src.nodes.analysis import _PROMPT_TEMPLATE


def get_llm(model_key: str):
    """worker 모델 선택 — claude(제품 기본) 또는 무료 대안. 결과 파일은 모델별 분리."""
    if model_key == "claude":
        return get_worker_llm()
    if model_key == "solar":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=os.getenv("MODEL_WORKER_SOLAR", "solar-pro3"),
                          temperature=0, base_url="https://api.upstage.ai/v1",
                          api_key=os.getenv("UPSTAGE_API_KEY"), max_retries=0)
    if model_key == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0)
    raise ValueError(model_key)

BASE = Path(__file__).parent.parent / "data" / "raw" / "sources_research" / "aihub580"
IN_CSV = BASE / "aihub580_cleaned.csv"
# 모델별 파일 분리 (main에서 확정)
CKPT = OUT_CSV = OUT_MD = None

_MAX_WORKERS = 4
_lock = threading.Lock()


def norm_key(t: str) -> str:
    return re.sub(r"[\s0-9①-⑮제조항()\.]+", "", t)[:120]


def main() -> None:
    global CKPT, OUT_CSV, OUT_MD
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["claude", "solar", "gemini"], default="claude")
    ap.add_argument("--subset", choices=["all", "strong"], default="all",
                    help="strong: 공정위 심결 인정 행만 실행 (프롬프트 개선 재측정용)")
    ap.add_argument("--tag", default="", help="결과 파일 태그 (예: v2) — 이전 실행과 분리")
    args = ap.parse_args()
    suffix = "" if args.model == "claude" else f"_{args.model}"
    if args.tag:
        suffix += f"_{args.tag}"
    CKPT = BASE / f"aihub580_full_run_checkpoint{suffix}.jsonl"
    OUT_CSV = BASE / f"aihub580_full_run_results{suffix}.csv"
    OUT_MD = Path(__file__).parent.parent / "docs" / f"eval_aihub580_full_run{suffix}.md"
    print(f"worker 모델: {args.model} / subset: {args.subset} / tag: {args.tag or '(없음)'}")

    rows = list(csv.DictReader(open(IN_CSV, encoding="utf-8")))
    if args.subset == "strong":
        rows = [r for r in rows if r["label_tier"] == "strong"]
        print(f"strong 서브셋만: {len(rows)}행")
    uniq: dict[str, str] = {}
    for r in rows:
        uniq.setdefault(norm_key(r["clause_text"]), r["clause_text"])
    print(f"전체 {len(rows)}행 / 고유 조항 {len(uniq)}건")

    done: dict[str, dict] = {}
    if CKPT.exists():
        for line in open(CKPT, encoding="utf-8"):
            rec = json.loads(line)
            done[rec["key"]] = rec
        print(f"체크포인트 {len(done)}건 로드 — 이어서 실행")

    todo = [(k, t) for k, t in uniq.items() if k not in done]
    print(f"실행 대상 {len(todo)}건 (workers={_MAX_WORKERS})")

    ckpt_f = open(CKPT, "a", encoding="utf-8")
    counter = {"n": 0}

    # 주의: _analyze_clause를 쓰지 않는다 — 그 폴백(주의/해당 없음)이 API 오류를
    # 정상 결과처럼 은폐한다 (2026-08-07 크레딧 소진 사고에서 4,115건 오염).
    # 여기서는 invoke_json을 직접 호출해 오류를 명시적으로 기록하고,
    # 429는 백오프 재시도, 크레딧·인증 오류(400/401)는 즉시 전체 중단한다.
    llm = get_llm(args.model)
    fatal = {"stop": False}

    def work(item):
        k, text = item
        if fatal["stop"]:
            return {"key": k, "risk_level": "SKIPPED", "risk_type": ""}
        prompt = _PROMPT_TEMPLATE.replace("{clause_text}", text)
        for attempt in range(4):
            try:
                d = invoke_json(llm, prompt)
                rec = {"key": k, "risk_level": d["risk_level"], "risk_type": d["risk_type"]}
                break
            except Exception as e:
                name = type(e).__name__
                if "BadRequest" in name or "Authentication" in name or "Permission" in name:
                    fatal["stop"] = True
                    rec = {"key": k, "risk_level": "FATAL", "risk_type": str(e)[:80]}
                    break
                if attempt == 3:
                    rec = {"key": k, "risk_level": "ERROR", "risk_type": str(e)[:80]}
                    break
                time.sleep(10 * (2 ** attempt))
        if rec["risk_level"] in ("FATAL", "SKIPPED", "ERROR"):
            return rec  # 체크포인트에 기록하지 않음 — 재개 시 재실행
        with _lock:
            ckpt_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            ckpt_f.flush()
            counter["n"] += 1
            if counter["n"] % 200 == 0:
                print(f"  진행 {counter['n']}/{len(todo)}")
        return rec

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        for rec in pool.map(work, todo):
            done[rec["key"]] = rec
    ckpt_f.close()

    # 전파 + 집계
    out_rows = []
    for r in rows:
        rec = done.get(norm_key(r["clause_text"]), {})
        r2 = dict(r)
        r2["pred_level"] = rec.get("risk_level", "")
        r2["pred_type"] = rec.get("risk_type", "")
        pred_pos = r2["pred_level"] in ("주의", "위험")
        label_pos = {"strong": True, "weak": False}.get(
            r["label_tier"], r["basis_direction"] == "unfair"
        )
        r2["agree"] = "O" if pred_pos == label_pos else "X"
        out_rows.append(r2)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_rows[0].keys())
        w.writeheader()
        w.writerows(out_rows)

    from collections import Counter

    def agree_rate(sub):
        n = len(sub)
        a = sum(1 for r in sub if r["agree"] == "O")
        return f"{a}/{n} ({a/n:.0%})" if n else "-"

    lines = [
        "# AI Hub 580 전량 측정 결과 (고유 5,782 실행 → 10,200행 전파)",
        "",
        "> C급 라벨과의 **정합성** 측정 — 불일치 ≠ 모델 오류. strong(공정위 심결 인정)",
        "> 서브셋만 준공식 지표로 해석. 원자료: aihub580_full_run_results.csv",
        "",
        "## 신호등급별 일치율",
        "",
    ]
    for tier in ["strong", "reviewed_mixed", "weak"]:
        sub = [r for r in out_rows if r["label_tier"] == tier]
        lines.append(f"- {tier}: {agree_rate(sub)}")
    lines += ["", "## 분야별 일치율 (행수 상위 15)", ""]
    fields = Counter(r["field_tag"] for r in out_rows)
    for fld, n in fields.most_common(15):
        sub = [r for r in out_rows if r["field_tag"] == fld]
        st = [r for r in sub if r["label_tier"] == "strong"]
        lines.append(f"- {fld} (n={n}): 전체 {agree_rate(sub)}, strong {agree_rate(st)}")
    err = sum(1 for r in out_rows if r["pred_level"] == "ERROR")
    dis_strong = sum(1 for r in out_rows if r["label_tier"] == "strong" and r["agree"] == "X")
    lines += [
        "",
        f"실행 오류: {err}행 / strong 불일치(정독 대상): {dis_strong}행",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"저장: {OUT_CSV}\n요약: {OUT_MD}")


if __name__ == "__main__":
    main()
