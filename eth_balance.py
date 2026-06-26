import sys
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from typing import Optional

from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError, Web3Exception
from dotenv import load_dotenv

# rETH contract address
RETH_CONTRACT_ADDRESS = "0xae78736Cd615f374D3085123A210448E74Fc6393"

# ABI for the rETH contract (balanceOf is ERC20; getEthValue/getExchangeRate
# are Rocket Pool-specific).
RETH_ABI = [
    {
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "_rethAmount", "type": "uint256"}],
        "name": "getEthValue",
        "outputs": [{"name": "ethAmount", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getExchangeRate",
        "outputs": [{"name": "exchangeRate", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def get_eth_balance(w3: Web3, address: str) -> Decimal:
    """
    Get the ETH balance of a given Ethereum address.

    :param w3: a Web3 instance connected to an Ethereum node
    :param address: Ethereum address as a string
    :return: Balance in ETH as a Decimal
    :raises ValueError: if the address is not a valid Ethereum address
    :raises Web3Exception: if the balance lookup fails
    """
    # Check if the address is valid
    if not w3.is_address(address):
        raise ValueError("Invalid Ethereum address")

    # Get the balance in Wei
    balance_wei = w3.eth.get_balance(address)

    # Convert Wei to ETH
    balance_eth = w3.from_wei(balance_wei, "ether")

    return balance_eth


def get_reth_balance(w3: Web3, reth_contract: Contract, address: str) -> tuple[Decimal, Decimal, Decimal]:
    """
    Get the rETH balance of a given Ethereum address, its ETH equivalent, and
    the current exchange rate.

    :param w3: a Web3 instance connected to an Ethereum node
    :param reth_contract: a Contract instance for the rETH token
    :param address: Ethereum address as a string
    :return: Tuple of (rETH balance, ETH equivalent, exchange rate) as Decimals
    :raises ValueError: if the address is not a valid Ethereum address
    :raises ContractLogicError: if a contract call reverts
    :raises Web3Exception: if a contract call fails
    """
    # Check if the address is valid
    if not w3.is_address(address):
        raise ValueError("Invalid Ethereum address")

    # Get the balance in Wei
    balance_wei = reth_contract.functions.balanceOf(address).call()

    # Convert Wei to ETH (rETH uses the same decimals as ETH)
    balance_reth = w3.from_wei(balance_wei, "ether")

    # Get the ETH equivalent
    eth_equivalent_wei = reth_contract.functions.getEthValue(balance_wei).call()
    eth_equivalent = w3.from_wei(eth_equivalent_wei, "ether")

    exchange_rate = reth_contract.functions.getExchangeRate().call()
    exchange_rate = w3.from_wei(exchange_rate, "ether")
    return balance_reth, eth_equivalent, exchange_rate


def _print_report(
    address: str,
    eth_balance: Decimal,
    reth_balance: Decimal,
    eth_equivalent: Decimal,
    exchange_rate: Decimal,
    eth_paid: Decimal,
) -> None:
    print(f"The ETH balance of {address} is {eth_balance:.4f} ETH")
    print(f"The rETH balance of {address} is {reth_balance:.4f} rETH")
    print(f"Exchange rate: {exchange_rate}")
    print(f"The ETH equivalent of the rETH balance is {eth_equivalent:.4f} ETH")

    if eth_paid > 0:
        profit_loss = eth_equivalent - eth_paid
        profit_loss_percentage = (profit_loss / eth_paid) * 100
        print(f"ETH paid: {eth_paid:.4f} ETH")
        if profit_loss >= 0:
            print(f"Profit: {profit_loss:.4f} ETH ({profit_loss_percentage:.2f}%)")
        else:
            print(f"Loss: {abs(profit_loss):.4f} ETH ({profit_loss_percentage:.2f}%)")


def main(argv: Optional[Sequence[str]] = None) -> None:
    """
    Entry point for the ETH/rETH balance checker.

    :param argv: optional argument list (defaults to sys.argv[1:])
    """
    import os

    load_dotenv()

    infura_url = os.getenv("INFURA_URL")
    if not infura_url:
        sys.exit("INFURA_URL is not set. Add it to your .env file.")
    w3 = Web3(Web3.HTTPProvider(infura_url))

    default_address = os.getenv("DEFAULT_ADDRESS")
    try:
        default_eth_paid = Decimal(os.getenv("DEFAULT_ETH_PAID", "0"))
    except InvalidOperation:
        sys.exit("DEFAULT_ETH_PAID in .env is not a valid number.")

    reth_contract = w3.eth.contract(address=RETH_CONTRACT_ADDRESS, abi=RETH_ABI)

    args = sys.argv[1:] if argv is None else argv
    use_env = "-e" in args

    if use_env:
        address = default_address
        if not address:
            sys.exit("DEFAULT_ADDRESS is not set. Add it to your .env file.")
        eth_paid = default_eth_paid
    else:
        # Example usage
        address = (
            input(
                "Enter an Ethereum address (press Enter to use the default from .env): "
            ).strip()
            or default_address
        )
        if not address:
            print(
                "No address provided. Please set DEFAULT_ADDRESS in .env or enter an address."
            )
            sys.exit(1)
        eth_paid_input = input(
            "Enter the amount of ETH paid (press Enter to use the default from .env): "
        ).strip()
        try:
            eth_paid = Decimal(eth_paid_input) if eth_paid_input else default_eth_paid
        except InvalidOperation:
            print("Invalid ETH paid amount. Please enter a valid number.")
            sys.exit(1)

    try:
        eth_balance = get_eth_balance(w3, address)
        reth_balance, eth_equivalent, exchange_rate = get_reth_balance(w3, reth_contract, address)
        _print_report(address, eth_balance, reth_balance, eth_equivalent, exchange_rate, eth_paid)

    except ValueError as e:
        print(f"Error: {e}")
    except ContractLogicError as e:
        print(f"Contract call failed: {e}")
    except Web3Exception as e:
        print(f"Web3 error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


def cli() -> None:
    """Console-script entry point: runs the balance checker in env mode (-e)."""
    main(["-e"])


if __name__ == "__main__":
    main()