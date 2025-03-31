from random import randint, choice, uniform
from decimal import Decimal
from loguru import logger

from .uniswap import Uniswap
from .wallet import Wallet
from .bungee import Bungee
from .matcha import Matcha
from .relay import Relay

from .utils import sleeping

import settings


def run_module(module_name: str, **kwargs):
    return MODULES_DATA[module_name]["func"](
        module_name=module_name,
        **kwargs
    )


def run_swap(wallet: Wallet, module_name: str):
    swap_module = MODULES_DATA[module_name]["module"](wallet=wallet)

    swap_amounts = settings.SWAP_AMOUNTS.copy()
    token_to_swap = choice(settings.TOKENS_TO_TRADE[module_name])

    eth_balance = wallet.get_balance(chain_name="unichain", human=True)
    if swap_amounts["amounts"] != [0, 0]:
        if eth_balance < swap_amounts["amounts"][0]:
            raise Exception(f"No ETH balance ({round(eth_balance, 5)}) for swap ({swap_amounts['amounts'][0]})")
        elif eth_balance < swap_amounts["amounts"][1]:
            swap_amounts["amounts"][1] = eth_balance

        amount = uniform(*swap_amounts["amounts"])
    else:
        percent = uniform(*swap_amounts["percents"]) / 100
        amount = eth_balance * percent

    amount_to_swap = str(round(Decimal(amount), randint(7, 9)))

    # ETH -> token
    to_token_info = wallet.get_token_info("unichain", token_to_swap)
    native_token_info = wallet.get_token_info("unichain", "ETH")
    swap_module.swap(
        from_token_info=native_token_info,
        to_token_info=to_token_info,
        amount=amount_to_swap,
        value=int(float(amount_to_swap) * 1e18),
    )

    if settings.SWAP_AMOUNTS["percent_back"] != [0, 0]:
        sleeping(settings.SLEEP_AFTER_TX)
        new_token_info = wallet.get_token_info(chain_name="unichain", token_name=token_to_swap)
        percent_back = uniform(*settings.SWAP_AMOUNTS["percent_back"]) / 100

        amount_back = str(round(Decimal(new_token_info["amount"] * percent_back), randint(7, 9)))
        value_back = int(new_token_info["value"] * percent_back)

        # token -> ETH
        swap_module.swap(
            from_token_info=new_token_info,
            to_token_info=native_token_info,
            amount=amount_back,
            value=value_back,
        )


def run_lending(wallet: Wallet, module_name: str):
    lend_module = MODULES_DATA[module_name]["module"](wallet=wallet)
    lend_amounts = settings.DEPOSIT_AMOUNTS.copy()

    eth_balance = wallet.get_balance(chain_name="unichain", human=True)
    if lend_amounts["amounts"] != [0, 0]:
        if eth_balance < lend_amounts["amounts"][0]:
            raise Exception(f"No ETH balance ({round(eth_balance, 5)}) to deposit in lending ({lend_amounts['amounts'][0]})")
        elif eth_balance < lend_amounts["amounts"][1]:
            lend_amounts["amounts"][1] = eth_balance

        amount_to_deposit = round(uniform(*lend_amounts["amounts"]), randint(5, 7))
    else:
        percent = uniform(*lend_amounts["percents"]) / 100
        amount_to_deposit = round(eth_balance * percent, randint(5, 7))

    lend_module.deposit(
        amount=amount_to_deposit,
        value=int(amount_to_deposit * 1e18),
    )
    sleeping(settings.SLEEP_AFTER_TX)

    lend_module.withdraw()


def run_stake(wallet: Wallet, module_name: str):
    stake_module = MODULES_DATA[module_name]["module"](wallet=wallet)
    stake_amounts = settings.STAKE_AMOUNTS.copy()

    eth_balance = wallet.get_balance(chain_name="unichain", human=True)
    if stake_amounts["amounts"] != [0, 0]:
        if eth_balance < stake_amounts["amounts"][0]:
            raise Exception(f"No ETH balance ({round(eth_balance, 5)}) to stake ({stake_amounts['amounts'][0]})")
        elif eth_balance < stake_amounts["amounts"][1]:
            stake_amounts["amounts"][1] = eth_balance

        amount_to_stake = round(uniform(*stake_amounts["amounts"]), randint(5, 7))
    else:
        percent = uniform(*stake_amounts["percents"]) / 100
        amount_to_stake = round(eth_balance * percent, randint(5, 7))

    stake_module.stake(
        amount=amount_to_stake,
        value=int(amount_to_stake * 1e18),
    )

    if stake_amounts["percent_back"] != [0, 0]:
        sleeping(settings.SLEEP_AFTER_TX)

        stake_module.unstake(percent=uniform(*stake_amounts["percent_back"]) / 100)


def run_custom(wallet: Wallet, module_name: str):
    if MODULES_DATA[module_name].get("kwargs"):
        MODULES_DATA[module_name]["module"](wallet=wallet).run(**MODULES_DATA[module_name]["kwargs"])
    else:
        MODULES_DATA[module_name]["module"](wallet=wallet).run()


def deposit_unichain(wallet: Wallet):
    old_balance = wallet.get_balance(chain_name="unichain", human=True)
    if old_balance > settings.DEPOSIT_SETTINGS["min_balance"]:
        return True

    funded_chain, bridge_amount = None, None
    if settings.DEPOSIT_SETTINGS["use_balance"]:
        funded_chain, bridge_amount = wallet.get_chain_balances(balance_amounts=settings.DEPOSIT_SETTINGS["amounts"])

    if not funded_chain or not bridge_amount:
        funded_chain, bridge_amount = wallet.withdraw_funds(
            amount=round(uniform(*settings.DEPOSIT_SETTINGS["amounts"]), 7)
        )
        sleeping(settings.SLEEP_AFTER_TX)

    Relay(
        wallet=wallet,
        from_chain=funded_chain,
        to_chain="unichain",
        bridge_amount=bridge_amount
    ).bridge()

    sleeping(settings.SLEEP_AFTER_TX)


def withdraw_unichain(wallet: Wallet):
    balance = wallet.get_balance(chain_name="unichain", human=True)
    keep_values = settings.WITHDRAW_SETTINGS["keep_balance"].copy()
    if balance < keep_values[1]:
        logger.error(f'[-] Unichain | Not enough ETH to bridge: {round(balance, 6)} ETH')
        wallet.db.append_report(
            privatekey=wallet.encoded_pk,
            text=f"not enough ETH to bridge: {round(balance, 6)} ETH",
            success=False,
        )
        return None, None

    bridge_amount = round(balance - uniform(*keep_values), randint(5, 7))
    random_chain = choice(settings.WITHDRAW_SETTINGS["chains"])

    relay = Relay(
        wallet=wallet,
        from_chain="unichain",
        to_chain=random_chain,
        bridge_amount=bridge_amount
    )
    relay.bridge()
    return random_chain, relay.bridged_amount


MODULES_DATA = {
    "uniswap": {"func": run_swap, "module": Uniswap},
    "bungee": {"func": run_swap, "module": Bungee},
    "matcha": {"func": run_swap, "module": Matcha},
}
