"""
sentiment_service.py

Service layer for customer and technician sentiment analysis.

The service delegates sentiment analysis to SentimentEngine.
It does not directly communicate with the AI provider.
"""

from app.services.ai.FieldOpsAI.agents.sentiment_engine import (
    SentimentEngine,
)
from app.services.ai.FieldOpsAI.schemas.sentiment import (
    SentimentContext,
    SentimentDecision,
)


class SentimentService:
    """
    Service layer for sentiment analysis.
    """

    def __init__(
        self,
        engine: SentimentEngine | None = None,
    ) -> None:
        self.engine = engine or SentimentEngine()

    # ---------------------------------------------------------
    # Customer sentiment
    # ---------------------------------------------------------

    def analyze_customer_message(
        self,
        message: str,
        language: str = "en",
        previous_messages: list[str] | None = None,
        channel: str = "CHAT",
    ) -> SentimentDecision:
        """
        Analyze customer sentiment.
        """

        context = SentimentContext(
            channel=channel,
            message=message,
            language=language,
            previous_messages=(
                previous_messages[-3:]
                if previous_messages
                else []
            ),
        )

        return self.engine.analyze(context)

    # ---------------------------------------------------------
    # Technician sentiment
    # ---------------------------------------------------------

    def analyze_technician_message(
        self,
        message: str,
        language: str = "en",
    ) -> SentimentDecision:
        """
        Analyze technician sentiment.
        """

        context = SentimentContext(
            channel="DISPATCH_NOTE",
            message=message,
            language=language,
            previous_messages=[],
        )

        return self.engine.analyze(context)
