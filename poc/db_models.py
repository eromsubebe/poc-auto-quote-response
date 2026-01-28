import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String, Text

from poc.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Rate(Base):
    __tablename__ = "rates"

    id = Column(String, primary_key=True, default=_uuid)
    carrier_name = Column(String, nullable=False)
    mode = Column(String, nullable=False)  # AIR, SEA, ROAD
    origin_port = Column(String, nullable=False)
    destination_port = Column(String, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    rate_per_unit = Column(Float, nullable=False)
    unit = Column(String, nullable=False)  # KG, CBM, CONTAINER
    minimum_charge = Column(Float, nullable=True)
    dg_surcharge_pct = Column(Float, nullable=True)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    source = Column(String, nullable=False, default="SEED")  # SEED, MANUAL, CARRIER_API
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE, EXPIRED
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class RFQWorkflow(Base):
    __tablename__ = "rfq_workflow"

    id = Column(String, primary_key=True, default=_uuid)
    rfq_reference = Column(String, nullable=True)
    customer_name = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    status = Column(String, nullable=False, default="received")
    shipping_mode = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    is_dangerous_goods = Column(Boolean, default=False)
    urgency = Column(String, default="STANDARD")
    parsed_email_json = Column(Text, nullable=True)
    parsed_cipl_json = Column(Text, nullable=True)
    parsed_msds_json = Column(Text, nullable=True)
    rate_id = Column(String, nullable=True)
    rate_amount = Column(Float, nullable=True)
    rate_currency = Column(String, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    odoo_sale_order_id = Column(Integer, nullable=True)
    odoo_quotation_number = Column(String, nullable=True)
    email_file_path = Column(String, nullable=True)
    attachment_paths_json = Column(Text, nullable=True)
    # Assigned agent for workflow
    assigned_agent = Column(String, nullable=True)
    # SLA tracking fields
    sla_target_hours = Column(Integer, nullable=True)
    sla_deadline_at = Column(DateTime, nullable=True)
    sla_breached = Column(Boolean, default=False)
    sla_breached_at = Column(DateTime, nullable=True)
    # Timestamps
    received_at = Column(DateTime, nullable=True)
    parsing_completed_at = Column(DateTime, nullable=True)
    rate_found_at = Column(DateTime, nullable=True)
    quote_drafted_at = Column(DateTime, nullable=True)
    quote_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfq_id = Column(String, nullable=False)
    event = Column(String, nullable=False)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)
