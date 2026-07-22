from sqlalchemy.orm import Session
from ..schemas.communication_configuration import (
    CommunicationChannelState,
    CommunicationMessageCategory,
    DeliveryDecision,
    CommunicationChannelDisabledError,
    CommunicationConfigurationResponse,
    normalize_channel,
    UnsupportedCommunicationChannelError,
    CommunicationConfigurationNotFoundError,
    CommunicationConfigurationUnavailableError,
    CommunicationConfigurationConflictError
)
from ..repositories.communication_configuration_repository import CommunicationConfigurationRepository
from app.models import CommunicationConfigurationAudit
import uuid
import datetime

class CommunicationConfigurationService:
    def __init__(self, repository: CommunicationConfigurationRepository, db: Session):
        self.repository = repository
        self.db = db

    def get_channel_configuration(self, channel: str) -> CommunicationConfigurationResponse:
        channel = normalize_channel(channel)
        config = self.repository.get_by_channel(channel)
        if not config:
            # Compatibility default for missing row
            return CommunicationConfigurationResponse(
                channel=channel,
                state=CommunicationChannelState.ENABLED,
                revision=0,
                updated_at=datetime.datetime.now(datetime.timezone.utc),
                updated_by="system_default"
            )
        return self._to_response(config)

    def update_channel_state(
        self,
        channel: str,
        new_state: CommunicationChannelState,
        actor_id: str,
        actor_tenant_id: str,
        reason: str,
        correlation_id: str = None
    ) -> CommunicationConfigurationResponse:
        channel = normalize_channel(channel)
        reason = reason.strip()
        if not 10 <= len(reason) <= 500:
            raise CommunicationConfigurationConflictError(
                "Invalid configuration change reason."
            )
        
        # We perform an atomic update using the database transaction.
        try:
            config = self.repository.get_by_channel(channel, for_update=True)
            if not config:
                raise CommunicationConfigurationNotFoundError(channel)

            previous_state = config.state
            previous_revision = config.revision

            if previous_state == new_state.value:
                return self._to_response(config)

            self.repository.update_state(config, new_state.value, actor_id)

            audit = CommunicationConfigurationAudit(
                channel=channel,
                previous_state=previous_state,
                new_state=new_state.value,
                previous_revision=previous_revision,
                new_revision=config.revision,
                actor_id=actor_id,
                actor_tenant_id=actor_tenant_id,
                reason=reason,
                correlation_id=correlation_id
            )
            self.repository.add_audit(audit)

            self.db.commit()
            return self.get_channel_configuration(channel)
        except (
            UnsupportedCommunicationChannelError,
            CommunicationConfigurationNotFoundError,
            CommunicationConfigurationConflictError,
        ):
            self.db.rollback()
            raise

        except Exception:
            self.db.rollback()
            raise CommunicationConfigurationUnavailableError(
                "Communication configuration unavailable."
            ) from None

    def evaluate_delivery(
        self,
        channel: str,
        category: CommunicationMessageCategory = (
            CommunicationMessageCategory.STANDARD
        ),
    ) -> DeliveryDecision:
        channel = normalize_channel(channel)

        try:
            config = self.repository.get_by_channel(channel)
        except Exception:
            return DeliveryDecision(
                allowed=False,
                channel=channel,
                state=CommunicationChannelState.DISABLED,
                category=category,
                reason_code="CONFIGURATION_UNAVAILABLE",
                revision=0,
            )

        if config is None:
            return DeliveryDecision(
                allowed=True,
                channel=channel,
                state=CommunicationChannelState.ENABLED,
                category=category,
                reason_code="COMPATIBILITY_DEFAULT",
                revision=0,
            )

        try:
            state = CommunicationChannelState(config.state)
        except (TypeError, ValueError):
            return DeliveryDecision(
                allowed=False,
                channel=channel,
                state=CommunicationChannelState.DISABLED,
                category=category,
                reason_code="CONFIGURATION_UNAVAILABLE",
                revision=0,
            )

        if state == CommunicationChannelState.ENABLED:
            return DeliveryDecision(
                allowed=True,
                channel=channel,
                state=state,
                category=category,
                reason_code="SMS_ENABLED",
                revision=config.revision,
            )

        if state == CommunicationChannelState.DISABLED:
            return DeliveryDecision(
                allowed=False,
                channel=channel,
                state=state,
                category=category,
                reason_code="SMS_DISABLED",
                revision=config.revision,
            )

        if category == CommunicationMessageCategory.EMERGENCY:
            return DeliveryDecision(
                allowed=True,
                channel=channel,
                state=state,
                category=category,
                reason_code="SMS_EMERGENCY_ALLOWED",
                revision=config.revision,
            )

        return DeliveryDecision(
            allowed=False,
            channel=channel,
            state=state,
            category=category,
            reason_code="SMS_EMERGENCY_REQUIRED",
            revision=config.revision,
        )
    def _to_response(
        self,
        config,
    ) -> CommunicationConfigurationResponse:
        return CommunicationConfigurationResponse(
            channel=config.channel,
            state=CommunicationChannelState(
                config.state
            ),
            revision=config.revision,
            updated_at=config.updated_at,
            updated_by=config.updated_by,
        )
