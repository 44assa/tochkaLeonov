import os
from uuid import UUID
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select, asc, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db_utils.trader import __change_balance
from alchemy.database import async_session_maker
from alchemy.models import Order, OrderSide, Trader, OrderStatus, Trade, Position


BASE_CURRENCY_TICKER = os.getenv('BASE_SYMBOL')
FINAL_ORDER_STATUSES = {OrderStatus.PARTIALLY_EXECUTED, OrderStatus.EXECUTED, OrderStatus.CANCELLED}
ACTIVE_ORDER_STATUSES = [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]


async def delete_all_orders() -> None:
    """Delete all orders from database."""
    async with async_session_maker() as session:
        await session.execute(delete(Order))
        await session.commit()


async def cancel_order(order_id: str, trader_id: UUID) -> Optional[Order]:
    """Cancel an order if it's still active."""
    async with async_session_maker() as session:
        query = select(Order).where(
            Order.id == order_id,
            Order.trader_id == trader_id
        )
        result = await session.execute(query)
        order = result.scalars().first()
        
        if not order:
            return None

        if order.status in FINAL_ORDER_STATUSES:
            raise HTTPException(400, 'Order executed/partially_executed/cancelled')
        
        if order.price is None:
            raise HTTPException(400, 'Order is market')

        # Return funds/instruments based on order direction
        if order.direction == OrderSide.ASK:
            await __change_balance(session, order.trader_id, order.symbol_ticker, order.amount)
        elif order.direction == OrderSide.BID:
            await __change_balance(session, order.trader_id, BASE_CURRENCY_TICKER, order.amount * order.price)
        
        order.status = OrderStatus.CANCELLED
        session.add(order)
        await session.flush()
        await session.refresh(order)
        await session.commit()
        return order


async def get_order(order_id: str) -> Optional[Order]:
    """Get order by ID."""
    async with async_session_maker() as session:
        query = select(Order).where(Order.id == order_id)
        result = await session.execute(query)
        return result.scalars().first()


async def get_orders(symbol_ticker: str, direction: OrderSide, limit: int = 10) -> List[Order]:
    """Get active orders for a symbol and direction."""
    async with async_session_maker() as session:
        return await __get_orders(session, symbol_ticker, direction, limit)


async def __get_orders(
    session: AsyncSession,
    symbol_ticker: str,
    direction: OrderSide,
    limit: int = 10
) -> List[Order]:
    """Internal helper to get orders from orderbook."""
    query = (
        select(Order)
        .filter(
            Order.symbol_ticker == symbol_ticker,
            Order.direction == direction.name,
            Order.status.in_(ACTIVE_ORDER_STATUSES)
        )
        .order_by(
            desc(Order.price) if direction == OrderSide.BID else asc(Order.price),
            Order.created_at
        )
        .limit(limit)
    )
    result = await session.execute(query)
    return result.scalars().all()


async def create_limit_buy_order(
    symbol_ticker: str,
    quantity: int,
    price: Optional[int],
    trader: Trader
) -> Order:
    """Create a limit buy order and try to match it immediately."""
    async with async_session_maker() as session:
        orderbook = await __get_orders(session, symbol_ticker, OrderSide.ASK, quantity)
        
        new_order = Order(
            trader_id=trader.id,
            symbol_ticker=symbol_ticker,
            amount=quantity,
            filled=0,
            price=price,
            direction=OrderSide.BID,
            status=OrderStatus.NEW
        )
        
        try:
            # Match orders from orderbook
            for matching_order in orderbook:
                if new_order.amount == 0 or (price is not None and matching_order.price > price):
                    break
                
                quantity_to_buy = min(matching_order.amount, new_order.amount)
                await buy(
                    session,
                    matching_order.trader_id,
                    trader.id,
                    symbol_ticker,
                    matching_order.price,
                    quantity_to_buy
                )
                await partially_execute_order(session, matching_order, quantity_to_buy)
                await partially_execute_order(session, new_order, quantity_to_buy)

            # Freeze balance for remaining order amount
            if new_order.status != OrderStatus.EXECUTED:
                if price is not None:
                    await freeze_balance(
                        session,
                        trader.id,
                        BASE_CURRENCY_TICKER,
                        new_order.amount * new_order.price
                    )
                else:
                    raise Exception('Not enough orders')

            session.add(new_order)
            await session.commit()
            return new_order

        except Exception as e:
            # Insufficient funds
            print(e)
            await session.rollback()
            new_order.filled = 0
            new_order.amount = quantity
            new_order.status = OrderStatus.CANCELLED
            session.add(new_order)
            await session.commit()
            return new_order


