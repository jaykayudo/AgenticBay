# schemas/messages.py
from __future__ import annotations
from typing import Any, Optional, Union, Literal
from pydantic import BaseModel, Field
import json

# ─────────────────────────────────────────────────
# BASE
# ─────────────────────────────────────────────────
class BaseMessage(BaseModel):
    """Root for all messages in the system"""

    class Config:
        use_enum_values = True

    def to_text(self) -> str:
        """
        All communication is wrapped as text.
        Even JSON is encapsulated as a string.
        """
        return self.model_dump_json()

    @classmethod
    def from_text(cls, text: str) -> "BaseMessage":
        return cls.model_validate_json(text)


# ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════
# ORCHESTRATOR ←→ USER AGENT  (WebSocket)
# ═══════════════════════════════════════════════
# ─────────────────────────────────────────────────


# ══════════════
# USER → ORCHESTRATOR REQUESTS
# ══════════════

class StartRequestData(BaseModel):
    user_api_key: str

class StartRequest(BaseMessage):
    type: Literal["START"]
    data: StartRequestData


class SearchAgentRequestData(BaseModel):
    message: str  # natural language e.g "i want to buy a car"

class SearchAgentRequest(BaseMessage):
    type: Literal["SEARCH_AGENT"]
    data: SearchAgentRequestData


class ConnectAgentRequestData(BaseModel):
    agent_id: str

class ConnectAgentRequest(BaseMessage):
    type: Literal["CONNECT_AGENT"]
    data: ConnectAgentRequestData


class ServiceAgentRequestData(BaseModel):
    command:   str
    arguments: dict[str, Any] = Field(default_factory=dict)

class ServiceAgentRequest(BaseMessage):
    type: Literal["SERVICE_AGENT"]
    data: ServiceAgentRequestData


class PaymentSuccessfulRequestData(BaseModel):
    invoice_id: str

class PaymentSuccessfulRequest(BaseMessage):
    type: Literal["PAYMENT_SUCCESSFUL"]
    data: PaymentSuccessfulRequestData


class CloseRequest(BaseMessage):
    type: Literal["CLOSE"]
    data: Optional[dict] = None


# Union of all possible inbound messages from user agent
UserAgentMessage = Union[
    StartRequest,
    SearchAgentRequest,
    ConnectAgentRequest,
    ServiceAgentRequest,
    PaymentSuccessfulRequest,
    CloseRequest,
]


# ══════════════
# ORCHESTRATOR → USER AGENT RESPONSES
# ══════════════

class AgentSearchResult(BaseModel):
    id:          str
    name:        str
    description: str
    rating:      float
    pricing:     dict[str, Any]  # e.g {"summarization": 90, "extraction": 30}

class StartResponseData(BaseModel):
    job_session_id:        str
    job_session_auth_token: str
    next_suggested_command: Literal["SEARCH_AGENT"] = "SEARCH_AGENT"

class StartResponse(BaseMessage):
    type: Literal["START"]
    data: StartResponseData


class SearchAgentResponseData(BaseModel):
    agents:                list[AgentSearchResult]
    next_suggested_command: Literal["CONNECT_AGENT"] = "CONNECT_AGENT"

class SearchAgentResponse(BaseMessage):
    type: Literal["SEARCH_AGENT"]
    data: SearchAgentResponseData


class ConnectResponseData(BaseModel):
    agent_id:              str
    capabilities:          str  # raw capability document text
    next_suggested_command: Literal["SERVICE_AGENT"] = "SERVICE_AGENT"

class ConnectResponse(BaseMessage):
    type: Literal["CONNECT"]
    data: ConnectResponseData


class ContractData(BaseModel):
    invoice_id:       str
    invoice_contract: str  # contract address
    function_name:    str  # e.g "pay_invoice"

class PaymentResponseData(BaseModel):
    amount:       float
    description:  str
    contract_data: ContractData

class PaymentResponse(BaseMessage):
    type: Literal["PAYMENT"]
    data: PaymentResponseData


class PaymentSuccessfulResponseData(BaseModel):
    invoice_id: str

class PaymentSuccessfulResponse(BaseMessage):
    type: Literal["PAYMENT_SUCCESSFUL"]
    data: PaymentSuccessfulResponseData


class CloseAppealResponse(BaseMessage):
    type: Literal["CLOSE_APPEAL"]
    data: dict[str, Any]
    next_suggested_command: Literal["CLOSE"] = "CLOSE"


class ServiceAgentResponse(BaseMessage):
    type: Literal["SERVICE_AGENT"]
    # Can be either data dict or plain message string
    data:    Optional[Any] = None
    message: Optional[str] = None


class ErrorResponseData(BaseModel):
    error_type: str  # "validation_error" | "payment_error" | "request_error" etc.
    message:    str

class ErrorResponse(BaseMessage):
    type: Literal["ERROR"]
    data: ErrorResponseData


# Union of all possible outbound messages to user agent
OrchestratorToUserMessage = Union[
    StartResponse,
    SearchAgentResponse,
    ConnectResponse,
    PaymentResponse,
    PaymentSuccessfulResponse,
    CloseAppealResponse,
    ServiceAgentResponse,
    ErrorResponse,
]


# ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════
# ORCHESTRATOR ←→ SERVICE AGENT (HTTP JSON-RPC)
# ═══════════════════════════════════════════════
# ─────────────────────────────────────────────────


# ══════════════
# ORCHESTRATOR → SERVICE AGENT (POST /invoke/{session_id})
# ══════════════

class ServiceAgentInvokeRequest(BaseModel):
    """
    Sent by orchestrator to service agent via HTTP POST.
    command and arguments are derived from the user agent's
    SERVICE_AGENT request or from orchestrator internal logic.
    """
    command:   str
    arguments: dict[str, Any] = Field(default_factory=dict)

    def to_text(self) -> str:
        return self.model_dump_json()


class ServiceAgentCapabilityRequest(BaseModel):
    """Sent to GET /capabilities of service agent"""
    pass  # no body needed — it's a GET


# ══════════════
# SERVICE AGENT → ORCHESTRATOR (HTTP Response body)
# ══════════════

class ServicePaymentRequestData(BaseModel):
    amount:      str           # USDC amount as string
    address:     Optional[str] = None  # if None, use agent's registered wallet
    description: str

class ServicePaymentRequest(BaseModel):
    """Service agent requesting payment from user"""
    type: Literal["PAYMENT"]
    data: ServicePaymentRequestData


class ServiceJobDoneData(BaseModel):
    message: str
    details: dict[str, Any] = Field(default_factory=dict)

class ServiceJobDone(BaseModel):
    """Service agent signaling job completion"""
    type: Literal["JOB_DONE"]
    data: ServiceJobDoneData


class ServiceCapabilityResponse(BaseModel):
    """Response from /capabilities endpoint"""
    message: str  # full capability document as text


class ServiceGenericResponse(BaseModel):
    """
    Any other response from service agent —
    data results, lists, confirmations etc.
    """
    data: Any  # could be dict, list, string


# Union of all possible responses from service agent
ServiceAgentResponseBody = Union[
    ServicePaymentRequest,
    ServiceJobDone,
    ServiceGenericResponse,
]


# ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════
# HTTP REST — Job Session Start
# (before WebSocket, authenticated with API key)
# ═══════════════════════════════════════════════
# ─────────────────────────────────────────────────

class StartJobSessionRequest(BaseModel):
    """POST /api/start-job-session/"""
    user_api_key: str

class StartJobSessionResponse(BaseModel):
    """HTTP response — client then opens WebSocket"""
    type: Literal["START"] = "START"
    data: StartResponseData


# ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════
# SESSION STATE
# Internal state object for the orchestrator
# ═══════════════════════════════════════════════
# ─────────────────────────────────────────────────

from enum import Enum

class SessionPhase(str, Enum):
    STARTED          = "STARTED"
    SEARCHING        = "SEARCHING"
    CONNECTING       = "CONNECTING"
    ACTIVE           = "ACTIVE"       # in a job loop with service agent
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    CLOSING          = "CLOSING"
    CLOSED           = "CLOSED"

class JobSessionState(BaseModel):
    """
    Full state of a job session.
    Stored in Redis, updated on every event.
    """
    # Identity
    session_id:        str
    user_id:           str
    user_agent_id:     str

    # Phase
    phase:             SessionPhase = SessionPhase.STARTED

    # Agent
    connected_agent_id:      Optional[str] = None
    agent_endpoint:          Optional[str] = None
    agent_wallet_address:    Optional[str] = None
    agent_capabilities:      Optional[str] = None  # raw capability doc

    # Payment tracking
    pending_invoice_id:      Optional[str] = None
    paid_invoice_ids:        list[str]     = Field(default_factory=list)
    total_paid:              float         = 0.0

    # Session
    auth_token:              str           = ""
    created_at:              str           = ""
    last_activity_at:        str           = ""


# ─────────────────────────────────────────────────
# HELPER: Parse any inbound user agent message
# ─────────────────────────────────────────────────

def parse_user_agent_message(raw: str) -> UserAgentMessage:
    """
    Parse raw text from WebSocket into the correct
    typed message object.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError(f"Message is not valid JSON: {raw}")

    msg_type = data.get("type")

    type_map = {
        "START":               StartRequest,
        "SEARCH_AGENT":        SearchAgentRequest,
        "CONNECT_AGENT":       ConnectAgentRequest,
        "SERVICE_AGENT":       ServiceAgentRequest,
        "PAYMENT_SUCCESSFUL":  PaymentSuccessfulRequest,
        "CLOSE":               CloseRequest,
    }

    handler = type_map.get(msg_type)
    if not handler:
        raise ValueError(f"Unknown message type: {msg_type}")

    return handler.model_validate(data)


def parse_service_agent_response(raw: dict) -> ServiceAgentResponseBody:
    """
    Parse HTTP response body from service agent into
    the correct typed response object.
    """
    msg_type = raw.get("type")

    if msg_type == "PAYMENT":
        return ServicePaymentRequest.model_validate(raw)
    elif msg_type == "JOB_DONE":
        return ServiceJobDone.model_validate(raw)
    else:
        return ServiceGenericResponse.model_validate(raw)