"""
Public API endpoints - accessible without authentication.
"""
from datetime import timezone
from collections import defaultdict
from typing import List

from fastapi import APIRouter, Depends, status

from api.v1.auth.jwt import create_access_token
from depends import get_symbol_depend
from alchemy.models import OrderSide, Symbol
from db_utils.trader import create_trader
from db_utils.symbol import get_all_symbols
from db_utils.order import get_orders
from db_utils.trade import get_trades_by_ticker
from .schemas import (
    TraderAuth,
    RegisterResponse,
    SymbolResponse,
    OrderLevelResponse,
    OrderBookResponse,
    TradeResponse
)


router = APIRouter()


@router.post('/register', response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(trader_data: TraderAuth) -> RegisterResponse:
    """
    Register a new trader.
    
    Args:
        trader_data: Trader registration data
        
    Returns:
        Registration response with trader info and API key
    """
    trader = await create_trader(trader_data.name)
    
    token_data = {
        "name": trader.name,
        "id": str(trader.id),
        "role": trader.role.name
    }
    api_key = create_access_token(token_data)
    
    return RegisterResponse(
        name=trader.name,
        id=trader.id,
        role=trader.role.name,
        api_key=api_key
    )


@router.get('/instrument', response_model=List[SymbolResponse])
async def get_symbols() -> List[SymbolResponse]:
    """
    Get list of all available symbols.
    
    Returns:
        List of symbols with name and ticker
    """
    symbols = await get_all_symbols()
    return [SymbolResponse(name=symbol.name, ticker=symbol.ticker) for symbol in symbols]


@router.get('/orderbook/{ticker}', response_model=OrderBookResponse)
async def get_orderbook(
    symbol: Symbol = Depends(get_symbol_depend),
    limit: int = 10
) -> OrderBookResponse:
    """
    Get order book for a symbol.
    
    Args:
        symbol: Symbol from path parameter
        limit: Maximum number of levels to return per side
        
    Returns:
        Order book with bid and ask levels aggregated by price
    """
    ticker = symbol.ticker

    async def aggregate_orders(direction: OrderSide) -> List[OrderLevelResponse]:
        """Aggregate orders by price for a given direction."""
        orders = await get_orders(ticker, direction, limit=limit)
        aggregated = defaultdict(int)
        for order in orders:
            if order.price:
                aggregated[order.price] += order.amount
        
        sorted_items = sorted(
            aggregated.items(),
            reverse=(direction == OrderSide.BID)
        )
        return [
            OrderLevelResponse(price=price, qty=qty)
            for price, qty in sorted_items
        ]

    bid_levels = await aggregate_orders(OrderSide.BID)
    ask_levels = await aggregate_orders(OrderSide.ASK)

    return OrderBookResponse(bid_levels=bid_levels, ask_levels=ask_levels)


@router.get('/transactions/{ticker}', response_model=List[TradeResponse])
async def get_trades(
    symbol: Symbol = Depends(get_symbol_depend),
    limit: int = 10
) -> List[TradeResponse]:
    """
    Get recent trades for a symbol.
    
    Args:
        symbol: Symbol from path parameter
        limit: Maximum number of trades to return
        
    Returns:
        List of recent trades with price, amount, and timestamp
    """
    ticker = symbol.ticker
    trades = await get_trades_by_ticker(ticker, limit)
    
    return [
        TradeResponse(
            symbol_ticker=trade.symbol_ticker or ticker,
            amount=trade.amount,
            price=trade.price,
            timestamp=trade.timestamp.astimezone(timezone.utc).isoformat(
                timespec='milliseconds'
            ).replace('+00:00', 'Z')
        )
        for trade in trades
    ]
