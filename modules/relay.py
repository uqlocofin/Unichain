from modules.utils import sleeping, logger
from modules.retry import CustomError, retry
from modules.wallet import Wallet


class Relay(Wallet):
    def __init__(self, wallet: Wallet, from_chain: str, to_chain: str, bridge_amount: float):
        super().__init__(
            privatekey=wallet.privatekey,
            encoded_pk=wallet.encoded_pk,
            recipient=wallet.recipient,
            db=wallet.db,
            browser=wallet.browser
        )

        self.bridged_amount = None
        self.bridge_amount = bridge_amount
        self.from_chain = from_chain
        self.to_chain = to_chain

        self.web3 = self.get_web3(chain_name=self.from_chain)
        self.from_chain_id = self.web3.eth.chain_id
        self.to_chain_id = self.get_web3(self.to_chain).eth.chain_id

        self.wait_for_gwei()


    @retry(source="Relay", module_str="Swap", exceptions=Exception)
    def bridge(self):
        module_str = f'relay bridge ETH {self.from_chain} -> {self.to_chain}'

        try:
            tx_data = self.browser.get_relay_tx(
                value=int(self.bridge_amount * 1e18),
                from_chain_id=self.from_chain_id,
                to_chain_id=self.to_chain_id
            )
            amount = round(int(tx_data["value"]) / 1e18, 6)
            module_str = f'relay bridge {amount} ETH {self.from_chain} -> {self.to_chain}'
            old_balance = self.get_balance(chain_name=self.to_chain, human=True)

            contract_txn = {
                'from': self.address,
                'to': self.web3.to_checksum_address(tx_data["to"]),
                'data': tx_data["data"],
                'chainId': self.web3.eth.chain_id,
                'nonce': self.web3.eth.get_transaction_count(self.address),
                'value': int(tx_data["value"]),
            }

            tx_hash = self.sent_tx(chain_name=self.from_chain, tx=contract_txn, tx_label=module_str, tx_raw=True)
            new_balance = self.wait_balance(chain_name=self.to_chain, needed_balance=old_balance, only_more=True)
            self.bridged_amount = round(new_balance - old_balance, 6)

            return True

        except Exception as error:
            if "insufficient funds for transfer" in str(error):
                logger.warning(f'[-] Web3 | {module_str} | {error} insufficient funds, recalculating')
                self.bridge_amount -= 0.0001
                return self.bridge(retry=retry)
            else:
                raise
