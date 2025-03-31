
SHUFFLE_WALLETS     = True                  # True | False - перемешивать ли кошельки
RETRY               = 3                     # кол-во попыток при ошибках / фейлах

ETH_MAX_GWEI        = 20
GWEI_MULTIPLIER     = 1.05                  # умножать текущий гвей при отправке транз на 5%
TO_WAIT_TX          = 1                     # сколько минут ожидать транзакцию. если транза будет находится в пендинге после указанного времени то будет считатся зафейленной

RPCS                = {
    'ethereum'  : 'https://eth.drpc.org',
    'unichain'  : 'https://unichain.drpc.org',
    'arbitrum'  : 'https://arbitrum.meowrpc.com',
    'optimism'  : 'https://optimism.drpc.org',
    'zksync'    : 'https://mainnet.era.zksync.io',
    'base'      : 'https://mainnet.base.org',
    'linea'     : 'https://rpc.linea.build',
}


# --- UNICHAIN SETTINGS ---
MODULES_COUNT       = {
    "uniswap"       : [1, 3],               # выполнять модуль от 1 до 3 раз
    "bungee"        : [1, 3],
    "matcha"        : [1, 3],
}
MODULES_PER_ACCOUNT = [0, 0]                # каждый аккаунт сделает от 4 до 7 модулей | укажите [0, 0] что бы отключить лимит


DEPOSIT_SETTINGS     = {
    "check_balance" : True,                 # перед выполнением каждого модуля проверять баланс $ETH в Unichain
    "min_balance"   : 0.0001,               # если баланс меньше указанного - пополняет баланс
    "amounts"       : [0.001, 0.002],       # из EVM сетей бриджить ETH в Unichain на сумму от 0.001 до 0.002 ETH
    "use_balance"   : True,                 # True - сначала пытаться забриджить используя имеющийся баланс в сетях, если баланса нет - выводить в рандомную сеть
                                            # False - всегда выводить с биржи, не используя имеющийся баланс
    "chains"        : [                     # из каких сетей можно бриджить ETH (и в какие можно выводить с биржи)
        'arbitrum',
        'optimism',
        'zksync',
        'base',
        'linea',
    ],
    "exchange"      : "OKX",                # OKX | Bybit | Bitget | Binance - с какой биржи выводить ETH
}

WITHDRAW_SETTINGS   = {
    "from_unichain" : False,                # True - после выполнения всех модулей на аккаунте - выводить ETH с Unichain в рандомную EVM сеть
                                            # False - оставлять ETH в Unichain
    "keep_balance"  : [0.001, 0.0015],      # сколько ETH оставлять в Unichain при отправке в рандомную сеть
    "chains"        : [                     # в какие сети можно отправлять из Unichain
        'arbitrum',
        'optimism',
        'zksync',
        'base',
    ],

    "to_exchange"   : False,                # True - отправлять средства из рандомной сети (из пункта выше) на биржу
                                            # False - оставлять средства в рандомной сети
}


# --- SWAP SETTINGS ---
SWAP_AMOUNTS        = {
    "amounts"       : [0.0001, 0.001],      # свапать от 0.0001 до 0.001 ETH в рандомный токен | укажите [0, 0] что бы использовать проценты
    "percents"      : [20, 50],             # свапать от 20% до 50% баланса ETH в рандомный токен
    "percent_back"  : [70, 90],             # свапать обратно из токена в ETH от 70% до 90% баланса этого токена  | [0, 0] что бы не свапать обратно
}
TOKENS_TO_TRADE     = {                     # список токенов для свапа (для каждой аппки отдельно)
    "uniswap": [
        "USDC",
        "USDT",
        "DAI",
        "UNI",
        "WBTC",
        "LINK",
        "UNICORN",
        "UNIDOGE",
    ],
    "bungee": [
        "USDC",
        "UNI"
    ],
    "matcha": [
        "USDC",
        "UNI",
        "UNICORN",
        "UNIDOGE",
    ],
}


SLEEP_AFTER_TX      = [10, 20]              # задержка после каждой транзы 10-20 секунд
SLEEP_AFTER_ACC     = [20, 40]              # задержка после каждого аккаунта 20-40 секунд


# --- PERSONAL SETTINGS ---

OKX_API_KEY         = ''
OKX_API_SECRET      = ''
OKX_API_PASSWORD    = ''

BYBIT_KEY           = ''
BYBIT_SECRET        = ''

BITGET_KEY          = ''
BITGET_SECRET       = ''
BITGET_PASSWORD     = ''

BINANCE_KEY         = ''
BINANCE_SECRET      = ''

PROXY_TYPE          = "mobile"              # "mobile" - для мобильных/резидентских прокси, указанных ниже | "file" - для статичных прокси из файла `proxies.txt`
PROXY               = 'http://log:pass@ip:port' # что бы не использовать прокси - оставьте как есть
CHANGE_IP_LINK      = 'https://changeip.mobileproxy.space/?proxy_key=...&format=json'

TG_BOT_TOKEN        = ''                    # токен от тг бота (`12345:Abcde`) для уведомлений. если не нужно - оставляй пустым
TG_USER_ID          = []                    # тг айди куда должны приходить уведомления.