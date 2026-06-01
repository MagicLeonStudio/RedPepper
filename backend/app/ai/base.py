"""AI Provider base class."""

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Abstract base class for AI service providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat completion request."""
        pass

    @abstractmethod
    async def vision(
        self,
        image_base64: str,
        prompt: str,
        model: str | None = None,
    ) -> str:
        """Send a vision request with an image."""
        pass

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings for the given texts."""
        pass
