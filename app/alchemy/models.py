import uuid
from datetime import datetime
from enum import Enum as PythonEnum
from typing import List, Optional

from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alchemy.database import Base

class TraderRole(PythonEnum):
    USER = "user"
    ADMIN = "admin"

class OrderSide(PythonEnum):
    ASK = "ask"
    BID = "bid"

class OrderStatus(PythonEnum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"

class Trader(Base):
    __tablename__ = 'traders'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[TraderRole] = mapped_column(Enum(TraderRole), default=TraderRole.USER)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    api_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # relations
    orders: Mapped[List['Order']] = relationship(
        "Order", back_populates="trader", cascade="all, delete-orphan", passive_deletes=True
    )
    trades_sent: Mapped[List['Trade']] = relationship(
        "Trade", foreign_keys='Trade.trader_from_id', back_populates="from_trader"
    )
    trades_received: Mapped[List['Trade']] = relationship(
        "Trade", foreign_keys='Trade.trader_to_id', back_populates="to_trader"
    )
    positions: Mapped[List['Position']] = relationship(
        "Position", back_populates="trader", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"Trader(id={self.id}, name={self.name}, role={self.role.name}, balance={self.balance})"

class Position(Base):
    __tablename__ = 'positions'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('traders.id', ondelete="CASCADE"), nullable=False, index=True)
    symbol_ticker: Mapped[str] = mapped_column(String(10), ForeignKey('symbols.ticker', ondelete="CASCADE"), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # relations
    trader: Mapped['Trader'] = relationship("Trader", back_populates="positions")
    symbol: Mapped['Symbol'] = relationship("Symbol", back_populates="positions")

    def __repr__(self) -> str:
        return f"Position(id={self.id}, trader_id={self.trader_id}, symbol_ticker={self.symbol_ticker}, qty={self.quantity})"


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('traders.id', ondelete="CASCADE"), nullable=False, index=True)
    symbol_ticker: Mapped[str] = mapped_column(String(10), ForeignKey('symbols.ticker', ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    filled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    direction: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.NEW)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # relations
    trader: Mapped['Trader'] = relationship("Trader", back_populates="orders")
    symbol: Mapped['Symbol'] = relationship("Symbol", back_populates="orders")

    def __repr__(self) -> str:
        return (
            f"Order(id={self.id}, trader_id={self.trader_id}, symbol_ticker={self.symbol_ticker}, "
            f"amount={self.amount}, filled={self.filled}, price={self.price}, "
            f"direction={self.direction.name}, status={self.status.name})"
        )


class Trade(Base):
    __tablename__ = 'trades'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('traders.id', ondelete="SET NULL"), nullable=True, index=True)
    trader_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('traders.id', ondelete="SET NULL"), nullable=True, index=True)
    symbol_ticker: Mapped[Optional[str]] = mapped_column(String(10), ForeignKey('symbols.ticker', ondelete="SET NULL"), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # relations
    from_trader: Mapped[Optional['Trader']] = relationship("Trader", foreign_keys=[trader_from_id], back_populates="trades_sent")
    to_trader: Mapped[Optional['Trader']] = relationship("Trader", foreign_keys=[trader_to_id], back_populates="trades_received")
    symbol: Mapped[Optional['Symbol']] = relationship("Symbol", back_populates="trades")

    def __repr__(self) -> str:
        return (
            f"Trade(id={self.id}, from={self.trader_from_id}, to={self.trader_to_id}, "
            f"symbol_ticker={self.symbol_ticker}, amount={self.amount}, price={self.price})"
        )


class Symbol(Base):
    __tablename__ = 'symbols'

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # backrefs
    positions: Mapped[List['Position']] = relationship(
        "Position", back_populates="symbol", cascade="all, delete-orphan", passive_deletes=True
    )
    orders: Mapped[List['Order']] = relationship(
        "Order", back_populates="symbol", cascade="all, delete-orphan", passive_deletes=True
    )
    trades: Mapped[List['Trade']] = relationship("Trade", back_populates="symbol")

    def __repr__(self) -> str:
        return f"Symbol(ticker={self.ticker}, name={self.name})"

# Helpful indexes (do not change logic; optimize common lookups)
Index('ix_position_trader_symbol', Position.trader_id, Position.symbol_ticker, unique=True)
Index('ix_order_symbol_status', Order.symbol_ticker, Order.status)
Index('ix_trade_symbol_time', Trade.symbol_ticker, Trade.timestamp)
