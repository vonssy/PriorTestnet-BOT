from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout
)
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from eth_account import Account
from web3 import Web3
from colorama import *
from datetime import datetime, timezone, timedelta
import asyncio, json, os, pytz

wib = pytz.timezone('Asia/Jakarta')

class PriorTestnet:
    def __init__(self) -> None:
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://priortestnet.xyz",
            "Referer": "https://priortestnet.xyz/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": FakeUserAgent().random
        }
        self.BASE_API = "https://priortestnet.xyz/api"
        self.RPC_URL = "https://base-sepolia-rpc.publicnode.com/89e4ff0f587fe2a94c7a2c12653f4c55d2bda1186cb6c1c95bd8d8408fbdc014"
        self.FAUCET_CONTRACT_ADDRESS = "0xa206dC56F1A56a03aEa0fCBB7c7A62b5bE1Fe419"
        self.PRIOR_CONTRACT_ADDRESS = "0xeFC91C5a51E8533282486FA2601dFfe0a0b16EDb"
        self.USDC_CONTRACT_ADDRESS = "0xdB07b0b4E88D9D5A79A08E91fEE20Bb41f9989a2"
        self.SWAP_ROUTER_ADDRESS = "0x8957e1988905311EE249e679a29fc9deCEd4D910"
        self.ERC20_CONTRACT_ABI = [
            {
                "name": "approve",
                "type": "function",
                "inputs": [
                    {"name": "spender", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "outputs": [{"type": "bool"}],
                "stateMutability": "nonpayable"
            },
            {
                "name": "allowance",
                "type": "function",
                "inputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "spender", "type": "address"}
                ],
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view"
            },
            {
                "name": "balanceOf",
                "type": "function",
                "inputs": [{"name": "account", "type": "address"}],
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view"
            },
            {
                "name": "decimals",
                "type": "function",
                "inputs": [],
                "outputs": [{"type": "uint8"}],
                "stateMutability": "view"
            }
        ]
        self.FAUCET_CONTRACT_ABI = [
            {
                "inputs": [],
                "name": "claim",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        self.PRIOR_HEX_DATA = "0x8ec7baf1000000000000000000000000000000000000000000000000016345785d8a0000"
        self.USDC_HEX_DATA = "0xea0e435800000000000000000000000000000000000000000000000000000000000f4240"
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(
            f"""
        {Fore.GREEN + Style.BRIGHT}Auto Claim Faucet & Swap {Fore.BLUE + Style.BRIGHT}Prior Testnet - BOT
            """
            f"""
        {Fore.GREEN + Style.BRIGHT}Rey? {Fore.YELLOW + Style.BRIGHT}<INI WATERMARK>
            """
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    async def load_proxies(self, use_proxy_choice: int):
        filename = "proxy.txt"
        try:
            if use_proxy_choice == 1:
                async with ClientSession(timeout=ClientTimeout(total=30)) as session:
                    async with session.get("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt") as response:
                        response.raise_for_status()
                        content = await response.text()
                        with open(filename, 'w') as f:
                            f.write(content)
                        self.proxies = content.splitlines()
            else:
                if not os.path.exists(filename):
                    self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                    return
                with open(filename, 'r') as f:
                    self.proxies = f.read().splitlines()
            
            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Proxies Total  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )
        
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def get_next_proxy_for_account(self, token):
        if token not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[token] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[token]

    def rotate_proxy_for_account(self, token):
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[token] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy
    
    def generate_address(self, account: str):
        try:
            account = Account.from_key(account)
            address = account.address
            
            return address
        except Exception as e:
            return None
    
    async def get_token_balance(self, address: str, contract_address: str):
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        try:
            token_contract = web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=self.ERC20_CONTRACT_ABI)
            decimals = token_contract.functions.decimals().call()
            balance = token_contract.functions.balanceOf(address).call()

            return decimals, balance
        except Exception as e:
            return None, None
    
    async def executing_faucet_claim(self, account: str, address: str):
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        contract = web3.eth.contract(address=self.FAUCET_CONTRACT_ADDRESS, abi=self.FAUCET_CONTRACT_ABI)
        try:
            estimated_gas = contract.functions.claim().estimate_gas({'from': address})
            tx = contract.functions.claim().build_transaction({
                'from': address,
                'nonce': web3.eth.get_transaction_count(address),
                'gas': estimated_gas,
                'gasPrice': web3.eth.gas_price
            })

            signed_tx = web3.eth.account.sign_transaction(tx, account)
            raw_tx = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = web3.to_hex(raw_tx)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            block_number = receipt.blockNumber

            return tx_hash, block_number
        except Exception as e:
            return None, None
    
    async def approving_swap_token(self, account: str, address: str, contract_address: str, amount: int):
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        contract = web3.eth.contract(address=contract_address, abi=self.ERC20_CONTRACT_ABI)
        try:
            approve_txn = contract.functions.approve(self.SWAP_ROUTER_ADDRESS, amount).build_transaction({
                'from': address,
                'nonce': web3.eth.get_transaction_count(address),
                'gas': 100000,
                'gasPrice': web3.eth.gas_price,
                'chainId': web3.eth.chain_id
            })

            signed_tx = web3.eth.account.sign_transaction(approve_txn, account)
            raw_tx = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = web3.to_hex(raw_tx)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            block_number = receipt.blockNumber

            return tx_hash, block_number
        except Exception as e:
            return None, None
    
    async def executing_swap_token(self, account: str, address: str, hex_data: str):
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        try:
            swap_tx = {
                'to': self.SWAP_ROUTER_ADDRESS,
                'data': hex_data,
                'from': address,
                'nonce': web3.eth.get_transaction_count(address),
                'gas': 300000,
                'gasPrice': web3.eth.gas_price,
                'chainId': web3.eth.chain_id
            }

            signed_tx = web3.eth.account.sign_transaction(swap_tx, account)
            raw_tx = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = web3.to_hex(raw_tx)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            block_number = receipt.blockNumber

            return tx_hash, block_number
        except Exception as e:
            return None, None
        
    def generate_swap_payload(self, address: str, amount: str, token_from: str, token_to: str, tx_hash: str):
        try:
            payload = {
                "address":address,
                "amount":amount,
                "tokenFrom":token_from,
                "tokenTo":token_to,
                "txHash":tx_hash
            }
            
            return payload
        except Exception as e:
            return None
    
    def mask_account(self, account):
        mask_account = account[:6] + '*' * 6 + account[-6:]
        return mask_account 
    
    def print_question(self):
        while True:
            try:
                print("1. Run With Monosans Proxy")
                print("2. Run With Private Proxy")
                print("3. Run Without Proxy")
                choose = int(input("Choose [1/2/3] -> ").strip())

                if choose in [1, 2, 3]:
                    proxy_type = (
                        "Run With Monosans Proxy" if choose == 1 else 
                        "Run With Private Proxy" if choose == 2 else 
                        "Run Without Proxy"
                    )
                    print(f"{Fore.GREEN + Style.BRIGHT}{proxy_type} Selected.{Style.RESET_ALL}")
                    return choose
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Please enter either 1, 2 or 3.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number (1, 2 or 3).{Style.RESET_ALL}")
    
    async def user_auth(self, address: str, proxy=None, retries=5):
        url = f"{self.BASE_API}/auth"
        data = json.dumps({"address":address})
        headers = {
            **self.headers,
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.post(url=url, headers=headers, data=data) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                return None
    
    async def user_data(self, address: str, proxy=None, retries=5):
        url = f"{self.BASE_API}/users/{address}"
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.get(url=url, headers=self.headers) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                return None
    
    async def claim_faucet(self, address: str, proxy=None, retries=5):
        url = f"{self.BASE_API}/faucet/claim"
        data = json.dumps({"address":address})
        headers = {
            **self.headers,
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.post(url=url, headers=headers, data=data) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                return None
            
    async def perfrom_swap(self, address: str, amount: str, token_from: str, token_to: str, tx_hash: str, proxy=None, retries=5):
        url = f"{self.BASE_API}/swap"
        data = json.dumps(self.generate_swap_payload(address, amount, token_from, token_to, tx_hash))
        headers = {
            **self.headers,
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.post(url=url, headers=headers, data=data) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                return None
            
    async def process_user_auth(self, address: str, use_proxy: bool):
        proxy = self.get_next_proxy_for_account(address) if use_proxy else None
        user = None
        while user is None:
            user = await self.user_auth(address, proxy)
            if not user:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status    :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} GET User Data Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} Retrying... {Style.RESET_ALL}"
                )

                proxy = self.rotate_proxy_for_account(address) if use_proxy else None
                await asyncio.sleep(3)
                continue

            return True
            
    async def process_get_user_data(self, address: str, use_proxy: bool):
        is_authenticate = await self.process_user_auth(address, use_proxy)
        if is_authenticate:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None

            user = None
            while user is None:
                user = await self.user_data(address, proxy)
                if not user:
                    self.log(
                        f"{Fore.CYAN+Style.BRIGHT}Status    :{Style.RESET_ALL}"
                        f"{Fore.RED+Style.BRIGHT} GET User Data Failed {Style.RESET_ALL}"
                        f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                        f"{Fore.YELLOW+Style.BRIGHT} Retrying... {Style.RESET_ALL}"
                    )

                    proxy = self.rotate_proxy_for_account(address) if use_proxy else None
                    await asyncio.sleep(3)
                    continue

                return user
        
    async def process_swap_prior_to_usdc(self, account: str, address: str, proxy=None):
        decimals, balance = await self.get_token_balance(address, self.PRIOR_CONTRACT_ADDRESS)
        if decimals and balance:
            amount = int(0.1 * (10 ** decimals))
            
            if balance < amount:
                return self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                    f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} Insufficient PRIOR balance {Style.RESET_ALL}"
                )
            
            approve_tx_hash, approve_block_number = await self.approving_swap_token(account, address, self.PRIOR_CONTRACT_ADDRESS, amount)
            if approve_tx_hash and approve_block_number:
                swap_tx_hash, swap_block_number = await self.executing_swap_token(account, address, self.PRIOR_HEX_DATA)
                if swap_tx_hash and swap_block_number:
                    swap = await self.perfrom_swap(address, "0.1", "PRIOR", "USDC", swap_tx_hash, proxy)
                    if swap and swap.get("success"):
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                            f"{Fore.GREEN+Style.BRIGHT} Perform Swap Success {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Approve Block Number:{Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT} {approve_block_number} {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Approve Tx Hash     :{Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT} {approve_tx_hash} {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Swap Block Number   :{Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT} {swap_block_number} {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Swap Tx Hash        :{Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT} {swap_tx_hash} {Style.RESET_ALL}"
                        )
                    else:
                        return self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                            f"{Fore.RED+Style.BRIGHT} Perform Swap Failed {Style.RESET_ALL}"
                        )
                else:
                    return self.log(
                        f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                        f"{Fore.RED+Style.BRIGHT} Perform On-chain Failed {Style.RESET_ALL}"
                    )
            else:
                return self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                    f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Approving TX Failed {Style.RESET_ALL}"
                )

        else:
            return self.log(
                f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} Insufficient PRIOR balance {Style.RESET_ALL}"
            )
        
    async def process_swap_usdc_to_prior(self, account: str, address: str, proxy=None):
        decimals, balance = await self.get_token_balance(address, self.USDC_CONTRACT_ADDRESS)
        if decimals and balance:
            amount = int(1 * (10 ** decimals))
            
            if balance < amount:
                return self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                    f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} Insufficient USDC balance {Style.RESET_ALL}"
                )
            
            approve_tx_hash, approve_block_number = await self.approving_swap_token(account, address, self.USDC_CONTRACT_ADDRESS, amount)
            if approve_tx_hash and approve_block_number:
                swap_tx_hash, swap_block_number = await self.executing_swap_token(account, address, self.USDC_HEX_DATA)
                if swap_tx_hash and swap_block_number:
                    swap = await self.perfrom_swap(address, "1", "USDC", "PRIOR", swap_tx_hash, proxy)
                    if swap and swap.get("success"):
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                            f"{Fore.GREEN+Style.BRIGHT} Perform Swap Success {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Approve Block Number:{Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT} {approve_block_number} {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Approve Tx Hash     :{Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT} {approve_tx_hash} {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Swap Block Number   :{Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT} {swap_block_number} {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Swap Tx Hash        :{Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT} {swap_tx_hash} {Style.RESET_ALL}"
                        )
                    else:
                        return self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                            f"{Fore.RED+Style.BRIGHT} Perform Swap Failed {Style.RESET_ALL}"
                        )
                else:
                    return self.log(
                        f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                        f"{Fore.RED+Style.BRIGHT} Perform On-chain Failed {Style.RESET_ALL}"
                    )

            else:
                return self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                    f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Approving TX Failed {Style.RESET_ALL}"
                )

        else:
            return self.log(
                f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                f"{Fore.CYAN+Style.BRIGHT}Status              :{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} Insufficient USDC balance {Style.RESET_ALL}"
            )

    async def process_accounts(self, account: str, address: str, use_proxy: bool):
        user = await self.process_get_user_data(address, use_proxy)
        if user:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Proxy     :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {proxy} {Style.RESET_ALL}"
            )

            balance = user.get("totalPoints", 0)
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Balance   :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {balance} PTS {Style.RESET_ALL}"
            )

            last_faucet_claim = user.get("lastFaucetClaim", None)
            if last_faucet_claim is None:
                tx_hash, block_number = await self.executing_faucet_claim(account, address)
                if tx_hash and block_number:
                    claim = await self.claim_faucet(address, proxy)
                    if claim and claim.get("success"):
                        self.log(
                            f"{Fore.CYAN+Style.BRIGHT}Faucet    :{Style.RESET_ALL}"
                            f"{Fore.GREEN+Style.BRIGHT} Claimed Successfully {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Block  :{Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT} {block_number} {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Tx Hash:{Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT} {tx_hash} {Style.RESET_ALL}"
                        )
                    else:
                        self.log(
                            f"{Fore.CYAN+Style.BRIGHT}Faucet    :{Style.RESET_ALL}"
                            f"{Fore.RED+Style.BRIGHT} Claim Failed {Style.RESET_ALL}"
                        )
                else:
                    self.log(
                        f"{Fore.CYAN+Style.BRIGHT}Faucet    :{Style.RESET_ALL}"
                        f"{Fore.RED+Style.BRIGHT} Perform On-chain Failed {Style.RESET_ALL}"
                        f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                        f"{Fore.YELLOW+Style.BRIGHT} Check Your Base Sepolia for Gas Fee {Style.RESET_ALL}"
                    )
            else:
                utc_now = datetime.now(timezone.utc)
                next_faucet_claim_utc = datetime.fromisoformat(last_faucet_claim.replace("Z", "+00:00")) + timedelta(days=1)

                if utc_now >= next_faucet_claim_utc:
                    tx_hash, block_number = await self.executing_faucet_claim(account, address)
                    if tx_hash and block_number:
                        claim = await self.claim_faucet(address, proxy)
                        if claim and claim.get("success"):
                            self.log(
                                f"{Fore.CYAN+Style.BRIGHT}Faucet    :{Style.RESET_ALL}"
                                f"{Fore.GREEN+Style.BRIGHT} Claimed Successfully {Style.RESET_ALL}"
                            )
                            self.log(
                                f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                                f"{Fore.CYAN+Style.BRIGHT}Block  :{Style.RESET_ALL}"
                                f"{Fore.BLUE+Style.BRIGHT} {block_number} {Style.RESET_ALL}"
                            )
                            self.log(
                                f"{Fore.MAGENTA+Style.BRIGHT}      ● {Style.RESET_ALL}"
                                f"{Fore.CYAN+Style.BRIGHT}Tx Hash:{Style.RESET_ALL}"
                                f"{Fore.BLUE+Style.BRIGHT} {tx_hash} {Style.RESET_ALL}"
                            )
                        else:
                            self.log(
                                f"{Fore.CYAN+Style.BRIGHT}Faucet    :{Style.RESET_ALL}"
                                f"{Fore.RED+Style.BRIGHT} Claim Failed {Style.RESET_ALL}"
                            )
                    else:
                        self.log(
                            f"{Fore.CYAN+Style.BRIGHT}Faucet    :{Style.RESET_ALL}"
                            f"{Fore.RED+Style.BRIGHT} Perform On-chain Failed {Style.RESET_ALL}"
                            f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                            f"{Fore.YELLOW+Style.BRIGHT} Check Your Base Sepolia for Gas Fee {Style.RESET_ALL}"
                        )

                else:
                    next_faucet_claim_wib = next_faucet_claim_utc.astimezone(wib).strftime('%x %X %Z')
                    self.log(
                        f"{Fore.CYAN+Style.BRIGHT}Faucet    :{Style.RESET_ALL}"
                        f"{Fore.YELLOW+Style.BRIGHT} Not Time To Claim {Style.RESET_ALL}"
                        f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT} Next Claim At: {Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT}{next_faucet_claim_wib}{Style.RESET_ALL}"
                    )
            

            daily_swaps = user.get("dailySwaps", 0)
            if daily_swaps < 5:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Daily Swap:{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {daily_swaps} Tx {Style.RESET_ALL}"
                )

                swap_limit = 5 - daily_swaps

                for i in range(swap_limit):
                    count = i + 1
                    self.log(
                        f"{Fore.MAGENTA+Style.BRIGHT} ● {Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT}{count}/{swap_limit}{Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT} PRIOR to USDC {Style.RESET_ALL}"
                    )
                    await self.process_swap_prior_to_usdc(account, address, proxy)

                self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT} ● {Style.RESET_ALL}"
                    f"{Fore.CYAN+Style.BRIGHT}USDC to PRIOR{Style.RESET_ALL}"
                )
                await self.process_swap_usdc_to_prior(account, address, proxy)

            else:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Daily Swap:{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {daily_swaps} Tx {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.GREEN+Style.BRIGHT} Completed {Style.RESET_ALL}"
                )

    async def main(self):
        try:
            with open('accounts.txt', 'r') as file:
                accounts = [line.strip() for line in file if line.strip()]
            
            use_proxy_choice = self.print_question()

            while True:
                use_proxy = False
                if use_proxy_choice in [1, 2]:
                    use_proxy = True

                self.clear_terminal()
                self.welcome()
                self.log(
                    f"{Fore.GREEN + Style.BRIGHT}Account's Total: {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{len(accounts)}{Style.RESET_ALL}"
                )

                if use_proxy:
                    await self.load_proxies(use_proxy_choice)
                
                separator = "=" * 25
                for account in accounts:
                    if account:
                        address = self.generate_address(account)
                        self.log(
                            f"{Fore.CYAN + Style.BRIGHT}{separator}[{Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT} {self.mask_account(address)} {Style.RESET_ALL}"
                            f"{Fore.CYAN + Style.BRIGHT}]{separator}{Style.RESET_ALL}"
                        )
                        await self.process_accounts(account, address, use_proxy)
                        await asyncio.sleep(3)

                self.log(f"{Fore.CYAN + Style.BRIGHT}={Style.RESET_ALL}"*72)
                seconds = 24 * 60 * 60
                while seconds > 0:
                    formatted_time = self.format_seconds(seconds)
                    print(
                        f"{Fore.CYAN+Style.BRIGHT}[ Wait for{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} {formatted_time} {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}... ]{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.BLUE+Style.BRIGHT}All Accounts Have Been Processed.{Style.RESET_ALL}",
                        end="\r"
                    )
                    await asyncio.sleep(1)
                    seconds -= 1

        except FileNotFoundError:
            self.log(f"{Fore.RED}File 'accounts.txt' Not Found.{Style.RESET_ALL}")
            return
        except Exception as e:
            self.log(f"{Fore.RED+Style.BRIGHT}Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        bot = PriorTestnet()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] Prior Testnet - BOT{Style.RESET_ALL}                                       "                              
        )