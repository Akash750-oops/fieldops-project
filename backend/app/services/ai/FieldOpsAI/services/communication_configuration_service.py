from sqlalchemy.orm import Session
from ..schemas.communication_configuration import (
    CommunicationChannelState,
    CommunicationMessageCategory,
    DeliveryDecision,
    CommunicationChannelDisabledError,
    CommunicationConfigurationResponse
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
        return CommunicationConfigurationResponse(
            channel=config.channel,
            state=CommunicationChannelState(config.state),
            revision=config.revision,
            updated_at=config.updated_at,
            updated_by=config.updated_by
        )

    def update_channel_state(
        self,
        channel: str,
        new_state: CommunicationChannelState,
        actor_id: str,
        actor_tenant_id: str,
        reason: str,
        correlation_id: str = None
    ) -> CommunicationConfigurationResponse:
        
        # We perform an atomic update using the database transaction.
        try:
            config = self.repository.get_by_channel(channel, for_update=True)
            if not config:
                raise ValueError(f"Configuration for channel '{channel}' not found.")

            previous_state = config.state
            previous_revision = config.revision

            if previous_state == new_state.value:
                # No-op
                self.db.commit()
                return self.get_channel_configuration(channel)

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
        except Exception:
            self.db.rollback()
            raise

    def evaluate_delivery(
        self,
        channel: str,
        category: CommunicationMessageCategory = CommunicationMessageCategory.STANDARD
    ) -> DeliveryDecision:
        try:
            config = self.repository.get_by_channel(channel)
            if not config:
                # Missing-row compatibility
                state = CommunicationChannelState.ENABLED
                revision = 0
                reason_code = "COMPATIBILITY_DEFAULT"
            else:
                state = CommunicationChannelState(config.state)
                revision = config.revision
                
                if state == CommunicationChannelState.ENABLED:
                    reason_code = f"{channel.upper()}_ENABLED"
                elif state == CommunicationChannelState.DISABLED:
                    reason_code = f"{channel.upper()}_DISABLED"
                else:
                    if category == CommunicationMessageCategory.EMERGENCY:
                        reason_code = f"{channel.upper()}_EMERGENCY_ALLOWED"
                    else:
                        reason_code = f"{channel.upper()}_EMERGENCY_REQUIRED"

            allowed = False
            if state == CommunicationChannelState.ENABLED:
                allowed = True
            elif state == CommunicationChannelState.EMERGENCY_ONLY and category == CommunicationMessageCategory.EMERGENCY:
                allowed = True
            
            return DeliveryDecision(
                allowed=allowed,
                channel=channel,
                state=state,
                category=category,
                reason_code=reason_code,
                revision=revision
            )
        except Exception as e:
            # Persistence failure block
            return DeliveryDecision(
                allowed=False,
                channel=channel,
                state=CommunicationChannelState.DISABLED,
                category=category,
                reason_code="CONFIGURATION_UNAVAILABLE",
                revision=0
            )
