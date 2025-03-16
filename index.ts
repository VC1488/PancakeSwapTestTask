import { ethers } from 'ethers';
import * as fs from 'fs';
import * as path from 'path';

const bscRpcUrl = "https://bsc-rpc.publicnode.com";
const provider = new ethers.providers.JsonRpcProvider(bscRpcUrl);

// Вставьте приватный ключ
const privateKey = '';
const wallet = new ethers.Wallet(privateKey, provider);

// Адрес контракта PancakeSwap Router
const pancakeRouterAddress = '0x10ED43C718714eb63d5aA57B78B54704E256024E';
const pancakeRouterAbi = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'pancakeRouterAbi.json'), 'utf8'));
const tokenAbi = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'tokenAbi.json'), 'utf8'));

// Адрес токенов USDT и WBNB
const usdtAddress = '0x55d398326f99059ff775485246999027b3197955'; // USDT
const wbnbAddress = '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'; // WBNB

// Функция для обмена ETH на токены
async function swapEthForTokens(amount: number, tokenAddress: string) {
    const routerContract = new ethers.Contract(pancakeRouterAddress, pancakeRouterAbi, wallet);
    const tokenContract = new ethers.Contract(tokenAddress, tokenAbi, provider);

    // Получаем количество ETH для обмена в wei
    const amountInWei = ethers.utils.parseUnits(amount.toString(), 'ether');
    const path = [wbnbAddress, tokenAddress];

    // Устанавливаем минимальное количество токенов (для предотвращения проскальзывания)
    const amountOutMin = 0;

    // Определяем дедлайн транзакции (30 минут)
    const deadline = Math.floor(Date.now() / 1000) + 1800;

    const nonce = await provider.getTransactionCount(wallet.address);
    const gasPrice = await provider.getGasPrice();

    const transaction = await routerContract.populateTransaction.swapExactETHForTokens(
        amountOutMin,
        path,
        wallet.address,
        deadline,
        {
            value: amountInWei,
            nonce: nonce,
            gasLimit: 200000,
            gasPrice: gasPrice,
        }
    );

    const tx = await wallet.sendTransaction(transaction);
    console.log(`Tx sent. Hash: ${tx.hash}`);

    const receipt = await tx.wait();
    console.log(`Tx approved. Receipt: ${receipt}`);

    // Получаем количество купленных токенов
    const purchasedTokens = await tokenContract.balanceOf(wallet.address);
    console.log(`Количество купленных токенов: ${ethers.utils.formatUnits(purchasedTokens, 18)}`);

    // Добавляем ликвидность с этими токенами и BNB
    await addLiquidity(tokenAddress, purchasedTokens, amount, wallet);
}

// Функция для добавления ликвидности
async function addLiquidity(tokenAddress: string, purchasedTokens: ethers.BigNumber, ethAmount: number, wallet: ethers.Wallet) {
    const routerContract = new ethers.Contract(pancakeRouterAddress, pancakeRouterAbi, wallet);
    const tokenContract = new ethers.Contract(tokenAddress, tokenAbi, wallet);

    const wbnbContract = new ethers.Contract(wbnbAddress, tokenAbi, wallet);

    // Получаем количество токенов и ETH для добавления в ликвидность
    const amountIn = purchasedTokens;
    const amountInWei = ethers.utils.parseUnits(ethAmount.toString(), 'ether');

    // Получаем количество токенов, которое получим за BNB
    const amountsOut = await routerContract.getAmountsOut(amountInWei, [wbnbAddress, tokenAddress]);
    const amountOutToken = amountsOut[1];

    const amountOutMin = amountOutToken.mul(95).div(100); // 5% slippage

    // Строим транзакцию для добавления ликвидности
    const deadline = Math.floor(Date.now() / 1000) + 1800;
    const nonce = await provider.getTransactionCount(wallet.address);
    const gasPrice = await provider.getGasPrice();

    // Даем разрешение на передачу USDT контракту PancakeSwap Router
    const approveUsdtTx = await tokenContract.populateTransaction.approve(
        pancakeRouterAddress,
        ethers.BigNumber.from("10000000000000000000000000000") // 10^20
    );

    const approveUsdtTxResponse = await wallet.sendTransaction({
        to: approveUsdtTx.to,
        data: approveUsdtTx.data,
        nonce: nonce,
        gasLimit: 100000,
        gasPrice: gasPrice,
    });

    console.log(`Транзакция для approve USDT отправлена. Хэш: ${approveUsdtTxResponse.hash}`);

    const approveUsdtTxReceipt = await approveUsdtTxResponse.wait();
    console.log(`Транзакция для approve USDT подтверждена. Receipt: ${approveUsdtTxReceipt}`);

    // Даем разрешение на передачу WBNB контракту PancakeSwap Router
    const approveWbnbTx = await wbnbContract.populateTransaction.approve(
        pancakeRouterAddress,
        ethers.BigNumber.from("10000000000000000000000000000") // 10^20
    );

    const approveWbnbTxResponse = await wallet.sendTransaction({
        to: approveWbnbTx.to,
        data: approveWbnbTx.data,
        nonce: nonce + 1, // Увеличиваем nonce для второй транзакции
        gasLimit: 100000,
        gasPrice: gasPrice,
    });

    console.log(`Транзакция для approve WBNB отправлена. Хэш: ${approveWbnbTxResponse.hash}`);

    const approveWbnbTxReceipt = await approveWbnbTxResponse.wait();
    console.log(`Транзакция для approve WBNB подтверждена. Receipt: ${approveWbnbTxReceipt}`);

    // Добавляем ликвидность в пул
    const addLiquidityTx = await routerContract.populateTransaction.addLiquidity(
        tokenAddress,  // Адрес токена
        wbnbAddress,   // Адрес WBNB
        amountIn,      // Количество токенов
        amountInWei,   // Количество BNB (ETH)
        amountOutMin,  // Минимальное количество токенов
        amountOutMin,  // Минимальное количество WBNB
        wallet.address, // Адрес получателя LP токенов
        deadline       // Срок действия транзакции
    );

    const addLiquidityTxResponse = await wallet.sendTransaction({
        to: addLiquidityTx.to,
        data: addLiquidityTx.data,
        nonce: nonce + 2, // Увеличиваем nonce для транзакции добавления ликвидности
        gasLimit: 200000,
        gasPrice: gasPrice,
        value: 0, // В этой транзакции value = 0, так как мы не добавляем BNB для ликвидности
    });

    console.log(`Транзакция для добавления ликвидности отправлена. Хэш: ${addLiquidityTxResponse.hash}`);

    const addLiquidityTxReceipt = await addLiquidityTxResponse.wait();
    console.log(`Транзакция для добавления ликвидности подтверждена. Receipt: ${addLiquidityTxReceipt}`);
}

// Основная функция
async function main() {
    const amount = 0.0001; // Количество ETH для обмена
    const tokenAddress = '0x55d398326f99059ff775485246999027b3197955'; // Адрес токена

    await swapEthForTokens(amount, tokenAddress);
}

main().catch((error) => {
    console.error(error);
});
