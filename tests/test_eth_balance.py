import io
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from web3 import Web3
from web3.exceptions import Web3Exception

import eth_balance
from eth_balance import (
    get_eth_balance,
    get_reth_balance,
    get_market_price,
    _print_report,
)


def _make_w3(*, get_balance_return=0):
    """Build a Web3-like object that uses the real static helpers but a mocked RPC."""
    w3 = MagicMock()
    w3.is_address = Web3.is_address
    w3.from_wei = Web3.from_wei
    w3.eth.get_balance.return_value = get_balance_return
    return w3


def _make_reth_contract(*, balance=0, eth_value=0, exchange_rate=0):
    """Build a fake rETH contract whose .call()s return fixed Wei values."""
    contract = MagicMock()
    contract.functions.balanceOf.return_value.call.return_value = balance
    contract.functions.getEthValue.return_value.call.return_value = eth_value
    contract.functions.getExchangeRate.return_value.call.return_value = exchange_rate
    return contract


# --- get_eth_balance -----------------------------------------------------

def test_get_eth_balance_returns_decimal():
    w3 = _make_w3(get_balance_return=3 * 10**18)  # 3 ETH in Wei
    balance = get_eth_balance(w3, "0xA5bBB646e8fcD3637B6F11CD5E72083E085905E5")
    assert balance == Decimal("3")
    assert isinstance(balance, Decimal)


def test_get_eth_balance_zero():
    w3 = _make_w3(get_balance_return=0)
    assert get_eth_balance(w3, "0xA5bBB646e8fcD3637B6F11CD5E72083E085905E5") == Decimal("0")


def test_get_eth_balance_invalid_address_raises():
    w3 = _make_w3()
    with pytest.raises(ValueError, match="Invalid Ethereum address"):
        get_eth_balance(w3, "not-an-address")


# --- get_reth_balance ----------------------------------------------------

def test_get_reth_balance_returns_three_decimals():
    w3 = _make_w3()
    # 10 rETH, 12 ETH equivalent, exchange rate 1.2 (all in Wei)
    contract = _make_reth_contract(
        balance=10 * 10**18,
        eth_value=12 * 10**18,
        exchange_rate=int(1.2 * 10**18),
    )
    balance_reth, eth_equivalent, rate = get_reth_balance(
        w3, contract, "0xA5bBB646e8fcD3637B6F11CD5E72083E085905E5"
    )
    assert balance_reth == Decimal("10")
    assert eth_equivalent == Decimal("12")
    assert rate == Decimal("1.2")
    assert isinstance(balance_reth, Decimal)
    assert isinstance(eth_equivalent, Decimal)
    assert isinstance(rate, Decimal)


def test_get_reth_balance_invalid_address_raises():
    w3 = _make_w3()
    contract = _make_reth_contract()
    with pytest.raises(ValueError, match="Invalid Ethereum address"):
        get_reth_balance(w3, contract, "0xnope")


# --- get_market_price ----------------------------------------------------

# sqrtPriceX96 from the live Uniswap V3 0.01% rETH/WETH pool.
# Expected price is computed at the default decimal context precision (28),
# which is what get_market_price uses (it does not customize precision).
_SQRT_PRICE_X96 = 85569339726481144956956941566
_EXPECTED_PRICE = Decimal("1.166479724224971319008351064")
_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
_POOL_ADDRESS = "0x553e9C493678d8606d6a5ba284643dB2110Df823"


def _make_uniswap_factory_pool(*, sqrt_price_x96=_SQRT_PRICE_X96, pool_addr=_POOL_ADDRESS):
    """Build mocked factory + pool contracts for get_market_price."""
    pool = MagicMock()
    pool.functions.slot0.return_value.call.return_value = (
        sqrt_price_x96, 0, 0, 0, 0, 0, False,
    )
    factory = MagicMock()
    factory.functions.getPool.return_value.call.return_value = pool_addr
    return factory, pool


def test_get_market_price_returns_decimal():
    w3 = _make_w3()
    factory, pool = _make_uniswap_factory_pool()
    # w3.eth.contract() must return the factory first, then the pool.
    w3.eth.contract.side_effect = [factory, pool]
    price = get_market_price(w3)
    assert isinstance(price, Decimal)
    assert price == _EXPECTED_PRICE


def test_get_market_price_missing_pool_raises():
    w3 = _make_w3()
    factory, _ = _make_uniswap_factory_pool(pool_addr=_ZERO_ADDRESS)
    w3.eth.contract.side_effect = [factory, MagicMock()]
    with pytest.raises(Web3Exception, match="No Uniswap V3 rETH/WETH pool"):
        get_market_price(w3)


# --- _print_report -------------------------------------------------------

def _run_report(
    capsys,
    eth_paid: Decimal,
    eth_equivalent: Decimal = Decimal("5"),
    exchange_rate: Decimal = Decimal("1.1"),
    market_price: Decimal = Decimal("1.12"),
) -> str:
    _print_report(
        "0xA5bBB646e8fcD3637B6F11CD5E72083E085905E5",
        Decimal("0"),
        Decimal("10"),
        eth_equivalent,
        exchange_rate,
        market_price,
        eth_paid,
    )
    return capsys.readouterr().out


def test_print_report_profit(capsys):
    out = _run_report(capsys, eth_paid=Decimal("2"), eth_equivalent=Decimal("5"))
    assert "Profit: 3.0000 ETH (150.00%)" in out


def test_print_report_loss_shows_magnitude(capsys):
    out = _run_report(capsys, eth_paid=Decimal("6"), eth_equivalent=Decimal("5"))
    assert "Loss: 1.0000 ETH (-16.67%)" in out
    assert "Loss: -1.0000" not in out  # magnitude, not the negative value


def test_print_report_no_profit_block_when_eth_paid_zero(capsys):
    out = _run_report(capsys, eth_paid=Decimal("0"), eth_equivalent=Decimal("5"))
    assert "Profit:" not in out
    assert "Loss:" not in out
    assert "ETH paid:" not in out


def test_print_report_shows_market_premium(capsys):
    # market 1.12 vs RocketPool 1.10 -> premium +0.02 (+1.8182%)
    out = _run_report(
        capsys,
        eth_paid=Decimal("0"),
        exchange_rate=Decimal("1.10"),
        market_price=Decimal("1.12"),
    )
    assert "RocketPool rate:  1.1000000000 ETH/rETH" in out
    assert "Market price:     1.1200000000 ETH/rETH (Uniswap V3)" in out
    assert "Market premium:  +0.0200000000 ETH/rETH (+1.8182%)" in out


def test_print_report_shows_market_discount(capsys):
    # market 1.08 vs RocketPool 1.10 -> discount -0.02 (-1.8182%)
    out = _run_report(
        capsys,
        eth_paid=Decimal("0"),
        exchange_rate=Decimal("1.10"),
        market_price=Decimal("1.08"),
    )
    assert "Market discount: 0.0200000000 ETH/rETH (-1.8182%)" in out


# --- module structure ----------------------------------------------------

def test_import_has_no_side_effects():
    # Importing eth_balance must not create a Web3 instance or load .env.
    # The module should only expose constants and functions; no `w3` attribute.
    assert not hasattr(eth_balance, "w3")
    assert not hasattr(eth_balance, "reth_contract")
    assert callable(eth_balance.main)
    assert callable(eth_balance.get_eth_balance)
    assert callable(eth_balance.get_reth_balance)


def test_abi_uses_statemutability_not_constant():
    for entry in eth_balance.RETH_ABI:
        assert entry["stateMutability"] == "view"
        assert "constant" not in entry