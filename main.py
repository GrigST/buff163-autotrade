import atexit
from threading import Thread
from time import time, sleep
import traceback
from requests.cookies import RequestsCookieJar
import json
from argparse import ArgumentParser

from cookie_manager import CookieManager
from steam import AdvancedSteamClient
from buff163.client import Buff163Client


class Account(Thread):
    EXCEPTION_TIMEOUT = 120
    RETRY_FAIL_DELAY = 1800

    def __init__(self, account_cfg, cookies: RequestsCookieJar, steam: AdvancedSteamClient,
                 buff: Buff163Client, refresh_period: int, notifiers=None):
        self._account_cfg = account_cfg
        self.username = self._account_cfg['username']
        self.cookies = cookies
        self.steam = steam
        self.buff = buff
        self.refresh_period = refresh_period
        self.notifiers = notifiers
        super().__init__(name=self.username, daemon=True)
        self.last_exception = 0
        self.known_ids = set()
        self.accepted_trade_ids = set()
        self.confirmed_trade_ids = set()

    def login(self, force=False):
        self.steam.login(force=force)
        self.buff.login(force=force)

    def accept_trade(self, tradeofferid: str):
        if tradeofferid in self.accepted_trade_ids:
            return

        print(f'[{self.username}] Accepting trade offer')
        self.steam.accept_trade_offer(tradeofferid)
        self.accepted_trade_ids.add(tradeofferid)
        print(f'[{self.username}] Success')

    def confirm_trade(self, tradeofferid: str):
        if tradeofferid in self.confirmed_trade_ids:
            return
        
        self.steam._confirm_transaction(tradeofferid)
        self.confirmed_trade_ids.add(tradeofferid)
        print(f'[{self.username}] Confirmed trade {tradeofferid}')

    def check_to_deliver(self, notifications):
        ids_to_send_trade = []
        for game, count in notifications['to_deliver_order'].items():
            if count == 0:
                continue

            data = self.buff.get_items_to_deliver(game)
            for item in data['items']:
                if item['state'] == 'DELIVERING':
                    self.confirm_trade(item['tradeofferid'])

                if item['id'] in self.known_ids:
                    continue

                if item['state'] == 'TO_DELIVER':
                    if not item['has_sent_offer']:
                        ids_to_send_trade.append(item['id'])

                else:
                    self.accept_trade(item['tradeofferid'])

        if len(ids_to_send_trade) > 0:
            print(f'[{self.username}] Sending trade offer to buyer')
            self.buff.send_trade_offers('seller', ids_to_send_trade)
            print(f'[{self.username}] Success')

        self.known_ids.update(ids_to_send_trade)

    def check_to_send_offer(self, notifications):
        ids_to_send_trade = []
        for game, count in notifications['to_send_offer_order'].items():
            if count == 0:
                continue

            data = self.buff.get_items_to_send_offer(game, count + 5)
            for item in data['items']:
                if item['id'] in self.known_ids:
                    continue

                if not item['is_seller_asked_to_send_offer'] and not item['has_sent_offer']:
                    ids_to_send_trade.append(item['id'])

        if len(ids_to_send_trade) > 0:
            print(f'[{self.username}] Sending trade offer to seller')
            self.buff.send_trade_offers('buyer', ids_to_send_trade)
            print(f'[{self.username}] Success')

        self.known_ids.update(ids_to_send_trade)

    def check_to_accept_offers(self, notifications):
        if sum(notifications['to_accept_offer_order'].values()) > 0:
            data = self.buff.get_trades_to_accept()
            for item in data:
                self.accept_trade(item['tradeofferid'])

    def mainloop(self):
        while True:
            notifications = self.buff.get_notifications()
            if self._account_cfg.get('process_sell_offers', True):
                self.check_to_deliver(notifications)
            
            if self._account_cfg.get('process_buy_offers', True):
                self.check_to_send_offer(notifications)
                self.check_to_accept_offers(notifications)

            sleep(self.refresh_period)

    def run(self):
        while True:
            try:
                self.mainloop()

            except:
                try:
                    print(f'[{self.username}] An exception occured')
                    if time() - self.last_exception < self.EXCEPTION_TIMEOUT:
                        raise

                    else:
                        traceback.print_exc()
                        self.last_exception = time()

                    self.login()

                except Exception as e:
                    if self.notifiers:
                        for notifier in self.notifiers:
                            notifier.notify_exception(self.username, e)

                    sleep(self.RETRY_FAIL_DELAY)


