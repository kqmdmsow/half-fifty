"""상담 녹취 → 발화 텍스트 (#175, 2순위 '무엇을 설명했고 무엇에 서명했는가').

## 왜 녹취가 필요한가

계약서만 보면 "무엇에 서명했는가"는 알 수 있지만 **"무엇을 설명받았는가"는
알 수 없다.** 금융소비자보호법의 설명의무 위반은 대부분 계약서가 아니라
판매 현장에서 일어난다 — 계약서에는 있는데 말로는 안 해 준 수수료, 계약서와
다르게 설명한 조건, 아예 언급하지 않은 위험.

불완전판매 민원의 30% 이상이 60세 이상이라는 통계가 이 지점을 가리킨다.
서류를 다 받았어도 설명을 못 들었으면 소비자는 알 수 없다.

## 설계

- **음성 파일은 Gemini 멀티모달로 바로 전사한다.** 별도 STT 서비스를 붙이지
  않는다 — 키와 의존성이 하나 늘고, 전사 품질 대비 이득이 없다.
- **텍스트 스크립트도 그대로 받는다.** 상담 스크립트·챗 상담 기록·녹취록
  문서가 이미 있는 경우가 많고, 그때는 전사 단계가 불필요하다.
- 전사 실패는 조용히 넘기지 않는다. 녹취를 못 읽었는데 "설명 누락 없음"으로
  보고하면 정반대 결론을 주게 된다.
"""

import os
from typing import Optional

_MAX_AUDIO_BYTES = 25 * 1024 * 1024      # 약 30분 분량. 그 이상은 분할 요청.
_MODEL = os.getenv("MODEL_TRANSCRIBE", "gemini-2.5-flash")

# 화자를 나누고 군더더기를 빼되 **내용을 요약하지는 않게** 한다. 요약하면
# "설명하지 않은 것"을 찾는 작업의 근거가 사라진다.
_PROMPT = (
    "이 오디오는 금융상품 판매 상담 녹취입니다. 전체 대화를 한국어로 받아쓰세요.\n"
    "- 화자를 [상담사]와 [고객]으로 구분해 각 발언 앞에 붙이세요.\n"
    "- 요약하지 말고 실제로 한 말을 그대로 옮기세요. 말끝 흐림·반복도 그대로 두세요.\n"
    "- 들리지 않는 구간은 [불명]으로 표시하세요. 추측해서 채우지 마세요.\n"
    "- 받아쓴 내용 외에 어떤 설명이나 평가도 덧붙이지 마세요."
)

_AUDIO_MIME = {
    ".mp3": "audio/mp3", ".m4a": "audio/mp4", ".wav": "audio/wav",
    ".ogg": "audio/ogg", ".flac": "audio/flac", ".aac": "audio/aac",
    ".webm": "audio/webm",
}


class TranscriptUnavailableError(RuntimeError):
    """전사를 할 수 없는 상태. 조용히 빈 문자열로 넘기지 않기 위한 예외.

    녹취를 못 읽었는데 "설명 누락 없음"으로 보고하면 사용자에게 정반대
    결론을 주게 된다.
    """


def guess_audio_mime(filename: str) -> Optional[str]:
    ext = os.path.splitext(filename.lower())[1]
    return _AUDIO_MIME.get(ext)


def transcribe(audio_bytes: bytes, filename: str) -> str:
    """음성 파일 -> 화자 구분된 발화 텍스트."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise TranscriptUnavailableError("GOOGLE_API_KEY 미설정 — 녹취 전사 비활성")
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        raise TranscriptUnavailableError(
            f"녹취 파일이 너무 큽니다 ({len(audio_bytes) // 1024 // 1024}MB). "
            f"{_MAX_AUDIO_BYTES // 1024 // 1024}MB 이하로 나눠 올려 주세요.")
    mime = guess_audio_mime(filename)
    if not mime:
        raise TranscriptUnavailableError(
            f"지원하지 않는 음성 형식입니다: {filename}. "
            f"{', '.join(sorted(_AUDIO_MIME))} 중 하나로 올려 주세요.")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=_MODEL,
            contents=[_PROMPT, types.Part.from_bytes(data=audio_bytes, mime_type=mime)],
        )
        text = (response.text or "").strip()
    except TranscriptUnavailableError:
        raise
    except Exception as exc:
        raise TranscriptUnavailableError(f"전사 호출 실패: {exc}") from exc

    if not text:
        raise TranscriptUnavailableError(
            "녹취에서 발화를 찾지 못했습니다 (무음이거나 판독 불가일 수 있습니다).")
    return text
