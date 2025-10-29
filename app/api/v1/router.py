"""
Main API router for v1 endpoints.
"""
import os
from typing import Dict

from fastapi import APIRouter, Depends

from db_utils.trader import get_trader_orders
from db_utils.position import get_trader_positions
from alchemy.models import Trader, OrderStatus, OrderSide
from api.v1.auth.jwt import get_current_user
from .public.public import router as public_router
from .admin.admin import router as admin_router
from .order.order import router as order_router


router = APIRouter()
router.include_router(public_router, prefix='/public')
router.include_router(admin_router, prefix='/admin')
router.include_router(order_router, prefix='/order')


@router.get("/balance")
async def get_balance(trader: Trader = Depends(get_current_user)) -> Dict[str, float]:
    """
    Get trader's balance including all positions and frozen funds from active orders.
    
    Args:
        trader: Authenticated trader from JWT token
        
    Returns:
        Dictionary mapping symbol tickers to quantities, including base currency balance
    """
    positions = await get_trader_positions(trader.id)
    result: Dict[str, float] = {position.symbol_ticker: position.quantity for position in positions}
    
    # Add base currency balance
    base_symbol = os.getenv('BASE_SYMBOL')
    if base_symbol:
        result[base_symbol] = trader.balance
    
    # Add frozen funds from active orders
    orders = await get_trader_orders(str(trader.id))
    for order in orders:
        if order.status in [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]:
            if order.direction == OrderSide.ASK:
                # Sell order: freeze instruments
                result[order.symbol_ticker] = result.get(order.symbol_ticker, 0.0) + order.amount
            elif order.direction == OrderSide.BID:
                # Buy order: freeze base currency
                if order.price:
                    frozen_amount = order.amount * order.price
                    result[base_symbol] = result.get(base_symbol, 0.0) + frozen_amount
    
    return result
