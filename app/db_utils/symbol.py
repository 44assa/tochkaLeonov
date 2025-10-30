from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select

from alchemy.database import async_session_maker
from alchemy.models import Symbol, Trader, Position


async def create_symbol(name: str, ticker: str) -> Symbol:
    """Create a new symbol and initialize positions for all existing traders."""
    async with async_session_maker() as session:
        new_symbol = Symbol(name=name, ticker=ticker)
        session.add(new_symbol)

        result = await session.execute(select(Trader))
        traders = result.scalars().all()

        for trader in traders:
            position = Position(trader=trader, symbol=new_symbol, quantity=0.0)
            session.add(position)

        await session.commit()
        await session.refresh(new_symbol)
        return new_symbol


async def get_symbol_by_ticker(ticker: str) -> Optional[Symbol]:
    """Get symbol by ticker."""
    async with async_session_maker() as session:
        query = select(Symbol).where(Symbol.ticker == ticker)
        result = await session.execute(query)
        return result.scalars().first()


async def delete_symbol(ticker: str) -> Symbol:
    """Delete symbol by ticker."""
    async with async_session_maker() as session:
        symbol = await get_symbol_by_ticker(ticker)
        if not symbol:
            raise HTTPException(
                status_code=404,
                detail='Инструмент с данным ticker е найден'
            )
        await session.delete(symbol)
        await session.commit()
        return symbol


async def delete_all_symbols() -> None:
    """Delete all symbols."""
    symbols = await get_all_symbols()
    for symbol in symbols:
        await delete_symbol(symbol.ticker)


async def get_all_symbols() -> List[Symbol]:
    """Get all symbols."""
    async with async_session_maker() as session:
        query = select(Symbol)
        result = await session.execute(query)
        return result.scalars().all()
