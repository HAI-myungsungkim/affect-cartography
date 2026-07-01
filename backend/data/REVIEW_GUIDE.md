# 한국어 감정 단어 사전 검수 가이드

연구진이 GPT-4o 초안을 검수할 때 따라야 할 체크리스트.

## 1. 자동 검증 (필수)

다음 스크립트가 통과해야 함:
```bash
python -m scripts.validate_emotion_dictionary data/emotion_dictionary_v0.json
```

자동 검증 항목:
- valence/arousal 범위 (-1.0 ~ +1.0)
- 각 사분면 최소 5개 (운영 시 12개로 상향 권장)
- 모든 `neighbors[].word`가 사전 내에 존재
- `neighbors` 4개
- 중복 단어 없음
- `definition`, `example` 비어있지 않음

## 2. 수동 검수 체크리스트 (각 단어마다)

### 정의 (definition)
- [ ] 일상적 한국어인가? (임상 용어·진단명 X)
- [ ] 15자 이상 35자 이하인가?
- [ ] 다른 단어와 충분히 구별되는 정의인가?

### 예시 (example)
- [ ] KAIST 학생 일상에서 자연스러운 맥락인가?
  - 좋은 예: "발표 직전이라 두근거린다", "시험 기간 내내 잠을 못 자서 지쳤다"
  - 나쁜 예: "회사 회의에서...", "아이를 키우다 보니..."
- [ ] 단어가 자연스럽게 들어가는가?

### 좌표 (valence, arousal)
- [ ] 사분면이 맞는가?
- [ ] 비슷한 단어들과 좌표 차이가 합리적인가?
  - 예: "설렌다(0.6, 0.5)" < "신난다(0.7, 0.7)" < "벅차다(0.8, 0.6)" 강도 순서

### 인접 단어 (neighbors)
- [ ] 4개 모두 사전에 존재하는가?
- [ ] direction 문구가 자연스러운가?
  - 권장: "더 강하다면", "더 약하다면", "더 차분한 쪽이라면", "더 들뜬 쪽이라면", "비슷한 느낌의 다른 표현"
- [ ] `delta_v`, `delta_a`가 실제 좌표 차이와 일치하는가?

## 3. 사분면 균형 (운영 사전 권장)

| 사분면 | 라벨 | 최소 | 권장 | 핵심 단어 예시 |
|---|---|---|---|---|
| Q1 | 유쾌-고각성 | 12 | 15~20 | 신난다, 설렌다, 벅차다, 두근거린다 |
| Q2 | 불쾌-고각성 | 12 | 15~20 | 긴장된다, 불안하다, 화난다, 짜증난다 |
| Q3 | 불쾌-저각성 | 12 | 15~20 | 답답하다, 지친다, 외롭다, 우울하다 |
| Q4 | 유쾌-저각성 | 12 | 15~20 | 편안하다, 차분하다, 뿌듯하다, 행복하다 |

## 4. 검수 완료 후 시드

```bash
# 검수 완료 본을 reviewed_by_researcher=True로 시드
python -m scripts.seed_emotion_dictionary --reset --reviewed --file data/emotion_dictionary_v1_reviewed.json
```

## 5. GPT-4o로 확장

```bash
# 예: Q2 단어 5개 추가 생성
OPENAI_API_KEY=sk-... python -m scripts.expand_emotion_dictionary --quadrant Q2 --count 5

# 검증
python -m scripts.validate_emotion_dictionary data/emotion_dictionary_v0.json

# 검수 후 시드
python -m scripts.seed_emotion_dictionary --reset --reviewed
```

## 6. 참고 자료

- 장혜진, 김영근 (2020). 한국어 대표 정서 단어. *정서·행동장애연구*
- 권소영, 윤홍옥, 이동훈 (2022). 한국어 정서 단어 450개에 대한 정서가, 각성가, 구체성 평정. *인지과학*
