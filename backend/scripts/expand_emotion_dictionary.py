"""GPT-4o로 한국어 감정 단어 사전 확장.

사용법:
    OPENAI_API_KEY=sk-... python -m scripts.expand_emotion_dictionary \\
        --target-count 60 --quadrant Q2

작동:
    1. 현재 사전을 읽어 부족한 사분면 확인
    2. GPT-4o에 해당 사분면 단어 추가 생성 요청
    3. 결과를 JSON 파일에 병합 (덮어쓰지 않고 누적)
    4. validate_emotion_dictionary.py로 검증

⚠️ 주의:
   - 비용 발생 (단어당 약 200~400 토큰)
   - 출력은 반드시 연구진 검수 후 --reviewed로 시드해야 함
   - 운영 사전은 절대 검수되지 않은 GPT-4o 초안을 직접 사용하지 말 것
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

PROMPT_TEMPLATE = """당신은 한국어 정서 어휘 전문가입니다.
대학생(KAIST 학부·대학원생)이 일상에서 자신의 감정을 인식하고 명명하는 데 도움이 되는 감정 단어 사전을 만들고 있습니다.

다음 조건을 만족하는 한국어 감정 단어 {n}개를 추가로 생성해주세요.

## 조건
1. **사분면**: {quadrant_label} (valence {v_range}, arousal {a_range})
2. **중복 금지**: 다음 단어들은 이미 사전에 있으니 제외하세요:
   {existing_words}
3. **단어 형태**: "답답하다", "설렌다", "외롭다"처럼 자연스러운 한국어 종결형
4. **임상 용어 회피**: "우울증", "불안장애" 같은 진단명은 사용하지 않음
5. **KAIST 학생 일상**: 시험, 발표, 연구실, 자취, 인간관계 등의 맥락에서 자연스럽게 쓰일 단어

## 각 단어마다 다음 정보를 JSON으로 반환:
- word: 단어 (종결형)
- definition: 일상적 한국어로 한 문장 정의 (15자 이상 35자 이하)
- example: KAIST 학생 일상에서 자연스러운 예시 한 문장
- valence: -1.0 ~ +1.0 (사분면 범위 내)
- arousal: -1.0 ~ +1.0 (사분면 범위 내)
- neighbors: 4개의 인접 단어 정보. 가능하면 다음 기존 사전 단어 중에서 선택:
   {existing_words}
   각 neighbor는:
     - word: 인접 단어
     - direction: "더 강하다면" / "더 약하다면" / "더 차분한 쪽이라면" / "더 들뜬 쪽이라면" / "비슷한 느낌의 다른 표현" 중 하나
     - delta_v, delta_a: 현재 단어에서 인접 단어로의 V, A 변화량

## 출력 형식 (반드시 valid JSON):
{{
  "words": [
    {{
      "word": "...", "definition": "...", "example": "...",
      "valence": 0.0, "arousal": 0.0,
      "neighbors": [
        {{"word": "...", "direction": "...", "delta_v": 0.0, "delta_a": 0.0}},
        ...4개...
      ]
    }},
    ...{n}개...
  ]
}}

JSON만 출력하세요. 설명이나 주석 금지.
"""


QUADRANT_INFO = {
    "Q1": ("유쾌-고각성 (흥분/기쁨/설렘)", "0.0 ~ +1.0", "0.0 ~ +1.0"),
    "Q2": ("불쾌-고각성 (분노/불안/긴장)", "-1.0 ~ 0.0", "0.0 ~ +1.0"),
    "Q3": ("불쾌-저각성 (우울/슬픔/지침)", "-1.0 ~ 0.0", "-1.0 ~ 0.0"),
    "Q4": ("유쾌-저각성 (평온/만족/편안)", "0.0 ~ +1.0", "-1.0 ~ 0.0"),
}


async def expand(file_path: Path, quadrant: str, count: int):
    try:
        from openai import AsyncOpenAI
    except ImportError:
        print("openai 패키지가 필요합니다: pip install openai")
        return 1

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY 환경변수를 설정해주세요")
        return 1

    data = json.loads(file_path.read_text(encoding="utf-8"))
    existing = sorted(w["word"] for w in data["words"])
    label, v_range, a_range = QUADRANT_INFO[quadrant]

    prompt = PROMPT_TEMPLATE.format(
        n=count,
        quadrant_label=label,
        v_range=v_range,
        a_range=a_range,
        existing_words=", ".join(existing),
    )

    print(f"GPT-4o 호출: {quadrant} 사분면 {count}개 단어 요청 중...")
    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "당신은 한국어 정서 어휘 전문가입니다. 반드시 valid JSON만 출력합니다."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    new_data = json.loads(resp.choices[0].message.content)

    # 병합 (중복 체크)
    existing_set = set(existing)
    added = 0
    for w in new_data.get("words", []):
        if w["word"] not in existing_set:
            data["words"].append(w)
            existing_set.add(w["word"])
            added += 1

    backup = file_path.with_suffix(".json.bak")
    file_path.rename(backup)
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {added}개 단어 추가됨. 백업: {backup}")
    print(f"  다음을 실행해 검증하세요:")
    print(f"    python -m scripts.validate_emotion_dictionary {file_path}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="data/emotion_dictionary_v0.json")
    parser.add_argument("--quadrant", choices=["Q1", "Q2", "Q3", "Q4"], required=True)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(expand(Path(args.file), args.quadrant, args.count))


if __name__ == "__main__":
    main()
