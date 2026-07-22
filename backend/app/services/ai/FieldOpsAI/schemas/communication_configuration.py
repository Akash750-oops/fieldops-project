from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class CommunicationChannelState(str, Enum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    EMERGENCY_ONLY = "EMERGENCY_ONLY"

class CommunicationMessageCategory(str, Enum):
    STANDARD = "STANDARD"
    EMERGENCY = "EMERGENCY"

class CommunicationChannelStateUpdate(BaseModel):
    state: CommunicationChannelState
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for the state change")
    
    class Config:
        extra = "forbid"
        
class CommunicationConfigurationResponse(BaseModel):
    channel: str
    state: CommunicationChannelState
    revision: int
    updated_at: datetime
    updated_by: str

class DeliveryDecision(BaseModel):
    allowed: bool
    channel: str
    state: CommunicationChannelState
    category: CommunicationMessageCategory
    reason_code: str
    revision: int

class CommunicationChannelDisabledError(Exception):
    def __init__(self, message: str, decision: DeliveryDecision):
        super().__init__(message)
        self.decision = decision
