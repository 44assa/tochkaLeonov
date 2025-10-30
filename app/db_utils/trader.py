import os
import uuid
from typing import Optional, List, Union

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from alchemy.models import Trader, TraderRole, Symbol, Position, Order
from alchemy.database import async_session_maker


BASE_CURRENCY_TICKER = os.getenv('BASE_SYMBOL')


async def create_trader(name: str, role: TraderRole = TraderRole.USER) -> Trader:
    """Create a new trader with initial positions for all symbols."""
    async with async_session_maker() as session:
        new_trader = Trader(name=name, role=role)
        session.add(new_trader)

        result = await session.execute(select(Symbol))
        symbols = result.scalars().all()
        
        for symbol in symbols:
            position = Position(trader=new_trader, symbol=symbol, quantity=0.0)
            session.add(position)

        await session.commit()
        await session.refresh(new_trader)
        return new_trader


async def get_trader(trader_id: str) -> Optional[Trader]:
    """Get trader by ID."""
    async with async_session_maker() as session:
        trader_uuid = uuid.UUID(trader_id)
        query = select(Trader).where(Trader.id == trader_uuid)
        result = await session.execute(query)
        return result.scalars().first()


async def apply_trader_api_key(trader_id: str, api_key: str) -> Trader:
    """Update trader's API key."""
    async with async_session_maker() as session:
        trader = await get_trader(trader_id)
        trader.api_key = api_key
        session.add(trader)
        await session.commit()
        return trader


async def delete_trader(trader_id: str) -> Optional[Trader]:
    """Delete trader by ID."""
    async with async_session_maker() as session:
        trader = await get_trader(trader_id)
        if not trader:
            raise HTTPException(status_code=404, detail='Пользователь с таким id не найден')
        await session.delete(trader)
        await session.commit()
        return trader


async def change_trader_balance(
    trader_id: Union[uuid.UUID, str],
    symbol_ticker: str,
    amount: int
) -> Optional[Trader]:
    """Change trader's balance or position for a symbol."""
    async with async_session_maker() as session:
        trader = await __change_balance(session, trader_id, symbol_ticker, amount)
        await session.commit()
        await session.refresh(trader)
        return trader


async def __change_balance(
    session: AsyncSession,
    trader_id: Union[uuid.UUID, str],
    symbol_ticker: str,
    amount: int
) -> Optional[Trader]:
    """Internal helper to change balance without committing."""
    trader_id_str = str(trader_id)
    
    if symbol_ticker == BASE_CURRENCY_TICKER:
        trader = await session.get(Trader, uuid.UUID(trader_id_str))
        if trader is None:
            trader = await get_trader(trader_id_str)
        
        new_balance = trader.balance + amount
        if new_balance < 0:
            raise HTTPException(status_code=400, detail='Balance must be >= 0')
        
        trader.balance = new_balance
        session.add(trader)
    else:
        query = (
            select(Trader)
            .where(Trader.id == uuid.UUID(trader_id_str))
            .options(selectinload(Trader.positions))
        )
        result = await session.execute(query)
        trader = result.scalar_one_or_none()
        
        for position in trader.positions:
            if position.symbol_ticker == symbol_ticker:
                new_balance = position.quantity + amount
                if new_balance < 0:
                    raise HTTPException(status_code=400, detail='Balance must be >= 0')
                
                position.quantity = new_balance
                session.add(position)
                break

    return trader


async def get_trader_orders(trader_id: str) -> List[Order]:
    """Get all orders for a trader."""
    async with async_session_maker() as session:
        query = select(Order).where(Order.trader_id == uuid.UUID(trader_id))
        result = await session.execute(query)
        return result.scalars().all()
