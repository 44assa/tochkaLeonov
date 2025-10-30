from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alchemy.database import async_session_maker
from alchemy.models import Trade, Symbol


async def get_trades_by_ticker(symbol_ticker: str, limit: int = 10) -> List[Trade]:
    """Get recent trades for a symbol."""
    async with async_session_maker() as session:
        query = (
            select(Trade)
            .join(Trade.symbol)
            .filter(Symbol.ticker == symbol_ticker)
            .order_by(Trade.timestamp.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return result.scalars().all()


async def create_trade(
    trader_from_id: str,
    trader_to_id: str,
    symbol_ticker: str,
    amount: int,
    price: float
) -> Trade:
    """Create a new trade record."""
    async with async_session_maker() as session:
        trade = await __create_trade(
            session,
            trader_from_id,
            trader_to_id,
            symbol_ticker,
            amount,
            price
        )
        await session.commit()
        await session.refresh(trade)
        return trade


async def __create_trade(
    session: AsyncSession,
    trader_from_id: str,
    trader_to_id: str,
    symbol_ticker: str,
    amount: int,
    price: float
) -> Trade:
    """Internal helper to create trade without committing."""
    trade_entry = Trade(
        trader_from_id=trader_from_id,
        trader_to_id=trader_to_id,
        symbol_ticker=symbol_ticker,
        amount=amount,
        price=price
    )
    session.add(trade_entry)
    return trade_entry


__all__ = ['get_trades_by_ticker', 'create_trade']
