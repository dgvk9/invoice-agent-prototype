from pydantic import BaseModel
from typing import List, Optional


class InvoiceLineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float


class Invoice(BaseModel):
    vendor: str
    invoice_number: str
    invoice_date: Optional[str] = None
    po_number: Optional[str] = None
    currency: str
    subtotal: float
    tax: float
    total: float
    line_items: List[InvoiceLineItem]
