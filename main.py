from modules.utils import sleeping, logger, sleep, choose_mode
from modules.retry import DataBaseError
from modules import *

from settings import DEPOSIT_SETTINGS, SLEEP_AFTER_ACC, SLEEP_AFTER_TX, WITHDRAW_SETTINGS


def run_modules(mode: int):
    while True:
        print('')
        try:
            module_data = db.get_random_module(mode=mode)
            if module_data == 'No more accounts left':
                logger.success(f'All accounts done.')
                return 'Ended'

            browser = Browser(db=db, encoded_pk=module_data["encoded_privatekey"], proxy=module_data["proxy"])
            wallet = Wallet(
                privatekey=module_data["privatekey"],
                encoded_pk=module_data["encoded_privatekey"],
                recipient=module_data["recipient"],
                browser=browser,
                db=db,
            )
            browser.address = wallet.address
            module_name = module_data["module_info"]["module_name"].replace("_", " ").title()
            logger.info(f'[•] Web3 | {wallet.address} | Starting {module_name}')

            if DEPOSIT_SETTINGS["check_balance"]:
                deposit_unichain(wallet=wallet)

            run_module(
                wallet=wallet,
                module_name=module_data["module_info"]["module_name"]
            )

            if module_data["last"] and WITHDRAW_SETTINGS["from_unichain"]:
                sleeping(SLEEP_AFTER_TX)
                random_chain, amount = withdraw_unichain(wallet=wallet)
                if random_chain and amount and WITHDRAW_SETTINGS["to_exchange"]:
                    if not wallet.recipient:
                        logger.error(f'[-] Soft | Recipient is not provided for transfer')
                        wallet.db.append_report(
                            privatekey=wallet.encoded_pk,
                            text="recipient is not provided for transfer",
                            success=False,
                        )
                    else:
                        sleeping(SLEEP_AFTER_TX)
                        wallet.send_native(chain_name=random_chain, amount=amount)

            module_data["module_info"]["status"] = True

        except Exception as err:
            logger.error(f'[-] Web3 | Account error: {err}')
            db.append_report(privatekey=wallet.encoded_pk, text=str(err), success=False)

        finally:
            if type(module_data) == dict:
                db.remove_module(module_data=module_data)

                if module_data['last']:
                    reports = db.get_account_reports(privatekey=wallet.encoded_pk)
                    TgReport().send_log(logs=reports)

                if module_data["module_info"]["status"] is True: sleeping(SLEEP_AFTER_ACC)
                else: sleeping(10)


if __name__ == '__main__':
    try:
        db = DataBase()

        while True:
            mode = choose_mode()

            match mode:
                case None: break

                case 'Delete and create new':
                    db.create_modules()

                case 1:
                    if run_modules(mode) == 'Ended': break
                    print('')


        sleep(0.1)
        input('\n > Exit\n')

    except DataBaseError as e:
        logger.error(f'[-] Database | {e}')

    except KeyboardInterrupt:
        pass

    finally:
        logger.info('[•] Soft | Closed')
