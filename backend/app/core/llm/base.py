"""واجهة موحّدة لكل مزوّدي النماذج (BaseLLM).

أي مزوّد (محلي أو سحابي) يطبّق هذه الواجهة — الدردشة والتدفق والأدوات والتضمين
بنفس الشكل، مهما كان المزوّد خلفه.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class BaseLLM(ABC):
    """العقد الموحّد لطبقة النماذج."""

    provider: str
    model: str

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """استجابة كاملة (غير متدفقة)."""

    @abstractmethod
    def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """تدفق الاستجابة قطعةً قطعة."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """تضمين نصوص (للاسترجاع الدلالي)."""
