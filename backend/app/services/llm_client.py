"""OpenAI LLM 호출 어댑터.

설계 원칙:
  - Zero Data Retention 적용 (OPENAI_ZERO_DATA_RETENTION=true 시 응답 헤더로 확인 권장)
  - 토큰 한도 보수적 (max_tokens=120, 사양서: 1-2문장)
  - 실패 시 fallback 응답 — LLM API 장애가 사용자 흐름을 완전히 막지 않도록
  - 테스트용 MockLLMClient 제공

비용 추정 (사양서 6항 가이드):
  사용자 1명 × 하루 3회 × 28일 × 평균 4턴 ≈ 336턴
  턴당 입출력 평균 500토큰 → 168,000 토큰 / 사용자 / 4주
  GPT-4o 가격(2025년 기준 입력 $2.5/1M, 출력 $10/1M): 사용자당 약 $0.5~1
"""
from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    async def complete(
        self, system: str, messages: list[dict[str, str]]
    ) -> str: ...


class OpenAIClient:
    """OpenAI GPT-4o 호출 어댑터."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: float = 15.0,
    ):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.timeout_s = timeout_s
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise RuntimeError(
                    "openai 패키지가 설치되지 않았습니다. pip install openai"
                ) from e
            self._client = AsyncOpenAI(api_key=self.api_key, timeout=self.timeout_s)
        return self._client

    async def complete(
        self, system: str, messages: list[dict[str, str]]
    ) -> str:
        """LLM 호출. 실패 시 RuntimeError.
        
        messages 형식: [{"role": "user"/"assistant", "content": "..."}, ...]
        """
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY 미설정")

        client = await self._get_client()
        chat_messages = [{"role": "system", "content": system}] + messages

        try:
            resp = await client.chat.completions.create(
                model=self.model,
                messages=chat_messages,
                temperature=0.7,
                max_tokens=120,  # 사양서: 1-2문장 짧게
                presence_penalty=0.0,
                frequency_penalty=0.0,
            )
            content = resp.choices[0].message.content or ""
            return content.strip()
        except Exception as e:
            logger.exception("OpenAI 호출 실패")
            raise RuntimeError(f"LLM 호출 실패: {e}") from e


class MockLLMClient:
    """테스트용 — 사전 정의된 응답을 순서대로 반환."""

    def __init__(self, scripted_responses: list[str] | None = None):
        self.scripted = scripted_responses or [
            "지금 몸에서 어떤 느낌이 가장 먼저 느껴지나요?",
            "그렇게 느끼는 데에는 그럴 만한 이유가 있을 것 같아요.",
            "그 느낌을 어떤 단어로 부르고 싶으신가요?",
        ]
        self.calls: list[tuple[str, list[dict]]] = []
        self._idx = 0

    async def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        self.calls.append((system, list(messages)))
        if self._idx < len(self.scripted):
            r = self.scripted[self._idx]
            self._idx += 1
            return r
        return self.scripted[-1]


# 전역 인스턴스 (앱 라이프타임)
_singleton: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """기본 클라이언트 가져오기. 테스트에서 override 가능."""
    global _singleton
    if _singleton is None:
        _singleton = OpenAIClient()
    return _singleton


def set_llm_client(client: LLMClient) -> None:
    """테스트나 의존성 주입에서 교체."""
    global _singleton
    _singleton = client
