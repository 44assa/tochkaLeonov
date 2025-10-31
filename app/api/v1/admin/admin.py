"""
Admin API endpoints - accessible only to administrators.
"""
import os

from fastapi import APIRouter, Depends, HTTPException, status

from api.v1.admin.schemas import (
    SymbolCreateRequest,
    BalanceChangeRequest,
    SuccessResponse,
    TraderDeleteResponse
)
from api.v1.auth.jwt import get_current_admin
from db_utils.symbol import create_symbol, get_symbol_by_ticker, delete_symbol
from db_utils.trader import get_trader, change_trader_balance, delete_trader
from alchemy.models import Trader, Symbol
from depends import get_symbol_depend, get_user_depend


router = APIRouter()


@router.post('/instrument', response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_symbol_endpoint(
    symbol_data: SymbolCreateRequest,
    admin: Trader = Depends(get_current_admin)
) -> SuccessResponse:
    """
    Create a new trading symbol (admin only).
    
    Args:
        symbol_data: Symbol creation data
        admin: Authenticated admin trader
        
    Returns:
        Success response
        
    Raises:
        HTTPException: 422 if symbol already exists
    """
    existing_symbol = await get_symbol_by_ticker(symbol_data.ticker)
    if existing_symbol:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Symbol with this ticker already exists"
        )
    
    await create_symbol(symbol_data.name, symbol_data.ticker)
    return SuccessResponse(success=True)


@router.delete('/instrument/{ticker}', response_model=SuccessResponse)
async def delete_symbol_endpoint(
    symbol: Symbol = Depends(get_symbol_depend),
    admin: Trader = Depends(get_current_admin)
) -> SuccessResponse:
    """
    Delete a trading symbol (admin only).
    
    Args:
        symbol: Symbol from path parameter
        admin: Authenticated admin trader
        
    Returns:
        Success response
    """
    await delete_symbol(symbol.ticker)
    return SuccessResponse(success=True)


@router.post('/balance/deposit', response_model=SuccessResponse)
async def deposit_balance(
    balance_data: BalanceChangeRequest,
    admin: Trader = Depends(get_current_admin)
) -> SuccessResponse:
    """
    Deposit balance to a trader's account (admin only).
    
    Args:
        balance_data: Balance change data
        admin: Authenticated admin trader
        
    Returns:
        Success response
        
    Raises:
        HTTPException: 404 if trader or symbol not found
    """
    trader = await get_trader(str(balance_data.trader_id))
    if not trader:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trader not found"
        )
    
    # Validate symbol if not base currency
    base_symbol = os.getenv('BASE_SYMBOL')
    if balance_data.ticker != base_symbol:
        symbol = await get_symbol_by_ticker(balance_data.ticker)
        if not symbol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Symbol not found"
            )
    
    await change_trader_balance(
        str(balance_data.trader_id),
        balance_data.ticker,
        balance_data.amount
    )
    
    return SuccessResponse(success=True)


@router.post('/balance/withdraw', response_model=SuccessResponse)
async def withdraw_balance(
    balance_data: BalanceChangeRequest,
    admin: Trader = Depends(get_current_admin)
) -> SuccessResponse:
    """
    Withdraw balance from a trader's account (admin only).
    
    Args:
        balance_data: Balance change data (amount will be withdrawn)
        admin: Authenticated admin trader
        
    Returns:
        Success response
        
    Raises:
        HTTPException: 404 if trader or symbol not found
    """
    trader = await get_trader(str(balance_data.trader_id))
    if not trader:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trader not found"
        )
    
    # Validate symbol if not base currency
    base_symbol = os.getenv('BASE_SYMBOL')
    if balance_data.ticker != base_symbol:
        symbol = await get_symbol_by_ticker(balance_data.ticker)
        if not symbol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Symbol not found"
            )
    
    await change_trader_balance(
        str(balance_data.trader_id),
        balance_data.ticker,
        -balance_data.amount
    )
    
    return SuccessResponse(success=True)


@router.delete('/user/{user_id}', response_model=TraderDeleteResponse)
async def delete_trader_endpoint(
    trader_to_delete: Trader = Depends(get_user_depend),
    admin: Trader = Depends(get_current_admin)
) -> TraderDeleteResponse:
    """
    Delete a trader (admin only).
    
    Args:
        trader_to_delete: Trader to delete from path parameter
        admin: Authenticated admin trader
        
    Returns:
        Deleted trader information
    """
    deleted_trader = await delete_trader(str(trader_to_delete.id))
    
    return TraderDeleteResponse(
        id=deleted_trader.id if deleted_trader else trader_to_delete.id,
        name=deleted_trader.name if deleted_trader else trader_to_delete.name,
        role=deleted_trader.role.name if deleted_trader else trader_to_delete.role.name,
        api_key=deleted_trader.api_key if deleted_trader else trader_to_delete.api_key
    )
