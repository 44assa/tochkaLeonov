"""
Order management API endpoints.
"""
import uuid
from datetime import timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from api.v1.auth.jwt import get_current_user
from db_utils.symbol import get_symbol_by_ticker
from db_utils.order import (
    create_limit_sell_order,
    create_limit_buy_order,
    create_market_buy_order,
    create_market_sell_order,
    cancel_order,
    get_order
)
from db_utils.trader import get_trader_orders
from alchemy.models import Trader, OrderStatus, OrderSide, Order
from .schemas import (
    CreateOrderRequest,
    OrderResponse,
    CreateOrderResponse,
    DeleteOrderResponse,
    OrderBodyResponse
)


router = APIRouter()


def _format_order_response(order: Order) -> OrderResponse:
    """
    Format order model to response schema.
    
    Args:
        order: Order database model
        
    Returns:
        Formatted order response
    """
    timestamp_utc = order.created_at.astimezone(timezone.utc)
    formatted_timestamp = timestamp_utc.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    
    direction_str = "BUY" if order.direction == OrderSide.BID else "SELL"
    
    return OrderResponse(
        id=order.id,
        status=order.status.value,
        trader_id=order.trader_id,
        timestamp=formatted_timestamp,
        body=OrderBodyResponse(
            direction=direction_str,
            symbol_ticker=order.symbol_ticker,
            qty=order.amount + order.filled,
            price=order.price
        ),
        filled=order.filled
    )


@router.get('', response_model=List[OrderResponse])
async def list_orders(trader: Trader = Depends(get_current_user)) -> List[OrderResponse]:
    """
    Get all orders for the authenticated trader.
    
    Args:
        trader: Authenticated trader from JWT token
        
    Returns:
        List of all trader's orders
    """
    orders = await get_trader_orders(str(trader.id))
    return [_format_order_response(order) for order in orders]


@router.get('/{order_id}', response_model=OrderResponse)
async def get_order_by_id(
    order_id: uuid.UUID,
    trader: Trader = Depends(get_current_user)
) -> OrderResponse:
    """
    Get a specific order by ID.
    
    Args:
        order_id: Order ID
        trader: Authenticated trader from JWT token
        
    Returns:
        Order details
        
    Raises:
        HTTPException: 404 if order not found, 403 if order doesn't belong to trader
    """
    order = await get_order(str(order_id))
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    if order.trader_id != trader.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return _format_order_response(order)


@router.delete('/{order_id}', response_model=DeleteOrderResponse)
async def delete_order_by_id(
    order_id: uuid.UUID,
    trader: Trader = Depends(get_current_user)
) -> DeleteOrderResponse:
    """
    Cancel a specific order by ID.
    
    Args:
        order_id: Order ID to cancel
        trader: Authenticated trader from JWT token
        
    Returns:
        Success response
        
    Raises:
        HTTPException: 404 if order not found
    """
    canceled_order = await cancel_order(str(order_id), trader.id)
    if not canceled_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return DeleteOrderResponse(success=True)


@router.post('', response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: CreateOrderRequest,
    trader: Trader = Depends(get_current_user)
) -> CreateOrderResponse:
    """
    Create a new order (buy or sell, limit or market).
    
    Args:
        order_data: Order creation data
        trader: Authenticated trader from JWT token
        
    Returns:
        Created order response with order ID
        
    Raises:
        HTTPException: 404 if symbol not found, 422 if order was cancelled
    """
    symbol = await get_symbol_by_ticker(order_data.ticker)
    if not symbol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Symbol not found"
        )
    
    # Determine order type and create order
    created_order = None
    if order_data.direction == 'BUY':
        if order_data.price:
            created_order = await create_limit_buy_order(
                order_data.ticker,
                order_data.qty,
                order_data.price,
                trader
            )
        else:
            created_order = await create_market_buy_order(
                order_data.ticker,
                order_data.qty,
                trader
            )
    elif order_data.direction == 'SELL':
        if order_data.price:
            created_order = await create_limit_sell_order(
                order_data.ticker,
                order_data.qty,
                order_data.price,
                trader
            )
        else:
            created_order = await create_market_sell_order(
                order_data.ticker,
                order_data.qty,
                trader
            )
    
    if not created_order or created_order.status == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order cancelled due to insufficient funds or invalid parameters"
        )
    
    return CreateOrderResponse(success=True, order_id=created_order.id)