class Buff163Autotrade:
    def __init__(self):
        self.parse_args()
        self.load_config()
        self.load_notifiers()
        self.accounts = {account['username']: Account(account, cookie_jar := RequestsCookieJar(),
                         AdvancedSteamClient(account, cookie_jar),
                         Buff163Client(account, cookie_jar),
                         refresh_period=self.refresh_period, notifiers=self.notifiers)
                         for account in self.config['accounts'] if account.get('enabled', True)}
        
        self.cookies_manager = CookieManager(self.cookies_path,
                                             {username: account.cookies
                                              for username, account in self.accounts.items()},
                                              save_enabled=self.cookies_enabled)
        
        self.cookies_manager.load()
        for account in self.accounts.values():
            account.buff.openid_callback = account.steam.login_openid

    def parse_args(self):
        parser = ArgumentParser(prog='Buff163-autotrade',
                                description='Tool to automate sending and receiving trades on buff163')
        
        parser.add_argument('-c', '--config', default='config.json', help='Path to config file')
        parser.add_argument('-d', '--cookies', action='store', dest='cookies', default='cookies.json', help='Path to cookies file')
        parser.add_argument('-n', '--no-cookies', action='store_false', dest='cookies_enabled', help='Do not save cookies file')
        parser.add_argument('-l', '--no-login-check', action='store_false', dest='login_check', help='Do not check if accounts are logged in')
        parser.add_argument('-f', '--force-login', action='store_true', dest='force_login', help='Force login all accounts')
        parser.add_argument('-s', '--check-sessions', action='store_true', dest='check_sessions', help='Check if accounts are logged in and exit')
        parser.add_argument('-r', '--refresh-period', action='store', dest='refresh_period', default=30, help='Buff trades refresh period', type=int)
        parser.add_argument('--notify-test', action='store_true', dest='notify_test', help='Test notifications')
        self.args = parser.parse_args()
        self.config_path: str = self.args.config
        self.cookies_path: str = self.args.cookies
        self.cookies_enabled: bool = self.args.cookies_enabled
        self.login_check: bool = self.args.login_check
        self.force_login: bool = self.args.force_login
        self.check_sessions: bool = self.args.check_sessions
        self.refresh_period: int = self.args.refresh_period
        self.notify_test: bool = self.args.notify_test
        return self.args
    
    def load_config(self):
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)

    def load_notifiers(self):
        self.notifiers = []
        if not self.config.get('notifiers', None):
            return

        if 'telegram_bot' in self.config['notifiers']:
            from notifiers.telegram_bot_notifier import TelegramBotNotifier
            notifier = TelegramBotNotifier(self.config['notifiers']['telegram_bot'])
            self.notifiers.append(notifier)
            notifier.start()

    def test_notifiers(self):
        for notifier in self.notifiers:
            notifier.notify_test()

    def start_all(self):
        for account in self.accounts.values():
            if self.login_check:
                account.login(force=self.force_login)

            account.start()

    def check_all_sessions(self):
        for account in self.accounts.values():
            print(f'Checking steam session for {account.steam.username}... ', end='')
            print('Session is alive' if account.steam.is_session_alive() else 'Session is not alive')
            print(f'Checking buff session for {account.steam.username}... ', end='')
            print('Session is alive' if account.buff.is_session_alive() else 'Session is not alive')


if __name__ == '__main__':
    autotrade = Buff163Autotrade()
    if autotrade.check_sessions:
        autotrade.check_all_sessions()
        exit(0)

    if autotrade.notify_test:
        autotrade.test_notifiers()
        exit(0)

    atexit.register(autotrade.cookies_manager.save)
    autotrade.start_all()

    try:
        while True:
            autotrade.cookies_manager.save()
            sleep(300)

    except KeyboardInterrupt:
        pass

    finally:
        autotrade.cookies_manager.save()
