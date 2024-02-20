from typing import Dict, Tuple
from requests import Response
from requests.cookies import RequestsCookieJar
from steampy.client import SteamClient
from steampy.login import LoginExecutor
from steampy.models import SteamUrl
from steampy.utils import create_cookie
from lxml import html

from exceptions import SteamHTTPCodeError

class LoginExecutorFix(LoginExecutor):
    # Temporary steampy fix
    def set_sessionid_cookies(self):
        community_domain = SteamUrl.COMMUNITY_URL[8:]
        store_domain = SteamUrl.STORE_URL[8:]
        community_cookie_dic = self.session.cookies.get_dict(domain = community_domain)
        store_cookie_dic = self.session.cookies.get_dict(domain = store_domain)
        for name in ('steamLoginSecure', 'sessionid', 'steamRefresh_steam', 'steamCountry'):
            cookie = self.session.cookies.get_dict()[name]
            if name in ["steamLoginSecure"]:
                store_cookie = create_cookie(name, store_cookie_dic[name], store_domain)
            else:
                store_cookie = create_cookie(name, cookie, store_domain)

            if name in ["sessionid", "steamLoginSecure"]:
                community_cookie = create_cookie(name, community_cookie_dic[name], community_domain)
            else:
                community_cookie = create_cookie(name, cookie, community_domain)
            
            self.session.cookies.set(**community_cookie)
            self.session.cookies.set(**store_cookie)


class AdvancedSteamClient(SteamClient):
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'

    def __init__(self, account_cfg, cookie_jar: RequestsCookieJar):
        super().__init__(account_cfg['api_key'])
        self._session.headers['User-Agent'] = self.USER_AGENT
        self._account_cfg = account_cfg
        self._session.cookies = cookie_jar
        if not self._account_cfg.get('trade_confirmations', True):
            self._confirm_transaction = lambda *args, **kwargs: None

        if 'proxy' in self._account_cfg and self._account_cfg['proxy'] is not None:
            if isinstance(self._account_cfg['proxy'], str):
                self._session.proxies.update({'http': self._account_cfg['proxy'], 'https': self._account_cfg['proxy']})

            else:
                self._session.proxies.update(self._account_cfg['proxy'])

        self.steam_guard = self._account_cfg['steamguard']
        self.steam_guard['steamid'] = str(self.steam_guard['steamid'])
        self.username = self._account_cfg['username']
        self._password = self._account_cfg['password']
        self.was_login_executed = True

    def login(self, force=False) -> bool:
        if not force:
            print(f'Checking steam session for {self.username}... ', end='')
            if self.is_session_alive():
                print('Session is alive')
                return False

            print('Session is not alive.')
            print('logging in... ', end='')

        else:
            print(f'logging in steam ({self.username})... ', end='')

        for domain in ('steamcommunity.com', 'store.steampowered.com', 'help.steampowered.com',
                       'steam.tv', 'checkout.steampowered.com', 'login.steampowered.com'):
           try:
               self._session.cookies.clear(domain=domain)
           except KeyError:
               pass

        self._session.cookies.set('steamRememberLogin', 'true')
        login_executor = LoginExecutorFix(self.username, self._password, self.steam_guard['shared_secret'], self._session)
        login_executor.login()
        self.market._set_login_executed(self.steam_guard, self._get_session_id())
        self._session.cookies.set('steamRememberLogin', None)
        print('OK')
        return True

    @staticmethod
    def parse_openid_params(resp: str) -> Dict[str, str]:
        parser = html.document_fromstring(resp)
        params = {
            'action': '',
            'openid.mode': '',
            'openidparams': '',
            'nonce': '',
        }

        for key in params:
            params[key] = parser.findall(f'.//input[@name="{key}"]')[0].attrib['value']

        return params

    def get_openid_params(self, url: str) -> Tuple[str, Dict[str, str]]:
        resp = self._session.get(url)
        if not resp.ok:
            raise SteamHTTPCodeError(f'Failed to get openid params. Code {resp.status_code}')
        
        return resp.url, self.parse_openid_params(resp.text)
    
    def login_openid(self, url: str) -> Response:
        referer, data = self.get_openid_params(url)
        headers = {
            'Origin': 'https://steamcommunity.com',
            'Referer': referer,
            'sessionidSecureOpenIDNonce': data['nonce']
        }

        resp = self._session.post('https://steamcommunity.com/openid/login', data=data, headers=headers)
        if not resp.ok:
            raise SteamHTTPCodeError(f'Failed to login openid. Code {resp.status_code}')
        
        return resp
    
    # Temporary steampy fix
    def _get_session_id(self) -> str:
        return self._session.cookies.get('sessionid', domain='steamcommunity.com')
    
