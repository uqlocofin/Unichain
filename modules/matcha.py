from .wallet import Wallet
from .retry import retry


class Matcha(Wallet):
    def __init__(self, wallet: Wallet):
        super().__init__(
            privatekey=wallet.privatekey,
            encoded_pk=wallet.encoded_pk,
            db=wallet.db,
            browser=wallet.browser,
            recipient=wallet.recipient
        )

        self.from_chain = "unichain"
        self.web3 = self.get_web3(self.from_chain)
        self.chain_id = self.web3.eth.chain_id


    @retry(source="Matcha", module_str="Swap", exceptions=Exception)
    def swap(
            self,
            from_token_info: dict,
            to_token_info: dict,
            amount: float,
            value: int,
    ):
        swap_data = self.browser.matcha_get_swap_tx(
            input_address=self._get_token_address(from_token_info["address"]),
            output_address=self._get_token_address(to_token_info["address"]),
            value=value,
            chain_id=self.chain_id
        )

        if (
                from_token_info["address"] != "0x0000000000000000000000000000000000000000" and
                swap_data.get("spender")
        ):
            self.approve(
                chain_name=self.from_chain,
                token_name=from_token_info["symbol"],
                spender=self.web3.to_checksum_address(swap_data["spender"]),
                value=0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff,
                decimals=from_token_info["decimals"],
            )
            return self.swap(from_token_info, to_token_info, amount, value)

        amount_out = round(swap_data['value_out'] / 10 ** to_token_info["decimals"], 6)
        tx_label = f"matcha swap {amount} {from_token_info['symbol']} -> {amount_out} {to_token_info['symbol']}"
        swap_tx = {
            "from": self.address,
            "to": self.web3.to_checksum_address(swap_data["to"]),
            "data": swap_data["data"],
            "value": int(swap_data["value"]),
            'chainId': self.web3.eth.chain_id,
            'nonce': self.web3.eth.get_transaction_count(self.address),
        }

        self.sent_tx(
            chain_name=self.from_chain,
            tx=swap_tx,
            tx_label=tx_label,
            tx_raw=True
        )

    def _get_token_address(self, token_address: str):
        if token_address == "0x0000000000000000000000000000000000000000":
            return "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        else:
            return token_address
