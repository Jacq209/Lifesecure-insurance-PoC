from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ClaimCreate(BaseModel):
    """The data a customer or claims officer must send to file a claim."""

    policy_number: str = Field(..., min_length=3, max_length=30)
    incident_date: date
    description: Optional[str] = Field(None, max_length=1000)
    claim_amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)