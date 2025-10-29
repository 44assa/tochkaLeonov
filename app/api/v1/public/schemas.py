from pydantic import BaseModel, Field
from typing import List
from uuid import UUID


class TraderAuth(BaseModel):
    """Request schema for trader registration."""
    name: str = Field(..., min_length=3, description="Trader name")


# Backward compatibility alias
UserAuth = TraderAuth


class SymbolResponse(BaseModel):
    """Response schema for symbol information."""
    name: str = Field(..., description="Symbol name")
    ticker: str = Field(..., description="Symbol ticker")

    class Config:
        from_attributes = True


class OrderLevelResponse(BaseModel):
    """Response schema for order book level."""
    price: int = Field(..., description="Order price")
    qty: int = Field(..., description="Order quantity")


class OrderBookResponse(BaseModel):
    """Response schema for order book."""
    bid_levels: List[OrderLevelResponse] = Field(..., description="Bid order levels")
    ask_levels: List[OrderLevelResponse] = Field(..., description="Ask order levels")


class TradeResponse(BaseModel):
    """Response schema for trade information."""
    symbol_ticker: str = Field(..., description="Symbol ticker")
    amount: float = Field(..., description="Trade amount")
    price: float | None = Field(None, description="Trade price")
    timestamp: str = Field(..., description="Trade timestamp in ISO format")

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    """Response schema for trader registration."""
    name: str = Field(..., description="Trader name")
    id: UUID = Field(..., description="Trader ID")
    role: str = Field(..., description="Trader role")
    api_key: str = Field(..., description="API key for authentication")
