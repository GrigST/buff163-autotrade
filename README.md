A tool for automating trading on buff163
=====

`buff163-autotrade` is a python tool for automatically sending and
accepting trade offers when buying or selling items on buff163.
`buff163-autotrade` is capable of handling multiple accounts and using proxies.

## Installation

Requires python 3.8 or higher

1. Download repository

    `git clone https://github.com/GrigST/buff163-autotrade.git`

2. Navigate to the directory

    `cd buff163-autotrade`

3. Create a virtual environment

    `python3 -m venv env`

4. Activate virtual environment

    - For Windows Powershell: `env\bin\activate.ps1`
    - For Linux: `source /env/bin/activate`

5. Install dependencies

    `pip install -r requirements.txt`

6. Configure project (see [Configuration](#configuration))

7. Run project

    `python3 main.py`

## Configuration

Rename `config_template.json` to `config.json`

### Configuration file structure

``` json
{
    "accounts": [
        {
            "username": "Your steam username",
            "password": "Your steam password",
            "api_key": "You steam api key",
            "steamguard": {
                "shared_secret": "Your shared secret",
                "identity_secret": "Your identity secret",
                "steamid": "Your steamid"
            },
            "proxy": "socks5://user:pass@ip:port",
            "process_sell_offers": true,
            "process_buy_offers": true
        }
    ]
}
```

`proxy`, `process_sell_offers` and `process_buy_offers` are optional parameters.

[Click here to get steam api key](https://steamcommunity.com/dev/apikey)
(Enter "localhost" in the domain field)

To get steamguard data see https://github.com/SteamTimeIdler/stidler/wiki/Getting-your-%27shared_secret%27-code-for-use-with-Auto-Restarter-on-Mobile-Authentication
or use [Steam Desktop Authenticator](https://github.com/Jessecar96/SteamDesktopAuthenticator)

### Command line options

- `-h`, `--help` - show help message and exit
- `-c CONFIG`, `--config CONFIG` - Path to config file
- `-d COOKIES`, `--cookies COOKIES` - Path to cookies file
- `-n`, `--no-cookies` - Do not save cookies
- `-l`, `--no-login-check` - Do not check if accounts are logged in
- `-f`, `--force-login` - Force login all accounts
- `-s`, `--check-sessions` - Check if accounts are logged in and exit
- `-r REFRESH_PERIOD`, `--refresh-period REFRESH_PERIOD` - Buff trades check period