async def create_limit_sell_order(
    symbol_ticker: str,
    quantity: int,
    price: Optional[int],
    trader: Trader
) -> Order:
    """Create a limit sell order and try to match it immediately."""
    async with async_session_maker() as session:
        orderbook = await __get_orders(session, symbol_ticker, OrderSide.BID, quantity)
        
        new_order = Order(
            trader_id=trader.id,
            symbol_ticker=symbol_ticker,
            amount=quantity,
            filled=0,
            price=price,
            direction=OrderSide.ASK,
            status=OrderStatus.NEW
        )
        
        try:
            # Match orders from orderbook
            for matching_order in orderbook:
                if new_order.amount == 0 or (price is not None and matching_order.price < price):
                    break
                
                quantity_to_sell = min(matching_order.amount, new_order.amount)
                await sell(
                    session,
                    trader.id,
                    matching_order.trader_id,
                    symbol_ticker,
                    matching_order.price,
                    quantity_to_sell
                )
                await partially_execute_order(session, matching_order, quantity_to_sell)
                await partially_execute_order(session, new_order, quantity_to_sell)

            # Freeze instruments for remaining order amount
            if new_order.status != OrderStatus.EXECUTED:
                if price is not None:
                    await freeze_balance(session, trader.id, symbol_ticker, new_order.amount)
                else:
                    raise Exception('Not enough orders')

            session.add(new_order)
            await session.commit()
            return new_order

        except Exception as e:
            # Insufficient instruments
            print(e)
            await session.rollback()
            new_order.filled = 0
            new_order.amount = quantity
            new_order.status = OrderStatus.CANCELLED
            session.add(new_order)
            await session.commit()
            return new_order


async def create_market_buy_order(
    symbol_ticker: str,
    quantity: int,
    trader: Trader
) -> Order:
    """Create a market buy order."""
    return await create_limit_buy_order(symbol_ticker, quantity, None, trader)


async def create_market_sell_order(
    symbol_ticker: str,
    quantity: int,
    trader: Trader
) -> Order:
    """Create a market sell order."""
    return await create_limit_sell_order(symbol_ticker, quantity, None, trader)


async def buy(
    session: AsyncSession,
    seller_id: UUID,
    buyer_id: UUID,
    symbol_ticker: str,
    price: int,
    amount: int
) -> Trade:
    """Execute a buy trade: transfer symbol from seller to buyer and update balances."""
    buyer_trader = await session.get(Trader, buyer_id)
    seller_trader = await session.get(Trader, seller_id)

    query = select(Position).where(
        Position.trader_id == buyer_id,
        Position.symbol_ticker == symbol_ticker
    )
    buyer_position = (await session.execute(query)).scalars().first()

    if buyer_trader.balance < amount * price:
        raise Exception('Not enough balance')

    trade_record = Trade(
        trader_from_id=seller_id,
        trader_to_id=buyer_id,
        symbol_ticker=symbol_ticker,
        amount=amount,
        price=price
    )
    session.add(trade_record)
    
    seller_trader.balance += amount * price
    buyer_trader.balance -= amount * price
    buyer_position.quantity += amount

    await session.flush()
    return trade_record


async def sell(
    session: AsyncSession,
    seller_id: UUID,
    buyer_id: UUID,
    symbol_ticker: str,
    price: int,
    amount: int
) -> Trade:
    """Execute a sell trade: transfer symbol from seller to buyer and update balances."""
    seller_trader = await session.get(Trader, seller_id)

    seller_query = select(Position).where(
        Position.trader_id == seller_id,
        Position.symbol_ticker == symbol_ticker
    )
    seller_position = (await session.execute(seller_query)).scalars().first()

    buyer_query = select(Position).where(
        Position.trader_id == buyer_id,
        Position.symbol_ticker == symbol_ticker
    )
    buyer_position = (await session.execute(buyer_query)).scalars().first()

    if seller_position.quantity < amount:
        raise Exception('Not enough instruments')

    trade_record = Trade(
        trader_from_id=seller_id,
        trader_to_id=buyer_id,
        symbol_ticker=symbol_ticker,
        amount=amount,
        price=price
    )
    session.add(trade_record)
    
    seller_trader.balance += amount * price
    seller_position.quantity -= amount
    buyer_position.quantity += amount

    await session.flush()
    return trade_record


async def partially_execute_order(
    session: AsyncSession,
    order: Order,
    amount: int
) -> None:
    """Partially execute an order by reducing amount and increasing filled."""
    if order.amount < amount:
        raise Exception('Order not enough amount')
    
    order.amount -= amount
    order.filled += amount
    order.status = (
        OrderStatus.EXECUTED
        if order.amount == 0
        else OrderStatus.PARTIALLY_EXECUTED
    )
    await session.flush()


async def freeze_balance(
    session: AsyncSession,
    trader_id: UUID,
    symbol_ticker: str,
    amount: int
) -> None:
    """Freeze trader's balance or position for an order."""
    trader = await session.get(Trader, trader_id)
    
    if symbol_ticker == BASE_CURRENCY_TICKER:
        balance = trader.balance
        if balance < amount:
            raise Exception('Trader not enough balance/instruments')
        trader.balance -= amount
    else:
        query = select(Position).where(
            Position.trader_id == trader.id,
            Position.symbol_ticker == symbol_ticker
        )
        position = (await session.execute(query)).scalars().first()
        
        balance = position.quantity
        if balance < amount:
            raise Exception('Trader not enough balance/instruments')
        position.quantity -= amount
    
    await session.flush()


async def unfreeze_balance(
    session: AsyncSession,
    trader_id: UUID,
    symbol_ticker: str,
    amount: int
) -> None:
    """Unfreeze trader's balance or position after order cancellation."""
    if symbol_ticker == BASE_CURRENCY_TICKER:
        trader = await session.get(Trader, trader_id)
        trader.balance += amount
    else:
        query = select(Position).where(
            Position.trader_id == trader_id,
            Position.symbol_ticker == symbol_ticker
        )
        position = (await session.execute(query)).scalars().first()
        position.quantity += amount
    
    await session.flush()
