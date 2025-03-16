import time
from web3 import Web3
from data.abi import abi
from data.private_key import private_key
from eth_account import Account

bsc_rpc_url = "https://bsc-rpc.publicnode.com"
web3 = Web3(Web3.HTTPProvider(bsc_rpc_url))

# Функция для обмена ETH на токены
def swap_eth_for_tokens(amount, token_address, private_key):

    pancake_router_address = '0x10ED43C718714eb63d5aA57B78B54704E256024E'
    pancake_router_abi = abi
    router_contract = web3.eth.contract(address=pancake_router_address, abi=pancake_router_abi)

    token_address = web3.to_checksum_address(token_address)
    sender_address = Account.from_key(private_key).address

    amount_in_wei = web3.to_wei(amount, 'ether')
    amount_out_min = 0

    path = [
        web3.to_checksum_address('0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'),  # WBNB адрес
        token_address  # Адрес целевого токена
    ]

    current_timestamp = int(time.time())
    deadline = current_timestamp + 1800

    nonce = web3.eth.get_transaction_count(sender_address)
    gas_price = web3.eth.gas_price

    transaction = router_contract.functions.swapExactETHForTokens(
        amount_out_min,
        path,
        sender_address,
        deadline
    ).build_transaction({
        'chainId': 56,
        'gas': 200_000,
        'gasPrice': gas_price,
        'nonce': nonce,
        'value': amount_in_wei,
    })

    signed_txn = web3.eth.account.sign_transaction(transaction, private_key)
    txn_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

    print(f"Tx sent. Hash: {web3.to_hex(txn_hash)}")

    receipt = web3.eth.wait_for_transaction_receipt(txn_hash)
    print(f"Tx approved. Receipt: {receipt}")


def main():
    amount = 0.0005
    token_address = '0x55d398326f99059ff775485246999027b3197955'

    swap_eth_for_tokens(amount, token_address, private_key)


if __name__ == "__main__":
    main()