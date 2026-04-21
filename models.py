from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class PaymentStatusEnum(str, enum.Enum):
    unpaid = "unpaid"
    pending = "pending"
    paid = "paid"


class VATRateEnum(str, enum.Enum):
    standard = "19"
    reduced = "7"
    none = "0"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    company_address = Column(Text)
    company_vat_id = Column(String)
    company_phone = Column(String)
    company_email = Column(String)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customers = relationship("Customer", back_populates="owner", cascade="all, delete")
    invoices = relationship("Invoice", back_populates="owner", cascade="all, delete")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String)
    address = Column(Text)
    city = Column(String)
    postal_code = Column(String)
    country = Column(String, default="Germany")
    vat_id = Column(String)
    phone = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="customers")
    invoices = relationship("Invoice", back_populates="customer")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    invoice_number = Column(String, nullable=False)
    issue_date = Column(String, nullable=False)
    due_date = Column(String, nullable=False)
    status = Column(String, default=PaymentStatusEnum.unpaid)
    notes = Column(Text)
    subtotal = Column(Float, default=0.0)
    vat_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    currency = Column(String, default="EUR")
    tax_free = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    unit_price = Column(Float, nullable=False)
    vat_rate = Column(String, default=VATRateEnum.standard)
    line_total = Column(Float, default=0.0)
    vat_amount = Column(Float, default=0.0)

    invoice = relationship("Invoice", back_populates="items")
