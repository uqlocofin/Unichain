from .wallet import Wallet
from .retry import retry


class Bungee(Wallet):
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


    @retry(source="Bungee", module_str="Swap", exceptions=Exception)
    def swap(
            self,
            from_token_info: dict,
            to_token_info: dict,
            amount: float,
            value: int,
            permit_headers: dict = {},
    ):
        swap_data = self.browser.get_bungee_swap_tx(
            input_address=self._get_token_address(from_token_info["address"]),
            output_address=self._get_token_address(to_token_info["address"]),
            value=value,
            chain_id=self.chain_id
        )

        tx_label = f"bungee swap {amount} {from_token_info['symbol']} -> {swap_data['output']} {to_token_info['symbol']}"

        if (
                from_token_info["address"] != "0x0000000000000000000000000000000000000000" and
                swap_data["permitData"] and
                not permit_headers
        ):
            self.approve(
                chain_name=self.from_chain,
                token_name=from_token_info["symbol"],
                spender=self.web3.to_checksum_address(swap_data["permitData"]["domain"]["verifyingContract"]),
                value=0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff,
                decimals=from_token_info["decimals"],
            )

            typed_data = {
                "domain": swap_data["permitData"]["domain"],
                "types": swap_data["permitData"]["types"],
                "message": swap_data["permitData"]["values"],
                "primaryType": "PermitWitnessTransferFrom",
            }
            request_hash = self.browser.bungee_submit_approve(
                signature=self.sign_message(typed_data=typed_data),
                typed_data_values=swap_data["permitData"]["values"]["witness"]
            )
            swap_tx_hash = self.browser.bungee_get_swap_tx(request_hash)
            self.wait_for_tx(chain_name=self.from_chain, tx_hash=swap_tx_hash, tx_label=tx_label)

        else:
            swap_tx = {
                "from": self.address,
                "to": self.web3.to_checksum_address(swap_data["tx"]["to"]),
                "data": swap_data["tx"]["data"],
                "value": int(swap_data["tx"]["value"]),
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
