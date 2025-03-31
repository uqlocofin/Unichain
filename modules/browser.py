from tls_client import Session
from requests import get, post
from time import sleep
from uuid import uuid4

from modules.retry import retry, have_json, CustomError
from modules.utils import logger, sleeping
from modules.database import DataBase
import settings


class Browser:

    privy_headers: dict = {
        "Privy-App-Id": "cm6twl7d200a3czewtswk8ghe",
        "Privy-Ca-Id": str(uuid4()),
        "Privy-Client": "react-auth:2.4.3",
    }

    def __init__(self, db: DataBase, encoded_pk: str, proxy: str):
        self.max_retries = 5
        self.db = db
        self.encoded_pk = encoded_pk
        if proxy == "mobile":
            if settings.PROXY not in ['https://log:pass@ip:port', 'http://log:pass@ip:port', 'log:pass@ip:port', '', None]:
                self.proxy = settings.PROXY
            else:
                self.proxy = None
        else:
            if proxy not in ['https://log:pass@ip:port', 'http://log:pass@ip:port', 'log:pass@ip:port', '', None]:
                self.proxy = "http://" + proxy.removeprefix("https://").removeprefix("http://")
                logger.debug(f'[•] Soft | Got proxy {self.proxy}')
            else:
                self.proxy = None

        if self.proxy:
            if proxy == "mobile": self.change_ip()
        else:
            logger.warning(f'[-] Soft | You dont use proxies!')

        self.session = self.get_new_session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        })
        self.address = None


    def get_new_session(self):
        session = Session(
            client_identifier="safari_16_0",
            random_tls_extension_order=True
        )

        if self.proxy:
            session.proxies.update({'http': self.proxy, 'https': self.proxy})

        return session


    @have_json
    def send_request(self, **kwargs):
        if kwargs.get("session"):
            session = kwargs["session"]
            del kwargs["session"]
        else:
            session = self.session

        if kwargs.get("method"): kwargs["method"] = kwargs["method"].upper()
        return session.execute_request(**kwargs)


    def change_ip(self):
        if settings.CHANGE_IP_LINK not in ['https://changeip.mobileproxy.space/?proxy_key=...&format=json', '']:
            print('')
            while True:
                try:
                    r = get(settings.CHANGE_IP_LINK)
                    if 'mobileproxy' in settings.CHANGE_IP_LINK and r.json().get('status') == 'OK':
                        logger.debug(f'[+] Proxy | Successfully changed ip: {r.json()["new_ip"]}')
                        return True
                    elif not 'mobileproxy' in settings.CHANGE_IP_LINK and r.status_code == 200:
                        logger.debug(f'[+] Proxy | Successfully changed ip: {r.text}')
                        return True
                    logger.error(f'[-] Proxy | Change IP error: {r.text} | {r.status_code}')
                    sleep(10)

                except Exception as err:
                    logger.error(f'[-] Browser | Cannot get proxy: {err}')


    @retry(source="Browser", module_str="Get relay tx", exceptions=Exception)
    def get_relay_tx(self, value: int, from_chain_id: int, to_chain_id: int):
        headers = {
            "Origin": "https://relay.link",
            "Referer": "https://relay.link/"
        }
        payload = {
            "user": self.address,
            "originChainId": from_chain_id,
            "originCurrency": "0x0000000000000000000000000000000000000000",
            "destinationChainId": to_chain_id,
            "destinationCurrency": "0x0000000000000000000000000000000000000000",
            "recipient": self.address,
            "amount": str(value),
            "useExternalLiquidity": False,
            "referrer": "relay.link/swap",
            "tradeType": "EXACT_INPUT",
        }

        r = post('https://api.relay.link/quote', json=payload, headers=headers)
        return r.json()['steps'][0]['items'][0]['data']

    @retry(source="Browser", module_str="Get Uniswap quote", exceptions=Exception)
    def get_uniswap_quote(
            self,
            input_address: str,
            output_address: str,
            value: int,
            chain_id: int,
            tried: int = 0
    ):
        payload = {
            "amount": str(value),
            "gasStrategies": [{
                "limitInflationFactor": 1.15, "displayLimitInflationFactor": 1.15, "priceInflationFactor": 1.5,
                "percentileThresholdFor1559Fee": 75, "minPriorityFeeGwei": 2, "maxPriorityFeeGwei": 9
            }],
            "swapper": self.address,
            "tokenIn": input_address,
            "tokenInChainId": chain_id,
            "tokenOut": output_address,
            "tokenOutChainId": chain_id,
            "type": "EXACT_INPUT",
            "urgency": "normal",
            "protocols": ["V4", "V3", "V2"],
            "slippageTolerance": 2.5
        }

        r = self.send_request(
            method="POST",
            url="https://trading-api-labs.interface.gateway.uniswap.org/v1/quote",
            json=payload,
            headers={
                "Origin": "https://app.uniswap.org",
                "Referer": "https://app.uniswap.org/",
                "X-Request-Source": "uniswap-web",
                "X-Universal-Router-Version": "2.0",
                "X-Api-Key": "JoyCGj29tT4pymvhaGciK4r1aIPvqW6W53xT1fwo"
            }
        )

        if r.json().get('quote'):
            return r.json()

        elif r.json().get("errorCode") == "ResourceNotFound" and r.json().get("detail"):
            if tried > 6:
                raise CustomError('Uniswap dont found routes for long time')
            logger.warning(f'[-] Uniswap | Error "{r.json()["detail"]}". Trying again in 5 seconds')
            sleep(5)
            return self.get_uniswap_quote(input_address, output_address, value, chain_id, tried+1)

        raise Exception(f'Unexpected response: {r.json()}')

    @retry(source="Browser", module_str="Get Uniswap get swap tx", exceptions=Exception)
    def get_uniswap_swap_tx(self, swap_quote: dict, permit_headers: dict):
        payload = {
            "quote": swap_quote,
            "simulateTransaction": True,
            "refreshGasPrice": True,
            "gasStrategies": [{
                "limitInflationFactor": 1.15, "displayLimitInflationFactor": 1.15, "priceInflationFactor": 1.5,
                "percentileThresholdFor1559Fee": 75, "minPriorityFeeGwei": 2, "maxPriorityFeeGwei": 9
            }],
            "urgency": "normal",
            **permit_headers
        }
        r = self.send_request(
            method="POST",
            url="https://trading-api-labs.interface.gateway.uniswap.org/v1/swap",
            json=payload,
            headers={
                "Origin": "https://app.uniswap.org",
                "Referer": "https://app.uniswap.org/",
                "X-Request-Source": "uniswap-web",
                "X-Universal-Router-Version": "2.0",
                "X-Api-Key": "JoyCGj29tT4pymvhaGciK4r1aIPvqW6W53xT1fwo"
            }
        )

        if r.json().get('swap'):
            return r.json()["swap"]

        elif r.json().get("errorCode") == "ResourceNotFound" and r.json().get("detail"):
            return {"soft_error": True, "reason": r.json()["detail"]}

        raise Exception(f'Unexpected response: {r.json()}')


    @retry(source="Browser", module_str="Get Bungee get swap tx", exceptions=Exception)
    def get_bungee_swap_tx(self, input_address: str, output_address: str, value: int, chain_id: int):
        params = {
            "userAddress": self.address,
            "originChainId": chain_id,
            "destinationChainId": chain_id,
            "inputAmount": value,
            "inputToken": input_address.lower(),
            "enableManual": "true",
            "receiverAddress": self.address,
            "refuel": "false",
            "outputToken": output_address.lower(),
        }
        r = self.send_request(
            method="GET",
            url="https://backend.bungee.exchange/bungee/quote",
            params=params,
            headers={
                "Origin": "https://new.bungee.exchange",
                "Referer": "https://new.bungee.exchange/",
                "X-Api-Key": "D1mx54qg0a6ZVmk7BCW9B35GK6p1ABYzaAspIkze"
            }
        )

        if (
                r.json().get("result") is None or
                (r.json().get("result", {}).get("autoRoute", {}).get("txData") is None and
                r.json().get("result", {}).get("autoRoute", {}).get("signTypedData") is None)
        ):
            raise Exception(f'Unexpected response: {r.json()}')

        min_out_value = float(r.json()["result"]["autoRoute"]["output"]["minAmountOut"])
        min_out_amount = round(min_out_value / 10 ** r.json()["result"]["autoRoute"]["output"]["token"]["decimals"], 5)

        return {
            "tx": r.json()["result"]["autoRoute"]["txData"],
            "output": min_out_amount,
            "permitData": r.json()["result"]["autoRoute"]["signTypedData"]
        }


    @retry(source="Browser", module_str="Bungee submit approve", exceptions=Exception)
    def bungee_submit_approve(self, signature: str, typed_data_values: dict):
        payload = {
            "requestType": "SWAP_REQUEST",
            "request": typed_data_values,
            "userSignature": signature
        }
        r = self.send_request(
            method="POST",
            url="https://backend.bungee.exchange/bungee-auto/submit",
            json=payload,
            headers={
                "Origin": "https://new.bungee.exchange",
                "Referer": "https://new.bungee.exchange/",
                "X-Api-Key": "D1mx54qg0a6ZVmk7BCW9B35GK6p1ABYzaAspIkze"
            }
        )

        if r.json().get("success") is not True:
            raise Exception(f'Unexpected response: {r.json()}')
        return r.json()["result"]["requestHash"]

    @retry(source="Browser", module_str="Bungee get swap tx", exceptions=Exception)
    def bungee_get_swap_tx(self, request_hash: str):
        r = self.send_request(
            method="GET",
            url="https://backend.bungee.exchange/bungee-auto/request-status",
            params={
                "requestHash": request_hash,
                "requestType": "SWAP_REQUEST",
            },
            headers={
                "Origin": "https://new.bungee.exchange",
                "Referer": "https://new.bungee.exchange/",
                "X-Api-Key": "D1mx54qg0a6ZVmk7BCW9B35GK6p1ABYzaAspIkze"
            }
        )

        if r.json().get("result") is None or r.json().get("result", {}).get("destinationTransactionHash") is None:
            sleep(5)
            return self.bungee_get_swap_tx(request_hash)
        return r.json()["result"]["destinationTransactionHash"]

    @retry(source="Browser", module_str="Matcha get swap tx", exceptions=Exception)
    def matcha_get_swap_tx(self, input_address: str, output_address: str, value: int, chain_id: int):
        r = self.send_request(
            method="GET",
            url="https://matcha.xyz/api/swap/quote",
            params={
                "chainId": chain_id,
                "buyToken": output_address.lower(),
                "sellToken": input_address.lower(),
                "sellAmount": value,
                "taker": self.address,
                "slippageBps": "50",
            },
            headers={
                "Origin": "https://matcha.xyz",
                "Referer": "https://matcha.xyz/",
            }
        )

        if r.json().get("issues").get("allowance"):
            return r.json()["issues"]["allowance"]

        if r.json().get("transaction") is None or r.json().get("transaction", {}).get("data") is None:
            raise Exception(f'Unexpected response: {r.json()}')

        return {
            **r.json()["transaction"],
            "value_out": int(r.json()["buyAmount"]),
        }
