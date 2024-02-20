from requests import Response, Session
from requests.cookies import RequestsCookieJar
from typing import Callable, List, Literal, Union
import os

from buff163.cookie_encryptor import CookieEncryptor
from buff163.exceptions import BuffError, BuffHTTPCodeError, BuffLoginError

class Buff163Client:
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    OPENID_URL = 'https://buff.163.com/account/login/steam?back_url=/'

    def __init__(self, account_cfg, cookies: Union[RequestsCookieJar, dict]):
        self._account_cfg = account_cfg
        self.username = self._account_cfg['username']
        self._session = Session()
        self._session.headers['User-Agent'] = self.USER_AGENT

        if isinstance(cookies, dict):
            self._session.cookies.update(cookies)
        
        else:
            self._session.cookies = cookies

        if account_cfg.get('proxy', None) is not None:
            if isinstance(account_cfg['proxy'], str):
                self._session.proxies.update({'http': account_cfg['proxy'], 'https': account_cfg['proxy']})

            else:
                self._session.proxies.update(account_cfg['proxy'])

        self.openid_callback: Callable = None

    def is_session_alive(self) -> bool:
        resp = self._session.get('https://buff.163.com/news/')
        if not resp.ok:
            raise BuffHTTPCodeError(f'Failed to check if session is alive. Code {resp.status_code}')
        
        resp_txt = resp.text
        return '"user": {"' in resp_txt and '"nickname": "' in resp_txt
    
    def login(self, force=False) -> bool:
        if not force:
            print(f'Checking buff session for {self.username}... ', end='')
            if self.is_session_alive():
                print('Session is alive')
                return False

            print('Session is not alive.')
            print('logging in... ', end='')

        else:
            print(f'logging in buff ({self.username})... ', end='')
        
        self.openid_callback(self.OPENID_URL)
        if self.is_session_alive():
            print('OK')
            return True
        
        raise BuffLoginError('Failed to login buff')
    
    @staticmethod
    def api_get_json_data(resp: Response, exception_msg: str):
        if resp.status_code // 100 == 3:  # redirect, this means user is not logger in
            raise BuffLoginError(f'{exception_msg}. User is not logged in')

        if not resp.ok:
            raise BuffHTTPCodeError(f'{exception_msg}. Code {resp.status_code}')
        
        jresp = resp.json()
        if jresp['code'].lower() != 'ok':
            raise BuffError(f'{exception_msg}. Message: {jresp["code"]}. {jresp["error"]}')
        
        return jresp['data']

    def get_items_to_deliver(self, game: str):
        url = f'https://buff.163.com/api/market/sell_order/to_deliver?game={game}'
        resp = self._session.get(url, allow_redirects=False)
        jresp = self.api_get_json_data(resp, 'Failed to get items to deliver')
        return jresp
    
    def get_items_to_send_offer(self, game: str, count: int = 10):
        url = f'https://buff.163.com/api/market/buy_order/history?game={game}&page_num=1&page_size={count}'
        resp = self._session.get(url, allow_redirects=False)
        jresp = self.api_get_json_data(resp, 'Failed to get items to send offer')
        return jresp
    
    def get_notifications(self):
        url = f'https://buff.163.com/api/message/notification'
        resp = self._session.get(url, allow_redirects=False)
        jresp = self.api_get_json_data(resp, 'Failed to get notifications')

        if len(jresp['updated_at']) == 0 and sum((int(count) for count in category.values()) for category in jresp.values()) == 0:
            raise BuffLoginError('Failed to get notifications. User is not logged in')
        
        return jresp
    
    def get_trades_to_accept(self):
        url = 'https://buff.163.com/api/market/steam_trade'
        resp = self._session.get(url, allow_redirects=False)
        jresp = self.api_get_json_data(resp, 'Failed to get trades to accept')
        return jresp
    
    def send_trade_offers(self, role: Literal['buyer', 'seller'], ids: List[str]):
        encryptor = CookieEncryptor(os.path.join(os.path.dirname(__file__), 'buff_pubkey.pem'))
        data = {
            'bill_orders': ids,
            f'{role}_info': encryptor.encrypt(encryptor.get_cookie_string(self._session.cookies))
        }
        # buff requires these headers, otherwise you will get a csrf error
        headers = {
            'System-Type': 'Android',
            'System-Version': '33'
        }
        url = f'https://buff.163.com/api/market/manual_plus/{role}_send_offer'
        resp = self._session.post(url, json=data, headers=headers, allow_redirects=False)
        jresp = self.api_get_json_data(resp, 'Failed to send trade')
        return jresp
