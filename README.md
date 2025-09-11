# Ethereum Balance Checker

This Python script allows you to check the ETH and rETH balances of an Ethereum address, as well as calculate profit/loss based on the amount of ETH paid.

## Features

- Check ETH balance of an Ethereum address
- Check rETH balance and its ETH equivalent
- Calculate profit/loss based on ETH paid
- Use default values from a .env file or input values at runtime
- Option to use only .env values with a command-line flag

## Prerequisites

- Python 3.6+
- pip (Python package installer)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/ethereum-balance-checker.git
   cd ethereum-balance-checker
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and add your Infura URL and default values:
   ```
   INFURA_URL=https://mainnet.infura.io/v3/your-project-id
   DEFAULT_ADDRESS=0x1234567890123456789012345678901234567890
   DEFAULT_ETH_PAID=1.5
   ```

## Usage

Run the script with:

```
python eth_balance.py
```

You will be prompted to enter an Ethereum address and the amount of ETH paid. Press Enter without input to use the default values from the .env file.

To use only the values from the .env file without prompts, use the `-e` flag:

```
python eth_balance.py -e
```

## Output

The script will display:
- ETH balance
- rETH balance
- ETH equivalent of the rETH balance
- Profit/Loss calculation (if ETH paid amount is provided)

## Contributing

Contributions, issues, and feature requests are welcome. Feel free to check issues page if you want to contribute.

## License

[MIT](https://choosealicense.com/licenses/mit/)
