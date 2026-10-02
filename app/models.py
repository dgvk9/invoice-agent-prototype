from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    quantity: float = Field(ge=0)
    unit_price: float = Field(ge=0)
    amount: float = Field(ge=0)


class InvoiceData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor: str = Field(min_length=1)
    invoice_number: str = Field(min_length=1)
    invoice_date: Optional[str] = None
    po_number: Optional[str] = None
    currency: str = Field(min_length=1)

    subtotal: Optional[float] = Field(default=None, ge=0)
    tax: Optional[float] = Field(default=None, ge=0)
    total: float = Field(ge=0)

    line_items: list[LineItem] = Field(min_length=1)


class PurchaseOrderData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    po_number: str = Field(min_length=1)
    vendor: str = Field(min_length=1)
    po_date: Optional[str] = None
    currency: str = Field(min_length=1)
    category: Optional[str] = None

    subtotal: Optional[float] = Field(default=None, ge=0)
    tax: Optional[float] = Field(default=None, ge=0)
    total: float = Field(ge=0)

    line_items: list[LineItem] = Field(min_length=1)


class InvoiceConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor: float = Field(ge=0, le=1)
    invoice_number: float = Field(ge=0, le=1)
    po_number: float = Field(ge=0, le=1)
    subtotal: float = Field(ge=0, le=1)
    tax: float = Field(ge=0, le=1)
    total: float = Field(ge=0, le=1)
    line_items: float = Field(ge=0, le=1)


class POConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    po_number: float = Field(ge=0, le=1)
    vendor: float = Field(ge=0, le=1)
    currency: float = Field(ge=0, le=1)
    subtotal: float = Field(ge=0, le=1)
    tax: float = Field(ge=0, le=1)
    total: float = Field(ge=0, le=1)
    line_items: float = Field(ge=0, le=1)


class InvoiceExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice: InvoiceData
    confidence: InvoiceConfidence


class POExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purchase_order: PurchaseOrderData
    confidence: POConfidence