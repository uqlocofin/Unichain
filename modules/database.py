from random import choice, shuffle, randint
from cryptography.fernet import Fernet
from base64 import urlsafe_b64encode
from time import sleep, time
from os import path, mkdir
from hashlib import md5
import json

from modules.retry import DataBaseError
from modules.utils import logger, get_address, WindowName, sleeping
from settings import (
    SHUFFLE_WALLETS,
    PROXY_TYPE,
    MODULES_COUNT,
    MODULES_PER_ACCOUNT,
)

from cryptography.fernet import InvalidToken


class DataBase:
    def __init__(self):

        self.modules_db_name = 'databases/modules.json'
        self.report_db_name = 'databases/report.json'
        self.personal_key = None
        self.window_name = None

        # create db's if not exists
        if not path.isdir(self.modules_db_name.split('/')[0]):
            mkdir(self.modules_db_name.split('/')[0])

        for db_params in [
            {"name": self.modules_db_name, "value": "[]"},
            {"name": self.report_db_name, "value": "{}"},
        ]:
            if not path.isfile(db_params["name"]):
                with open(db_params["name"], 'w') as f: f.write(db_params["value"])

        amounts = self.get_amounts()
        logger.info(f'Loaded {amounts["modules_amount"]} modules for {amounts["accs_amount"]} accounts\n')


    def set_password(self):
        if self.personal_key is not None: return

        logger.debug(f'Enter password to encrypt privatekeys (empty for default):')
        raw_password = input("")

        if not raw_password:
            raw_password = "@karamelniy dumb shit encrypting"
            logger.success(f'[+] Soft | You set empty password for Database\n')
        else:
            print(f'')
        sleep(0.2)

        password = md5(raw_password.encode()).hexdigest().encode()
        self.personal_key = Fernet(urlsafe_b64encode(password))


    def get_password(self):
        if self.personal_key is not None: return

        with open(self.modules_db_name, encoding="utf-8") as f: modules_db = json.load(f)
        if not modules_db: return

        try:
            temp_key = Fernet(urlsafe_b64encode(md5("@karamelniy dumb shit encrypting".encode()).hexdigest().encode()))
            self.decode_pk(pk=list(modules_db.keys())[0], key=temp_key)
            self.personal_key = temp_key
            return
        except InvalidToken: pass

        while True:
            try:
                logger.debug(f'Enter password to decrypt your privatekeys (empty for default):')
                raw_password = input("")
                password = md5(raw_password.encode()).hexdigest().encode()

                temp_key = Fernet(urlsafe_b64encode(password))
                self.decode_pk(pk=list(modules_db.keys())[0], key=temp_key)
                self.personal_key = temp_key
                logger.success(f'[+] Soft | Access granted!\n')
                return

            except InvalidToken:
                logger.error(f'[-] Soft | Invalid password\n')


    def encode_pk(self, pk: str, key: None | Fernet = None):
        if key is None:
            return self.personal_key.encrypt(pk.encode()).decode()
        return key.encrypt(pk.encode()).decode()


    def decode_pk(self, pk: str, key: None | Fernet = None):
        if key is None:
            return self.personal_key.decrypt(pk).decode()
        return key.decrypt(pk).decode()


    def create_modules(self):
        def _format_modules(full_modules: list):
            return [{"module_name": m, "status": "to_run"} for m in full_modules]

        def _generate_modules(raw: bool = False):
            full_modules = [module for module in MODULES_COUNT for _ in range(randint(*MODULES_COUNT[module]))]
            shuffle(full_modules)

            if "apr_claim" in full_modules and "apr" in full_modules:
                while "apr_claim" in full_modules:
                    full_modules.remove("apr_claim")
                after_index = max([index for index, module in enumerate(full_modules) if module == "apr"])
                claim_place = randint(after_index + 1, len(full_modules) + 1)
                full_modules.insert(claim_place, "apr_claim")

            if MODULES_PER_ACCOUNT == [0, 0]: return _format_modules(full_modules)
            elif raw: return full_modules

            modules_amount = randint(*MODULES_PER_ACCOUNT)
            while modules_amount > len(full_modules):
                full_modules += _generate_modules(raw=True)
            return _format_modules(full_modules[:modules_amount])

        self.set_password()

        with open('input_data/privatekeys.txt') as f: private_keys = f.read().splitlines()

        if PROXY_TYPE == "file":
            with open('input_data/proxies.txt') as f:
                proxies = f.read().splitlines()
            if len(proxies) == 0 or proxies == [""] or proxies == ["http://login:password@ip:port"]:
                logger.error('You will not use proxy')
                proxies = [None for _ in range(len(private_keys))]
            else:
                proxies = list(proxies * (len(private_keys) // len(proxies) + 1))[:len(private_keys)]
        elif PROXY_TYPE == "mobile":
            proxies = ["mobile" for _ in range(len(private_keys))]

        with open('input_data/recipients.txt') as f: recipients = f.read().splitlines()
        if len(recipients) == 0 or recipients == [""]:
            recipients = [None for _ in range(len(private_keys))]
        elif len(recipients) != len(private_keys):
            raise DataBaseError(f'Amount of Recipients ({len(recipients)}) must be same as Private keys amount ({len(private_keys)}) or 0')

        with open(self.report_db_name, 'w') as f: f.write('{}')  # clear report db

        new_modules = {
            self.encode_pk(pk): {
                "address": get_address(pk),
                "modules": _generate_modules(),
                "proxy": proxy,
                "recipient": recipient,
            }
            for pk, proxy, recipient in zip(private_keys, proxies, recipients)
        }

        with open(self.modules_db_name, 'w', encoding="utf-8") as f: json.dump(new_modules, f)

        amounts = self.get_amounts()
        logger.critical(f'Dont Forget To Remove Private Keys from privatekeys.txt!')
        logger.info(f'Created Database for {amounts["accs_amount"]} accounts with {amounts["modules_amount"]} modules!\n')


    def get_amounts(self):
        with open(self.modules_db_name, encoding="utf-8") as f: modules_db = json.load(f)
        modules_len = sum([len(modules_db[acc]["modules"]) for acc in modules_db])

        for acc in modules_db:
            for index, module in enumerate(modules_db[acc]["modules"]):
                if module["status"] in ["failed", "cloudflare"]: modules_db[acc]["modules"][index]["status"] = "to_run"

        with open(self.modules_db_name, 'w', encoding="utf-8") as f: json.dump(modules_db, f)

        if self.window_name == None: self.window_name = WindowName(accs_amount=len(modules_db))
        else: self.window_name.accs_amount = len(modules_db)
        self.window_name.set_modules(modules_amount=modules_len)

        return {'accs_amount': len(modules_db), 'modules_amount': modules_len}


    def get_random_module(self, mode: int):
        self.get_password()

        last = False
        with open(self.modules_db_name, encoding="utf-8") as f: modules_db = json.load(f)

        if (
                not modules_db or
                (
                        [module["status"] for acc in modules_db for module in modules_db[acc]["modules"]].count('to_run') == 0 and
                        [module["status"] for acc in modules_db for module in modules_db[acc]["modules"]].count('cloudflare') == 0
                )
        ):
                return 'No more accounts left'

        index = 0
        while True:
            if index == len(modules_db.keys()) - 1: index = 0
            if SHUFFLE_WALLETS: privatekey = choice(list(modules_db.keys()))
            else: privatekey = list(modules_db.keys())[index]
            module_info = choice(modules_db[privatekey]["modules"])
            if module_info["status"] not in ["to_run", "cloudflare"]:
                index += 1
                continue

            if [module["status"] for module in modules_db[privatekey]["modules"]].count('to_run') == 1:  # if no modules left for this account
                last = True

            return {
                'privatekey': self.decode_pk(pk=privatekey),
                'encoded_privatekey': privatekey,
                'proxy': modules_db[privatekey].get("proxy"),
                'recipient': modules_db[privatekey].get("recipient"),
                'module_info': module_info,
                'last': last
            }

    def remove_module(self, module_data: dict):
        with open(self.modules_db_name, encoding="utf-8") as f: modules_db = json.load(f)

        for index, module in enumerate(modules_db[module_data["encoded_privatekey"]]["modules"]):
            if module["module_name"] == module_data["module_info"]["module_name"] and module["status"] in ["to_run", "cloudflare"]:
                self.window_name.add_module()

                if module_data["module_info"]["status"] in [True, "completed"]:
                    modules_db[module_data["encoded_privatekey"]]["modules"].remove(module)
                elif module_data["module_info"]["status"] == "cloudflare":
                    modules_db[module_data["encoded_privatekey"]]["modules"][index]["status"] = "cloudflare"
                else:
                    modules_db[module_data["encoded_privatekey"]]["modules"][index]["status"] = "failed"
                break

        if [module["status"] for module in modules_db[module_data["encoded_privatekey"]]["modules"]].count('to_run') == 0 and \
                [module["status"] for module in modules_db[module_data["encoded_privatekey"]]["modules"]].count('cloudflare') == 0:
            self.window_name.add_acc()
        if not modules_db[module_data["encoded_privatekey"]]["modules"]:
            del modules_db[module_data["encoded_privatekey"]]

        with open(self.modules_db_name, 'w', encoding="utf-8") as f: json.dump(modules_db, f)

    def remove_account(self, module_data: dict):
        with open(self.modules_db_name, encoding="utf-8") as f: modules_db = json.load(f)

        self.window_name.add_acc()
        if module_data["module_info"]["status"] in [True, "completed"]:
            del modules_db[module_data["encoded_privatekey"]]
        else:
            modules_db[module_data["encoded_privatekey"]]["modules"] = [{
                "module_name": modules_db[module_data["encoded_privatekey"]]["modules"][0]["module_name"],
                "status": "failed"
            }]

        with open(self.modules_db_name, 'w', encoding="utf-8") as f: json.dump(modules_db, f)


    def get_wallets_amount(self):
        self.get_password()
        with open(self.modules_db_name, encoding="utf-8") as f: modules_db = json.load(f)
        return len(modules_db)


    def append_report(self, privatekey: str, text: str, success: bool = None):
        status_smiles = {True: '✅ ', False: "❌ ", None: ""}

        with open(self.report_db_name, encoding="utf-8") as f: report_db = json.load(f)

        if not report_db.get(privatekey): report_db[privatekey] = {'texts': [], 'success_rate': [0, 0]}

        report_db[privatekey]["texts"].append(status_smiles[success] + text)
        if success != None:
            report_db[privatekey]["success_rate"][1] += 1
            if success == True: report_db[privatekey]["success_rate"][0] += 1

        with open(self.report_db_name, 'w') as f: json.dump(report_db, f)


    def get_account_reports(self, privatekey: str, get_rate: bool = False):
        with open(self.report_db_name, encoding="utf-8") as f: report_db = json.load(f)

        decoded_privatekey = self.decode_pk(pk=privatekey)
        account_index = f"[{self.window_name.accs_done}/{self.window_name.accs_amount}]"
        if report_db.get(privatekey):
            account_reports = report_db[privatekey]
            if get_rate: return f'{account_reports["success_rate"][0]}/{account_reports["success_rate"][1]}'
            del report_db[privatekey]

            with open(self.report_db_name, 'w', encoding="utf-8") as f: json.dump(report_db, f)

            logs_text = '\n'.join(account_reports['texts'])
            tg_text = f'{account_index} <b>{get_address(pk=decoded_privatekey)}</b>\n\n{logs_text}'
            if account_reports["success_rate"][1]:
                tg_text += f'\n\nSuccess rate {account_reports["success_rate"][0]}/{account_reports["success_rate"][1]}'

            return tg_text

        else:
            return f'{account_index} <b>{get_address(pk=decoded_privatekey)}</b>\n\nNo actions'
