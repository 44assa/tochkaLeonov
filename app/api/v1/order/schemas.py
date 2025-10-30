from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, constr, conint, field_validator


class CreateOrderRequest(BaseModel):
    """Request schema for creating an order."""
    direction: str = Field(..., description="Order direction: BUY or SELL")
    ticker: constr(min_length=2, max_length=10, pattern="^[A-Z]+$") = Field(..., description="Symbol ticker")
    qty: conint(gt=0) = Field(..., description="Order quantity")
    price: Optional[conint(gt=0)] = Field(None, description="Order price (required for limit orders)")

    @field_validator('direction')
    @classmethod
    def validate_direction(cls, value: str) -> str:
        """Validate order direction."""
        directions = ['BUY', 'SELL']
        if value.upper() not in directions:
            raise ValueError(f"Direction must be one of {directions}")
        return value.upper()


class OrderBodyResponse(BaseModel):
    """Response schema for order body details."""
    direction: str = Field(..., description="Order direction: BUY or SELL")
    symbol_ticker: str = Field(..., description="Symbol ticker")
    qty: int = Field(..., description="Total order quantity")
    price: int | None = Field(None, description="Order price")


class OrderResponse(BaseModel):
    """Response schema for order information."""
    id: UUID = Field(..., description="Order ID")
    status: str = Field(..., description="Order status")
    trader_id: UUID = Field(..., description="Trader ID")
    timestamp: str = Field(..., description="Order creation timestamp in ISO format")
    body: OrderBodyResponse = Field(..., description="Order details")
    filled: int = Field(..., description="Filled quantity")

    class Config:
        from_attributes = True


class CreateOrderResponse(BaseModel):
    """Response schema for order creation."""
    success: bool = Field(True, description="Operation success flag")
    order_id: UUID = Field(..., description="Created order ID")


class DeleteOrderResponse(BaseModel):
    """Response schema for order deletion."""
    success: bool = Field(True, description="Operation success flag")
