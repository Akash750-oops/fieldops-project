"""
intent_engine.py

Intent Recognition Engine for FieldOps Commander.

Responsibilities
----------------
- Analyze customer communication.
- Identify the customer's primary intent.
- Return a validated IntentResult.

The Intent Engine does NOT:
- Generate customer replies.
- Assign technicians.
- Dispatch jobs.
- Modify database records.
- Change job status.
- Send notifications.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.services.ai.FieldOpsAI.runtime.orchestrator import (
    AIOrchestrator,
    ai_orchestrator,
)
from app.services.ai.FieldOpsAI.schemas.ai_task import AITask
from app.services.ai.FieldOpsAI.schemas.intent import (
    IntentContext,
    IntentResult,
)

logger = logging.getLogger(__name__)


class IntentEngine:
    """
    AI engine responsible for customer intent recognition.
    """

    def __init__(
        self,
        orchestrator: Optional[AIOrchestrator] = None,
    ) -> None:
        """
        Initialize the Intent Recognition Engine.
        """

        self.orchestrator = orchestrator or ai_orchestrator

    # ---------------------------------------------------------
    # Keyword fallback
    # ---------------------------------------------------------

        # ---------------------------------------------------------
    # Keyword fallback
    # ---------------------------------------------------------

    def _keyword_fallback(
        self,
        context: IntentContext,
    ) -> IntentResult:
        """
        Classify customer intent using keyword rules when
        the AI provider is unavailable.

        Supports:
        - English
        - Spanish
        - Tamil
        - Hindi
        """

        message = context.message.lower()
        language = context.language.lower().strip()

        # -----------------------------------------------------
        # Multilingual keyword definitions
        # -----------------------------------------------------

        escalation_keywords = (
            # English
            "manager",
            "supervisor",
            "escalate",
            "escalation",
            "speak to someone",
            "speak to a person",

            # Spanish
            "gerente",
            "supervisor",
            "escalar",
            "escalación",
            "hablar con alguien",

            # Tamil
            "மேலாளர்",
            "மேற்பார்வையாளர்",
            "மேலாளரிடம் பேச",
            "ஒருவரிடம் பேச",

            # Hindi
            "मैनेजर",
            "प्रबंधक",
            "सुपरवाइजर",
            "शिकायत ऊपर",
            "किसी से बात करना",
        )

        if any(keyword in message for keyword in escalation_keywords):
            return IntentResult(
                intent="ESCALATION_REQUEST",
                confidence=0.80,
                requires_human=True,
            )

        # -----------------------------------------------------
        # Cancellation requests
        # -----------------------------------------------------

        cancellation_keywords = (
            # English
            "cancel",
            "cancellation",
            "call off",
            "terminate appointment",

            # Spanish
            "cancelar",
            "cancelación",
            "anular",
            "quiero cancelar",

            # Tamil
            "ரத்து",
            "ரத்து செய்ய",
            "நியமனத்தை ரத்து",
            "அப்பாயின்ட்மெண்ட்டை ரத்து",

            # Hindi
            "रद्द",
            "रद्द करना",
            "अपॉइंटमेंट रद्द",
            "नियुक्ति रद्द",
        )

        if any(keyword in message for keyword in cancellation_keywords):
            return IntentResult(
                intent="CANCELLATION",
                confidence=0.85,
                requires_human=False,
            )

        # -----------------------------------------------------
        # Complaints
        # -----------------------------------------------------

        complaint_keywords = (
            # English
            "complaint",
            "complain",
            "unhappy",
            "disappointed",
            "terrible",
            "bad service",
            "not working",
            "still not fixed",
            "problem",

            # Spanish
            "queja",
            "reclamo",
            "insatisfecho",
            "insatisfecha",
            "decepcionado",
            "decepcionada",
            "mal servicio",
            "malo",
            "mala",
            "muy malo",
            "muy mala",
            "no funciona",
            "problema",

            # Tamil
            "புகார்",
            "திருப்தி இல்லை",
            "மோசமான சேவை",
            "வேலை செய்யவில்லை",
            "பிரச்சனை",
            "சரி செய்யவில்லை",

            # Hindi
            "शिकायत",
            "असंतुष्ट",
            "निराश",
            "खराब सेवा",
            "काम नहीं कर रहा",
            "समस्या",
            "ठीक नहीं किया",
        )

        if any(keyword in message for keyword in complaint_keywords):
            return IntentResult(
                intent="COMPLAINT",
                confidence=0.80,
                requires_human=False,
            )

        # -----------------------------------------------------
        # Compliments
        # -----------------------------------------------------

        # IMPORTANT:
        # Compliment is checked before STATUS_INQUIRY because
        # messages such as:
        # "Thank you, the technician did a great job"
        # contain the word "technician".

        compliment_keywords = (
            # English
            "thank you",
            "thanks",
            "great service",
            "excellent service",
            "good service",
            "well done",
            "happy with",
            "satisfied",
            "great job",

            # Spanish
            "gracias",
            "muchas gracias",
            "excelente servicio",
            "buen servicio",
            "buen trabajo",
            "muy satisfecho",
            "muy satisfecha",

            # Tamil
            "நன்றி",
            "மிக்க நன்றி",
            "சிறந்த சேவை",
            "நல்ல சேவை",
            "நல்ல வேலை",
            "திருப்தியாக உள்ளது",
            "மிகவும் நன்றாக",

            # Hindi
            "धन्यवाद",
            "बहुत धन्यवाद",
            "बेहतरीन सेवा",
            "अच्छी सेवा",
            "बहुत अच्छा काम",
            "संतुष्ट",
            "बहुत बढ़िया",
        )

        if any(keyword in message for keyword in compliment_keywords):
            return IntentResult(
                intent="COMPLIMENT",
                confidence=0.80,
                requires_human=False,
            )

        # -----------------------------------------------------
        # Status inquiries
        # -----------------------------------------------------

        status_keywords = (
            # English
            "status",
            "where is",
            "when will",
            "when is",
            "update",
            "progress",
            "technician",
            "appointment status",

            # Spanish
            "estado",
            "dónde está",
            "cuando llegará",
            "cuándo llegará",
            "actualización",
            "progreso",
            "técnico",
            "estado de la cita",

            # Tamil
            "நிலை",
            "எங்கே இருக்கிறார்",
            "எப்போது வருவார்",
            "புதுப்பிப்பு",
            "முன்னேற்றம்",
            "தொழில்நுட்ப நிபுணர்",
            "அப்பாயின்ட்மென்ட் நிலை",

            # Hindi
            "स्थिति",
            "कहां है",
            "कब आएगा",
            "कब आएंगे",
            "अपडेट",
            "प्रगति",
            "तकनीशियन",
            "अपॉइंटमेंट की स्थिति",
        )

        if any(keyword in message for keyword in status_keywords):
            return IntentResult(
                intent="STATUS_INQUIRY",
                confidence=0.75,
                requires_human=False,
            )

        # -----------------------------------------------------
        # General question
        # -----------------------------------------------------

        return IntentResult(
            intent="GENERAL_QUESTION",
            confidence=0.50,
            requires_human=True,
        )

    # ---------------------------------------------------------
    # Main intent recognition
    # ---------------------------------------------------------

    def recognize(
        self,
        context: IntentContext,
    ) -> IntentResult:
        """
        Analyze customer communication and identify its intent.

        Parameters
        ----------
        context
            Structured intent recognition context.

        Returns
        -------
        IntentResult
            Validated AI intent classification.
        """

        start_time = time.perf_counter()

        logger.info(
            "Intent Recognition Engine started."
        )

        try:
            # -------------------------------------------------
            # Primary path: AI / Llama through orchestrator
            # -------------------------------------------------

            result = self.orchestrator.execute(
                task=AITask.INTENT,
                context=context.model_dump(),
                response_schema=IntentResult,
            )

            elapsed = time.perf_counter() - start_time

            logger.info(
                "Intent recognition completed in %.2f sec | "
                "Intent=%s | Confidence=%.2f",
                elapsed,
                result.intent,
                result.confidence,
            )

            return result

        except Exception as exc:
            logger.exception(
                "AI intent recognition failed. Using keyword fallback. Error=%s",
                exc,
            )

            fallback_result = self._keyword_fallback(
                context
            )

            logger.info(
                "Intent keyword fallback completed. "
                "Intent=%s | Confidence=%.2f",
                fallback_result.intent,
                fallback_result.confidence,
            )

            return fallback_result