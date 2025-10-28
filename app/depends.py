import uuid

from fastapi import HTTPException

from db_utils.symbol import get_symbol_by_ticker
from db_utils.trader import get_trader
from alchemy.models import Symbol, Trader


async def get_symbol_depend(ticker: str) -> Symbol:
    """Dependency to get symbol by ticker from path parameter."""
    symbol = await get_symbol_by_ticker(ticker)
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return symbol


async def get_trader_depend(trader_id: uuid.UUID) -> Trader:
    """Dependency to get trader by ID from path parameter."""
    trader = await get_trader(str(trader_id))
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    return trader


async def get_user_depend(user_id: uuid.UUID) -> Trader:
    """Dependency to get trader by ID from path parameter (backward compatibility)."""
    trader = await get_trader(str(user_id))
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    return trader


# Backward compatibility aliases
get_instrument_depend = get_symbol_depend