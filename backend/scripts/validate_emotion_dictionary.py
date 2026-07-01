"""감정 단어 사전 무결성 검증.

체크 항목:
  1. valence/arousal 범위 (-1.0 ~ +1.0)
  2. 사분면별 단어 수 균형 (각 사분면 최소 N개)
  3. neighbors의 word가 실제 사전에 존재하는지 (5단계 에이전트가 인접 단어를 가져올 때 누락 방지)
  4. neighbors 4개 보장
  5. 중복 단어 없음

운영 전 검수 시 매번 이 스크립트를 통과해야 한다.

사용법:
    python -m scripts.validate_emotion_dictionary data/emotion_dictionary_v0.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def quadrant_of(v: float, a: float) -> str:
    if v >= 0 and a >= 0:
        return "Q1"
    if v < 0 and a >= 0:
        return "Q2"
    if v < 0 and a < 0:
        return "Q3"
    return "Q4"


def validate(path: Path, min_per_quadrant: int = 5) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    words = data["words"]
    errors: list[str] = []
    warnings: list[str] = []

    word_set = {w["word"] for w in words}
    counts: Counter[str] = Counter()

    # 1. 중복 검사
    duplicates = [w for w, c in Counter(w["word"] for w in words).items() if c > 1]
    if duplicates:
        errors.append(f"중복 단어: {duplicates}")

    for w in words:
        word = w["word"]
        v, a = w["valence"], w["arousal"]

        # 2. 범위
        if not (-1.0 <= v <= 1.0):
            errors.append(f"{word}: valence={v} 범위 초과")
        if not (-1.0 <= a <= 1.0):
            errors.append(f"{word}: arousal={a} 범위 초과")

        # 3. 사분면 집계
        counts[quadrant_of(v, a)] += 1

        # 4. neighbors 검증
        neighbors = w.get("neighbors", [])
        if len(neighbors) != 4:
            warnings.append(f"{word}: neighbors {len(neighbors)}개 (4개 권장)")
        for n in neighbors:
            if n["word"] not in word_set:
                errors.append(
                    f"{word}의 neighbor '{n['word']}'가 사전에 없음 → 5단계 에이전트가 깨짐"
                )
            for k in ("delta_v", "delta_a"):
                if k not in n:
                    errors.append(f"{word}의 neighbor '{n['word']}'에 {k} 누락")

        # 5. 필수 필드
        for field in ("definition", "example"):
            if not w.get(field):
                errors.append(f"{word}: {field} 비어있음")

    # 6. 사분면 균형
    print("\n=== 사분면 분포 ===")
    for q in ("Q1", "Q2", "Q3", "Q4"):
        c = counts[q]
        label = {"Q1": "유쾌-고각성", "Q2": "불쾌-고각성",
                 "Q3": "불쾌-저각성", "Q4": "유쾌-저각성"}[q]
        marker = "✓" if c >= min_per_quadrant else "✗"
        print(f"  {marker} {q} ({label}): {c}개 (최소 {min_per_quadrant})")
        if c < min_per_quadrant:
            errors.append(f"{q} 단어 수 부족: {c} < {min_per_quadrant}")

    print(f"\n총 단어 수: {len(words)}")
    print(f"버전: {data.get('version', 'unknown')}")

    if warnings:
        print(f"\n=== 경고 ({len(warnings)}) ===")
        for w in warnings:
            print(f"  ⚠ {w}")

    if errors:
        print(f"\n=== 오류 ({len(errors)}) ===")
        for e in errors:
            print(f"  ✗ {e}")
        return 1

    print("\n✅ 사전 검증 통과")
    return 0


if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1
                else "data/emotion_dictionary_v0.json")
    sys.exit(validate(path))
