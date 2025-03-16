import time
from web3 import Web3
from data.abi import abi
from data.token_abi import token_abi
from data.private_key import private_key
from eth_account import Account

bsc_rpc_url = "https://bsc-rpc.publicnode.com"
web3 = Web3(Web3.HTTPProvider(bsc_rpc_url))

# Адрес контракта PancakeSwap Router
pancake_router_address = '0x10ED43C718714eb63d5aA57B78B54704E256024E'
pancake_router_abi = abi
router_contract = web3.eth.contract(address=pancake_router_address, abi=pancake_router_abi)

# Адрес токена USDT и WBNB
usdt_address = web3.to_checksum_address('0x55d398326f99059ff775485246999027b3197955')
wbnb_address = web3.to_checksum_address('0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c')

def swap_eth_for_tokens(amount, token_address, private_key):
    sender_address = Account.from_key(private_key).address
    token_address = web3.to_checksum_address(token_address)
    pancake_router_address = '0x10ED43C718714eb63d5aA57B78B54704E256024E'
    pancake_router_abi = abi
    router_contract = web3.eth.contract(address=pancake_router_address, abi=pancake_router_abi)

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

    # Получаем количество купленных токенов
    token_contract = web3.eth.contract(address=token_address, abi=token_abi)
    purchased_tokens = token_contract.functions.balanceOf(sender_address).call()
    print(f"Количество купленных токенов: {purchased_tokens}")

    # Добавляем ликвидность с этими токенами и BNB
    add_liquidity(token_address, purchased_tokens, amount, private_key)


def add_liquidity(token_address, purchased_tokens, eth_amount, private_key):
    sender_address = Account.from_key(private_key).address
    token_address = web3.to_checksum_address(token_address)
    token_contract = web3.eth.contract(address=token_address, abi=token_abi)

    # Получаем количество токенов для добавления в ликвидность
    amount_in = purchased_tokens  # Купленные токены
    amount_in_wei = web3.to_wei(eth_amount, 'ether')  # Количество BNB (ETH)

    # Запрашиваем цену обмена для количества BNB на токены
    amounts_out = router_contract.functions.getAmountsOut(amount_in_wei, [wbnb_address, token_address]).call()
    amount_out_token = amounts_out[1]  # Сколько токенов получим за BNB

    amount_out_min = int(amount_out_token * 0.95)  # 5% слиппедж

    # Строим транзакцию для добавления ликвидности
    current_timestamp = int(time.time())
    deadline = current_timestamp + 1800

    nonce = web3.eth.get_transaction_count(sender_address)
    gas_price = web3.eth.gas_price

    # Даем разрешение на передачу токенов контракту PancakeSwap Router
    approve_txn = token_contract.functions.approve(
        pancake_router_address,
        amount_in
    ).build_transaction({
        'chainId': 56,
        'gas': 100_000,
        'gasPrice': gas_price,
        'nonce': nonce,
    })

    # Подписываем транзакцию для разрешения
    signed_approve_txn = web3.eth.account.sign_transaction(approve_txn, private_key)
    approve_txn_hash = web3.eth.send_raw_transaction(signed_approve_txn.raw_transaction)
    print(f"Транзакция для approve отправлена. Хэш: {web3.to_hex(approve_txn_hash)}")

    # Ожидаем подтверждения транзакции для approve
    approve_receipt = web3.eth.wait_for_transaction_receipt(approve_txn_hash)
    print(f"Транзакция для approve подтверждена. Receipt: {approve_receipt}")

    # Добавляем ликвидность в пул
    add_liquidity_txn = router_contract.functions.addLiquidity(
        token_address,  # Адрес токена
        wbnb_address,   # Адрес WBNB
        amount_in,      # Количество токенов
        amount_in_wei,  # Количество BNB (ETH)
        amount_out_min, # Минимальное количество токенов
        amount_out_min, # Минимальное количество WBNB
        sender_address, # Адрес получателя LP токенов
        deadline        # Срок действия транзакции
    ).build_transaction({
        'chainId': 56,
        'gas': 200_000,  # Количество газа для транзакции
        'gasPrice': gas_price,
        'nonce': nonce + 1,  # Увеличиваем nonce для транзакции добавления ликвидности
        'value': 0  # Количество BNB для добавления в ликвидность
    })

    # Подписываем транзакцию для добавления ликвидности
    signed_add_liquidity_txn = web3.eth.account.sign_transaction(add_liquidity_txn, private_key)

    # Отправка транзакции для добавления ликвидности
    add_liquidity_txn_hash = web3.eth.send_raw_transaction(signed_add_liquidity_txn.raw_transaction)
    print(f"Транзакция для добавления ликвидности отправлена. Хэш: {web3.to_hex(add_liquidity_txn_hash)}")

    # Ожидание подтверждения транзакции добавления ликвидности
    add_liquidity_receipt = web3.eth.wait_for_transaction_receipt(add_liquidity_txn_hash)
    print(f"Транзакция для добавления ликвидности подтверждена. Receipt: {add_liquidity_receipt}")


def main():
    amount = 0.0003
    token_address = '0x55d398326f99059ff775485246999027b3197955'

    swap_eth_for_tokens(amount, token_address, private_key)


if __name__ == "__main__":
    main()
