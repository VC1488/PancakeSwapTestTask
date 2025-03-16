import time
from web3 import Web3
from data.abi import abi
from data.token_abi import token_abi
from data.private_key import private_key
from eth_account import Account

# Подключаемся к RPC BSC
bsc_rpc_url = "https://bsc-rpc.publicnode.com"
web3 = Web3(Web3.HTTPProvider(bsc_rpc_url))

# Адрес контракта PancakeSwap Router
pancake_router_address = '0x10ED43C718714eb63d5aA57B78B54704E256024E'
pancake_router_abi = abi  # Замените на реальный ABI для контракта роутера
router_contract = web3.eth.contract(address=pancake_router_address, abi=pancake_router_abi)

# Адрес токена USDT и WBNB
usdt_address = web3.to_checksum_address('0x55d398326f99059ff775485246999027b3197955')
wbnb_address = web3.to_checksum_address('0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c')

# Добавление ликвидности в пул
def add_liquidity(token_address, private_key):
    sender_address = Account.from_key(private_key).address
    token_address = web3.to_checksum_address(token_address)
    # Получаем количество токенов
    token_contract = web3.eth.contract(address=token_address, abi=token_abi)
    balance = token_contract.functions.balanceOf(sender_address).call()
    wbnb_contract = web3.eth.contract(address=wbnb_address, abi=token_abi)

    # Запрашиваем цену обмена для 0.01 USDT на WBNB
    amount_in = web3.to_wei(0.01, 'ether')  # 0.01 USDT
    amounts_out = router_contract.functions.getAmountsOut(amount_in, [usdt_address, wbnb_address]).call()
    amount_out_wbnb = amounts_out[1]  # Сколько WBNB получим за 0.01 USDT

    # Минимальное количество токенов, которые мы готовы получить (с учетом проскальзывания)
    amount_out_min = int(amount_out_wbnb * 0.95)  # Например, допускаем 5% проскальзывания

    # Строим транзакцию для добавления ликвидности
    current_timestamp = int(time.time())
    deadline = current_timestamp + 1800  # Срок действия транзакции — 30 минут

    nonce = web3.eth.get_transaction_count(sender_address)
    gas_price = web3.eth.gas_price

    # Даем разрешение на передачу USDT контракту PancakeSwap Router
    approve_usdt_txn = token_contract.functions.approve(
        pancake_router_address,
        10**20  # Разрешаем потратить 0.01 USDT
    ).build_transaction({
        'chainId': 56,
        'gas': 100_000,
        'gasPrice': gas_price,
        'nonce': nonce,
    })

    # Даем разрешение на передачу WBNB контракту PancakeSwap Router
    approve_wbnb_txn = wbnb_contract.functions.approve(
        pancake_router_address,
        10**20  # Разрешаем потратить WBNB
    ).build_transaction({
        'chainId': 56,
        'gas': 100_000,
        'gasPrice': gas_price,
        'nonce': nonce + 1,  # Увеличиваем nonce для второй транзакции
    })

    # Подписываем транзакцию для USDT
    signed_approve_usdt_txn = web3.eth.account.sign_transaction(approve_usdt_txn, private_key)
    approve_usdt_txn_hash = web3.eth.send_raw_transaction(signed_approve_usdt_txn.raw_transaction)
    print(f"Транзакция для approve USDT отправлена. Хэш: {web3.to_hex(approve_usdt_txn_hash)}")

    # Ожидаем подтверждения транзакции для USDT
    approve_usdt_receipt = web3.eth.wait_for_transaction_receipt(approve_usdt_txn_hash)
    print(f"Транзакция для approve USDT подтверждена. Receipt: {approve_usdt_receipt}")

    # Подписываем транзакцию для WBNB
    signed_approve_wbnb_txn = web3.eth.account.sign_transaction(approve_wbnb_txn, private_key)
    approve_wbnb_txn_hash = web3.eth.send_raw_transaction(signed_approve_wbnb_txn.raw_transaction)
    print(f"Транзакция для approve WBNB отправлена. Хэш: {web3.to_hex(approve_wbnb_txn_hash)}")

    # Ожидаем подтверждения транзакции для WBNB
    approve_wbnb_receipt = web3.eth.wait_for_transaction_receipt(approve_wbnb_txn_hash)
    print(f"Транзакция для approve WBNB подтверждена. Receipt: {approve_wbnb_receipt}")

    # Добавляем ликвидность в пул
    add_liquidity_txn = router_contract.functions.addLiquidity(
        usdt_address,  # Адрес токена A (USDT)
        wbnb_address,  # Адрес токена B (WBNB)
        amount_in,  # Количество токенов A (USDT)
        amount_out_wbnb,  # Количество BNB (WBNB)
        amount_out_min,  # Минимальное количество токенов A (с учетом проскальзывания)
        amount_out_min,  # Минимальное количество токенов B (с учетом проскальзывания)
        sender_address,  # Адрес получателя LP токенов
        deadline  # Срок действия транзакции
    ).build_transaction({
        'chainId': 56,
        'gas': 200_000,  # Количество газа для транзакции
        'gasPrice': gas_price,
        'nonce': nonce + 2,  # Увеличиваем nonce для транзакции добавления ликвидности
        'value': 0  # Сумма BNB для добавления в ликвидность
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
    add_liquidity(usdt_address, private_key)

if __name__ == "__main__":
    main()
