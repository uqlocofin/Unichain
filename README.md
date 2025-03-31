## Unichain Soft

### описание
софт для выполнения транзакций в Unichain

есть возможность пополнения Unichain двумя способами:
1. бридж из рандомной EVM сети (где уже есть баланс) в Unichain
2. вывод с биржи в рандомую EVM сеть и бридж в Unichain

так же есть возможность вывода ETH с Unichain:
* после выполнения всех модулей на аккаунте - бриджить ETH в рандомную EVM сеть
* (при необходимости) в этой EVM сети отправлять ETH на адрес биржи


### список модулей:
*Свапалки*
- [*uniswap*](https://app.uniswap.org/)
- [*matcha*](https://matcha.xyz/)
- [*bungee*](https://new.bungee.exchange/)


### настройка

1. указать свои приватники в `privatekeys.txt`
2. в `settings.py` настройте софт под себя, указав настройки для стейкингов, прокси и тд

---

### запуск

1. установить необходимые либы `pip install -r requirements.txt`
2. запустить софт `py main.py`
3. создать базу данных (*Create Database -> New Database*)
4. стартуем неободимый режим

---

[🍭 kAramelniy 🍭](https://t.me/kAramelniy)

---
