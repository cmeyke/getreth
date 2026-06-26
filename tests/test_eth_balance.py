import io
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from web3 import Web3

import eth_balance
from eth_balance import get_eth_balance, get_reth_balance, _print_report


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


# --- _print_report -------------------------------------------------------

def _run_report(capsys, eth_paid: Decimal, eth_equivalent: Decimal = Decimal("5")) -> str:
    _print_report(
        "0xA5bBB646e8fcD3637B6F11CD5E72083E085905E5",
        Decimal("0"),
        Decimal("10"),
        eth_equivalent,
        Decimal("1.1"),
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