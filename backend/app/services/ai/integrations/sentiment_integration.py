"""
sentiment_integration.py

Integration layer between the backend
communication workflow and the AI Sentiment Service.
"""

from app.services.ai.FieldOpsAI.services.sentiment_service import (
    SentimentService,
)
from app.services.ai.FieldOpsAI.schemas.sentiment import SentimentDecision


class SentimentIntegration:
    """
    Adapter for customer sentiment analysis.
    """

    def __init__(
        self,
        service: SentimentService | None = None,
    ) -> None:
        self.service = service or SentimentService()

    def analyze(
        self,
        message: str,
        channel: str,
        language: str = "en",
        previous_messages: list[str] | None = None,
    ) -> SentimentDecision:
        """
        Analyze customer sentiment.
        """

        return self.service.analyze_customer_message(
            message=message,
            language=language,
            previous_messages=previous_messages,
            channel=channel,
        )