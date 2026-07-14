from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Order:
    entity_id: int
    increment_id: str
    status: str
    estimated_delivery_datetime: Optional[datetime] = None
    shipping_city: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    shipping_address: Optional[str] = None
    carrier_code: Optional[str] = None
    tracking_number: Optional[str] = None
