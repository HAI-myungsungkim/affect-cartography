"""감정 단어 사전 JSON → PostgreSQL emotion_dictionary 테이블로 시드.

사용법:
    python -m scripts.seed_emotion_dictionary
    python -m scripts.seed_emotion_dictionary --file data/emotion_dictionary_v0.json --reset

옵션:
    --file PATH     사전 JSON 경로 (기본 data/emotion_dictionary_v0.json)
    --reset         기존 사전 전체 삭제 후 재삽입
    --reviewed      reviewed_by_researcher=True로 표시 (검수 완료 본)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.emotion import EmotionDictionary


async def seed(file_path: Path, reset: bool, reviewed: bool) -> int:
    if not file_path.exists():
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return 1

    data = json.loads(file_path.read_text(encoding="utf-8"))
    words = data["words"]

    async with AsyncSessionLocal() as db:
        if reset:
            await db.execute(delete(EmotionDictionary))
            print("기존 사전 삭제 완료")

        existing = await db.execute(select(EmotionDictionary.word))
        existing_set = {row[0] for row in existing.all()}

        added, skipped = 0, 0
        for w in words:
            if w["word"] in existing_set:
                skipped += 1
                continue
            db.add(EmotionDictionary(
                word=w["word"],
                definition=w["definition"],
                example=w["example"],
                valence=w["valence"],
                arousal=w["arousal"],
                neighbors=w["neighbors"],
                reviewed_by_researcher=reviewed,
                source=data.get("version", "v0"),
            ))
            added += 1

        await db.commit()

    print(f"\n시드 완료: 추가 {added}개, 스킵(이미 존재) {skipped}개")
    print(f"사전 버전: {data.get('version', 'unknown')}")
    print(f"reviewed_by_researcher: {reviewed}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="data/emotion_dictionary_v0.json")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--reviewed", action="store_true",
                        help="연구진 검수 완료 본을 시드할 때 사용")
    args = parser.parse_args()

    code = asyncio.run(seed(Path(args.file), args.reset, args.reviewed))
    sys.exit(code)


if __name__ == "__main__":
    main()
