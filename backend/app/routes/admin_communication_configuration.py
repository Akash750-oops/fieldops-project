from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from ..database import get_db
from .admin_prompts import require_prompt_admin # Reusing the strongest admin dependency
from ..services.ai.FieldOpsAI.schemas.communication_configuration import (
    CommunicationChannelStateUpdate,
    CommunicationConfigurationResponse,
    CommunicationChannelState
)
from ..services.ai.FieldOpsAI.repositories.communication_configuration_repository import CommunicationConfigurationRepository
from ..services.ai.FieldOpsAI.services.communication_configuration_service import CommunicationConfigurationService
from ..context import correlation_id_ctx

router = APIRouter(
    prefix="/admin/communication-config/channels",
    tags=["admin", "communication-config"]
)

def get_config_service(db: Session = Depends(get_db)) -> CommunicationConfigurationService:
    repository = CommunicationConfigurationRepository(db)
    return CommunicationConfigurationService(repository, db)

@router.get("/{channel}", response_model=CommunicationConfigurationResponse)
def get_channel_configuration(
    channel: str,
    admin=Depends(require_prompt_admin),
    service: CommunicationConfigurationService = Depends(get_config_service)
):
    if admin.tenant_id != "**platform**":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform super-admin required")
        
    if channel.lower() != "sms":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Channel {channel} is not supported.")
        
    return service.get_channel_configuration(channel.upper())

@router.put("/{channel}", response_model=CommunicationConfigurationResponse)
def update_channel_configuration(
    channel: str,
    update: CommunicationChannelStateUpdate,
    admin=Depends(require_prompt_admin),
    service: CommunicationConfigurationService = Depends(get_config_service)
):
    if admin.tenant_id != "**platform**":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform super-admin required")
        
    if channel.lower() != "sms":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Channel {channel} is not supported.")
        
    reason = update.reason.strip()
    if len(reason) < 10 or len(reason) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason length must be between 10 and 500 characters")

    try:
        correlation_id = correlation_id_ctx.get()
        return service.update_channel_state(
            channel=channel.upper(),
            new_state=update.state,
            actor_id=admin.user_id,
            actor_tenant_id=admin.tenant_id,
            reason=reason,
            correlation_id=correlation_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
