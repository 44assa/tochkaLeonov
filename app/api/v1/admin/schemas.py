from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field, constr, field_validator


class SymbolCreateRequest(BaseModel):
    """Request schema for creating a symbol."""
    name: str = Field(..., min_length=1, description="Symbol name")
    ticker: constr(pattern="^[A-Z]{2,10}$") = Field(..., description="Symbol ticker")


class BalanceChangeRequest(BaseModel):
    """Request schema for balance change operations."""
    trader_id: UUID = Field(..., description="Trader ID")
    ticker: constr(min_length=2, max_length=10, pattern="^[A-Z]+$") = Field(..., description="Symbol ticker")
    amount: int = Field(..., gt=0, description="Amount to change")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, value: int) -> int:
        """Validate that amount is positive."""
        if value <= 0:
            raise ValueError("Amount must be greater than 0")
        return value


class TraderDeleteResponse(BaseModel):
    """Response schema for trader deletion."""
    id: UUID = Field(..., description="Deleted trader ID")
    name: str = Field(..., description="Deleted trader name")
    role: str = Field(..., description="Deleted trader role")
    api_key: Optional[str] = Field(None, description="Deleted trader API key")


class SuccessResponse(BaseModel):
    """Generic success response schema."""
    success: bool = Field(True, description="Operation success flag")
