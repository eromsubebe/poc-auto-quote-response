from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel


# --- Rate schemas ---

class RateCreate(BaseModel):
    carrier_name: str
    mode: str  # AIR, SEA, ROAD
    origin_port: str
    destination_port: str
    currency: str = "USD"
    rate_per_unit: float
    unit: str  # KG, CBM, CONTAINER
    minimum_charge: Optional[float] = None
    dg_surcharge_pct: Optional[float] = None
    valid_from: date
    valid_to: date
    source: str = "MANUAL"
    notes: Optional[str] = None


class RateUpdate(BaseModel):
    carrier_name: Optional[str] = None
    rate_per_unit: Optional[float] = None
    minimum_charge: Optional[float] = None
    dg_surcharge_pct: Optional[float] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class RateResponse(BaseModel):
    id: str
    carrier_name: str
    mode: str
    origin_port: str
    destination_port: str
    currency: str
    rate_per_unit: float
    unit: str
    minimum_charge: Optional[float]
    dg_surcharge_pct: Optional[float]
    valid_from: date
    valid_to: date
    source: str
    status: str
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RateLookupRequest(BaseModel):
    origin: str
    destination: str
    mode: str
    weight_kg: Optional[float] = None
    is_dangerous_goods: bool = False


class RateLookupResponse(BaseModel):
    found: bool
    match_type: str  # EXACT, SIMILAR, EXPIRED, NONE
    rate: Optional[RateResponse] = None
    estimated_cost: Optional[float] = None
    confidence: float
    message: str


# --- RFQ schemas ---

class RFQCreateResponse(BaseModel):
    id: str
    status: str
    customer_name: Optional[str]
    customer_email: Optional[str]
    subject: Optional[str]
    urgency: str
    shipping_mode: Optional[str]
    origin: Optional[str]
    destination: Optional[str]
    is_dangerous_goods: bool
    rate_id: Optional[str]
    rate_amount: Optional[float]
    rate_currency: Optional[str]
    estimated_cost: Optional[float]
    odoo_sale_order_id: Optional[int]
    odoo_quotation_number: Optional[str]
    message: str


class RFQDetail(BaseModel):
    id: str
    rfq_reference: Optional[str]
    customer_name: Optional[str]
    customer_email: Optional[str]
    subject: Optional[str]
    status: str
    shipping_mode: Optional[str]
    origin: Optional[str]
    destination: Optional[str]
    is_dangerous_goods: bool
    urgency: str
    parsed_email_json: Optional[str]
    parsed_cipl_json: Optional[str]
    parsed_msds_json: Optional[str]
    rate_id: Optional[str]
    rate_amount: Optional[float]
    rate_currency: Optional[str]
    estimated_cost: Optional[float]
    odoo_sale_order_id: Optional[int]
    odoo_quotation_number: Optional[str]
    email_file_path: Optional[str]
    attachment_paths_json: Optional[str]
    assigned_agent: Optional[str]
    sla_target_hours: Optional[int]
    sla_deadline_at: Optional[datetime]
    sla_breached: bool = False
    sla_breached_at: Optional[datetime]
    received_at: Optional[datetime]
    parsing_completed_at: Optional[datetime]
    rate_found_at: Optional[datetime]
    quote_drafted_at: Optional[datetime]
    quote_sent_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    audit_log: list[dict[str, Any]] = []

    model_config = {"from_attributes": True}


class RFQListItem(BaseModel):
    id: str
    rfq_reference: Optional[str]
    customer_name: Optional[str]
    subject: Optional[str]
    status: str
    urgency: str
    shipping_mode: Optional[str]
    origin: Optional[str]
    destination: Optional[str]
    is_dangerous_goods: bool
    odoo_quotation_number: Optional[str]
    assigned_agent: Optional[str]
    sla_deadline_at: Optional[datetime]
    sla_breached: bool = False
    received_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AssignRateRequest(BaseModel):
    rate_id: str


class AssignAgentRequest(BaseModel):
    agent: str


class AgentWorkload(BaseModel):
    agent: str
    active_rfqs: int
    pending_rfqs: int
    total_assigned: int


# --- Dashboard schemas ---

class DashboardOverview(BaseModel):
    by_status: dict[str, int]
    total: int
    urgent_count: int
