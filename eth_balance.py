import os
import sys
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Web3 with an Ethereum node provider (e.g., Infura)
infura_url = os.getenv("INFURA_URL")
w3 = Web3(Web3.HTTPProvider(infura_url))

# Get the default address and ETH paid from .env file
DEFAULT_ADDRESS = os.getenv("DEFAULT_ADDRESS")
DEFAULT_ETH_PAID = float(os.getenv("DEFAULT_ETH_PAID", "0"))

# rETH contract address
RETH_CONTRACT_ADDRESS = "0xae78736Cd615f374D3085123A210448E74Fc6393"

# ERC20 ABI (including balanceOf and getEthValue functions)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_rethAmount", "type": "uint256"}],
        "name": "getEthValue",
        "outputs": [{"name": "ethAmount", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "getExchangeRate",
        "outputs": [{"name": "exchangeRate", "type": "uint256"}],
        "type": "function",
    },
]

# Initialize rETH contract
reth_contract = w3.eth.contract(address=RETH_CONTRACT_ADDRESS, abi=ERC20_ABI)


def get_eth_balance(address):
    """
    Get the ETH balance of a given Ethereum address.

    :param address: Ethereum address as a string
    :return: Balance in ETH as a float
    """
    # Check if the address is valid
    if not w3.is_address(address):
        raise ValueError("Invalid Ethereum address")

    # Get the balance in Wei
    balance_wei = w3.eth.get_balance(address)

    # Convert Wei to ETH
    balance_eth = w3.from_wei(balance_wei, "ether")

    return float(balance_eth)


def get_reth_balance(address):
    """
    Get the rETH balance of a given Ethereum address and its ETH equivalent.

    :param address: Ethereum address as a string
    :return: Tuple of (rETH balance, ETH equivalent) as floats
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
    return float(balance_reth), float(eth_equivalent), float(exchange_rate)


if __name__ == "__main__":
    # Check if -e flag is used
    use_env = "-e" in sys.argv

    if use_env:
        address = DEFAULT_ADDRESS
        eth_paid = DEFAULT_ETH_PAID
    else:
        # Example usage
        address = (
            input(
                "Enter an Ethereum address (press Enter to use the default from .env): "
            ).strip()
            or DEFAULT_ADDRESS
        )
        if not address:
            print(
                "No address provided. Please set DEFAULT_ADDRESS in .env or enter an address."
            )
            sys.exit(1)
        eth_paid_input = input(
            "Enter the amount of ETH paid (press Enter to use the default from .env): "
        ).strip()
        eth_paid = float(eth_paid_input) if eth_paid_input else DEFAULT_ETH_PAID

    try:
        eth_balance = get_eth_balance(address)
        reth_balance, eth_equivalent, exchange_rate = get_reth_balance(address)
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
                print(f"Loss: {profit_loss:.4f} ETH ({profit_loss_percentage:.2f}%)")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
