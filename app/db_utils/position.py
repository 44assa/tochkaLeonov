import uuid
from typing import List, Optional

from sqlalchemy import select
from alchemy.database import async_session_maker
from alchemy.models import Position


async def get_trader_positions(
    trader_id: uuid.UUID,
    symbol_ticker: Optional[str] = None
) -> List[Position]:
    """Get trader's positions, optionally filtered by symbol ticker."""
    async with async_session_maker() as session:
        query = select(Position).where(Position.trader_id == trader_id)
        
        if symbol_ticker:
            query = query.where(Position.symbol_ticker == symbol_ticker)
        
        result = await session.execute(query)
        return result.scalars().all()


__all__ = ['get_trader_positions']
