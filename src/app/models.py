from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class ShipmentLog(Base):
    __tablename__ = "shipment_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    correlation_id = Column(String, index=True, nullable=False)
    tenant_id = Column(String, nullable=False)
    message_type = Column(String, nullable=False)
    raw_payload = Column(Text, nullable=False)
    healed_payload = Column(Text, nullable=True)
    status = Column(String, default="PROCESSING")  # PROCESSING, HEALED, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_primary=True, default=lambda: str(uuid.uuid4()))
    correlation_id = Column(String, index=True, nullable=False)
    rule_code = Column(String, nullable=False)
    field_xpath = Column(String, nullable=False)
    original_value = Column(String, nullable=True)
    healed_value = Column(String, nullable=True)
    healing_strategy = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)