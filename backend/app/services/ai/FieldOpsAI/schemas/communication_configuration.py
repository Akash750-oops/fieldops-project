from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class UnsupportedCommunicationChannelError(Exception):
    def __init__(self, channel: str):
        super().__init__(f"Unsupported communication channel: {channel}")
        self.channel = channel

class CommunicationConfigurationNotFoundError(Exception):
    def __init__(self, channel: str):
        super().__init__(f"Configuration for channel '{channel}' not found.")
        self.channel = channel

class CommunicationConfigurationUnavailableError(Exception):
    def __init__(self, message: str = "Communication configuration unavailable"):
        super().__init__(message)

class CommunicationConfigurationConflictError(Exception):
    def __init__(self, message: str = "Communication configuration conflict"):
        super().__init__(message)

def normalize_channel(channel: str) -> str:
    normalized = channel.strip().upper()
    if normalized != "SMS":
        raise UnsupportedCommunicationChannelError(normalized)
    return normalized
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
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
        
class CommunicationConfigurationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    channel: str
    state: CommunicationChannelState
    revision: int
    updated_at: datetime
    updated_by: str

class DeliveryDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
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
